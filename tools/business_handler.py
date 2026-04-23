"""
业务处理工具
调用后端 API 获取业务数据，分析后生成回复
支持知识库检索增强
"""
import re
import json
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import httpx

from config.prompts import (
    BUSINESS_HANDLER_SYSTEM,
    BUSINESS_PLAN_SYSTEM,
    KNOWLEDGE_ANSWER_SYSTEM,
    build_business_plan_prompt,
    build_knowledge_answer_prompt,
    build_analyze_response_prompt,
)
from config.settings import settings
from .base import BaseToolNode


class BusinessHandlerInput(BaseModel):
    """业务处理输入"""
    user_message: str = Field(description="用户消息")
    session_id: str = Field(description="会话ID")
    token: str = Field(default="", description="用户认证 token")
    history: list = Field(default_factory=list, description="对话历史")
    context: Optional[Dict[str, Any]] = Field(default=None, description="上下文")


class BusinessHandlerOutput(BaseModel):
    """业务处理输出"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    response: str = Field(description="返回给用户的回复")
    error: Optional[str] = None
    tools_used: list[str] = Field(default_factory=list, description="调用过的工具/Skills 列表")
    knowledge_used: list[str] = Field(default_factory=list, description="参考的知识库内容")


class BusinessHandlerNode(BaseToolNode):
    """业务处理工具节点"""

    def __init__(self, **kwargs):
        super().__init__(
            name="business_handler",
            description=(
                "处理业务相关请求。调用后端 API 获取数据，分析后返回结果。"
                "支持用户查询订单、产品、数据统计等业务场景。"
            ),
            args_schema=BusinessHandlerInput,
            **kwargs
        )

    def _run_impl(
        self,
        user_message: str,
        session_id: str,
        token: str = "",
        history: list = None,
        context: Optional[Dict[str, Any]] = None
    ) -> BusinessHandlerOutput:
        """
        执行业务处理

        Args:
            user_message: 用户消息
            session_id: 会话ID
            context: 上下文

        Returns:
            BusinessHandlerOutput: 处理结果
        """
        # Step 0: 先查知识库
        knowledge_context = self._search_knowledge(user_message, top_k=3)
        knowledge_ids = [k["id"] for k in knowledge_context] if knowledge_context else []

        # Step 1: 让 LLM 分析用户问题 + 知识库上下文，制定计划
        api_plan = self._plan_api_call(user_message, history, context, knowledge_context)
        print("--------------- API/工具 调用计划 -----------------")
        print(api_plan)
        print("--------------------------------")
        if not api_plan:
            # 没有 API 调用计划，检查知识库是否有答案
            if knowledge_context:
                response = self._answer_from_knowledge(
                    user_message, knowledge_context, history, context
                )
                return BusinessHandlerOutput(
                    success=True,
                    response=response,
                    tools_used=[],
                    knowledge_used=knowledge_ids
                )
            return BusinessHandlerOutput(
                success=False,
                response="抱歉，我无法理解您的业务请求，请更详细地描述您的需求。",
                error="无法制定 API 调用计划"
            )

        # 检查 LLM 的决定：
        # - action=answer: 直接用知识库回答
        # - action=api_call: 调用后端 API
        # - action=confirm: 需要用户确认
        action = api_plan.get("action", "api_call")

        if action == "answer" and knowledge_context:
            response = self._answer_from_knowledge(
                user_message, knowledge_context, history, context,
                available_tools_text=self._get_available_tools_description(),
                reason=api_plan.get("reason")
            )
            return BusinessHandlerOutput(
                success=True,
                response=response,
                tools_used=[],
                knowledge_used=knowledge_ids
            )

        if action == "confirm":
            return BusinessHandlerOutput(
                success=True,
                response=api_plan.get("confirm_message", "我需要确认一下您的需求："),
                tools_used=[],
                knowledge_used=knowledge_ids
            )

        # Step 2: 调用 Skill 或后端 API
        skill_name = api_plan.get("skill_name", "")
        if skill_name:
            # 有 skill_name，说明要调用本地 Skill
            api_result = self._call_skill(skill_name, api_plan.get("params", {}), token=token)
            # Skill 返回结果可能有现成的 message
            if api_result.get("success") and api_result.get("message"):
                return BusinessHandlerOutput(
                    success=True,
                    data=api_result,
                    response=api_result["message"],
                    tools_used=[skill_name],
                    knowledge_used=knowledge_ids
                )
            # 如果 Skill 返回失败，走后续分析逻辑
            if "error" in api_result:
                return BusinessHandlerOutput(
                    success=False,
                    response=f"Skill 执行失败：{api_result['error']}",
                    tools_used=[skill_name],
                    knowledge_used=knowledge_ids
                )
        else:
            # 没有 skill_name，调后端 HTTP API
            api_result = self._call_backend(api_plan, token=token)

        # Step 3: 分析 API 返回，生成回复（仅后端 API 或 Skill 返回无 message 时走这里）
        response = self._analyze_and_respond(
            user_message, api_result, history, context, knowledge_context
        )

        return BusinessHandlerOutput(
            success=True,
            data=api_result,
            response=response,
            tools_used=[api_plan.get("skill_name", "unknown")],
            knowledge_used=knowledge_ids
        )

    def _search_knowledge(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """查询知识库获取相关内容"""
        try:
            from knowledge import get_knowledge_manager
            manager = get_knowledge_manager()
            results = manager.search(query=query, top_k=top_k)
            return results
        except Exception as e:
            # 知识库不可用时静默跳过
            return []

    def _format_knowledge_context(self, knowledge: List[Dict[str, Any]]) -> str:
        """格式化知识库内容为 prompt 上下文"""
        if not knowledge:
            return ""

        context_parts = []
        context_parts.append("\n\n【知识库参考内容】")
        context_parts.append("（如果以下内容与用户问题相关，请优先参考）\n")

        for i, k in enumerate(knowledge, 1):
            context_parts.append(f"\n--- 知识 {i} ---")
            if k.get("title"):
                context_parts.append(f"标题：{k['title']}")
            if k.get("category"):
                context_parts.append(f"分类：{k['category']}")
            context_parts.append(f"内容：{k['content']}")
            context_parts.append(f"相关度：{k.get('score', 0):.2f}")

        return "\n".join(context_parts)

    def _get_available_tools_description(self) -> str:
        """获取所有已启用工具的描述，用于 LLM 决策"""
        from config.tool_registry import get_registry
        registry = get_registry()
        tools = registry.list_tools_with_status()
        enabled = [t for t in tools if t["enabled"]]
        disabled = [t for t in tools if not t["enabled"]]

        lines = ["\n【当前可用的 Skills/Tools】（enabled=True）"]
        if enabled:
            for t in enabled:
                desc = t.get("description", "") or "无描述"
                lines.append(f"  - {t['name']}: {desc}")
        else:
            lines.append("  （暂无）")

        lines.append("\n【已禁用的 Skills/Tools】（enabled=False）")
        if disabled:
            for t in disabled:
                lines.append(f"  - {t['name']}: {t.get('description', '无描述')}")
        else:
            lines.append("  （暂无）")

        return "\n".join(lines)

    def _plan_api_call(
        self,
        user_message: str,
        history: list = None,
        context: Optional[dict] = None,
        knowledge_context: List[Dict[str, Any]] = None
    ) -> Optional[dict]:
        """
        让 LLM 分析用户问题，制定行动计划
        结合知识库内容决定：直接回答 / 调用API / 询问确认

        Args:
            user_message: 用户消息
            history: 对话历史
            context: 上下文
            knowledge_context: 知识库检索结果

        Returns:
            dict: 包含 action, skill_name, endpoint, method, params, reason 等
        """
        history = history or []
        knowledge_text = self._format_knowledge_context(knowledge_context)

        # 使用结构化 prompt 模板
        available_tools_text = self._get_available_tools_description()
        print("--------------- 可用工具描述 -----------------")
        print(available_tools_text)
        prompt = build_business_plan_prompt(
            user_message=user_message,
            history=history,
            context=context or {},
            knowledge_text=knowledge_text,
            available_tools_text=available_tools_text
        )

        response = self._call_llm(
            prompt=prompt,
            system=BUSINESS_PLAN_SYSTEM,
            temperature=0.3
        )
        print("--------------- llm判断直接回答 / 调用API / 询问确认 -----------------")
        print(response)
        print("--------------------------------")
        return self._parse_json_response(response)

    def _answer_from_knowledge(
        self,
        user_message: str,
        knowledge: List[Dict[str, Any]],
        history: list = None,
        context: dict = None,
        available_tools_text: str = "",
        reason: str = None
    ) -> str:
        """基于知识库内容生成回答"""
        history = history or []
        knowledge_text = self._format_knowledge_context(knowledge)
        available_tools_text = available_tools_text or self._get_available_tools_description()

        # 使用结构化 prompt 模板
        prompt = build_knowledge_answer_prompt(
            user_message=user_message,
            history=history,
            context=context,
            knowledge_text=knowledge_text,
            available_tools_text=available_tools_text
        )

        answer = self._call_llm(
            prompt=prompt,
            system=KNOWLEDGE_ANSWER_SYSTEM,
            temperature=0.7
        )

        # 标记来源，让用户知道这是从知识库来的
        source_info = f"📚 基于知识库回答（相关度: {knowledge[0].get('score', 0):.2f}）\n\n" if knowledge else ""
        return source_info + answer

    def _call_skill(self, skill_name: str, params: dict, token: str = "") -> dict:
        """
        调用本地 Skill

        Args:
            skill_name: Skill 名称
            params: Skill 参数
            token: 用户认证 token（会注入到 params 中传给 Skill）

        Returns:
            dict: Skill 返回数据
        """
        try:
            from config.tool_registry import get_registry
            registry = get_registry()
            skill = registry.get(skill_name)

            # 将 token 注入 params（如果 Skill 需要）
            if token:
                params["token"] = token

            # 调用 skill 的 _run 方法
            result = skill._run(**params)

            # Skill 返回的是 Pydantic 模型，转成 dict
            if hasattr(result, 'model_dump'):
                return result.model_dump()
            elif hasattr(result, 'dict'):
                return result.dict()
            else:
                return {"result": str(result)}
        except Exception as e:
            return {"error": f"Skill 调用失败: {str(e)}"}

    def _call_backend(self, plan: dict, token: str = "") -> dict:
        """
        调用后端 API

        Args:
            plan: API 调用计划
            token: 用户认证 token

        Returns:
            dict: API 返回数据
        """
        if not plan:
            return {}

        endpoint = plan.get("endpoint", "")
        method = plan.get("method", "GET").upper()
        params = plan.get("params", {})

        url = f"{settings.BACKEND_API_HOST}{settings.BACKEND_API_PREFIX}{endpoint}"

        headers = {"Authorization": f"Bearer {token}"} if token else {}

        try:
            with httpx.Client(timeout=30.0, headers=headers) as client:
                if method == "GET":
                    resp = client.get(url, params=params)
                elif method == "POST":
                    resp = client.post(url, json=params)
                else:
                    return {"error": f"Unsupported method: {method}"}

                resp.raise_for_status()

                text = resp.text.strip()
                if not text:
                    return {"data": None, "message": "后端返回空数据"}

                return resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    def _analyze_and_respond(
        self,
        user_message: str,
        api_result: dict,
        history: list = None,
        context: Optional[dict] = None,
        knowledge_context: List[Dict[str, Any]] = None
    ) -> str:
        """
        分析 API 返回，生成用户友好回复

        Args:
            user_message: 用户原始消息
            api_result: API 返回数据
            history: 对话历史
            context: 上下文
            knowledge_context: 知识库内容（可选参考）

        Returns:
            str: 生成的回复
        """
        history = history or []
        history_text = f"\n\n对话历史（共 {len(history)} 条消息）：\n{self._format_history(history)}" if history else ""
        knowledge_text = self._format_knowledge_context(knowledge_context) if knowledge_context else ""

        if "error" in api_result:
            return f"请求后端失败：{api_result['error']}"

        if not api_result:
            return "没有获取到数据，请稍后再试。"

        # 使用结构化 prompt 模板
        prompt = build_analyze_response_prompt(
            user_message=user_message,
            history=history,
            knowledge_text=knowledge_text,
            api_result=api_result
        )

        answer = self._call_llm(
            prompt=prompt,
            system=BUSINESS_HANDLER_SYSTEM,
            temperature=0.7
        )

        # 标记来源
        if knowledge_context:
            return f"📊 基于后端API数据\n\n{answer}"
        return answer

    def _format_history(self, history: list) -> str:
        if not history:
            return "（无历史消息）"
        lines = []
        for m in history[-6:]:
            role = "用户" if m.get("role") == "user" else "助手"
            content = m.get("content", "")[:100]
            lines.append(f"{role}：{content}")
        return "\n".join(lines) or "（无）"

    def _parse_json_response(self, response: str) -> Optional[dict]:
        """
        解析 LLM 返回的 JSON

        Args:
            response: LLM 原始返回

        Returns:
            dict 或 None
        """
        text = response.strip()

        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None