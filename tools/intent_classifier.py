"""
意图分类工具
使用 LLM 判断用户意图类型
"""
import re
import json
from typing import Literal, List
from pydantic import BaseModel, Field
from config.prompts import (
    INTENT_CLASSIFIER_SYSTEM,
    build_intent_classifier_prompt,
)
from .base import BaseToolNode


class IntentClassifierInput(BaseModel):
    """意图分类输入"""
    user_message: str = Field(description="用户发送的原始消息")
    history: list = Field(default_factory=list, description="对话历史")


class IntentClassifierOutput(BaseModel):
    """意图分类输出"""
    intent_type: Literal["BUSINESS", "GENERAL", "CONFIRM", "REMEMBER"] = Field(
        description="意图类型: BUSINESS=业务相关, GENERAL=一般对话, CONFIRM=需确认, REMEMBER=记住指令"
    )
    confidence: float = Field(description="置信度 0~1")
    reason: str = Field(description="判断理由（简短）", default="")


class IntentClassifierNode(BaseToolNode):
    """意图分类工具节点"""

    def __init__(self, **kwargs):
        super().__init__(
            name="intent_classifier",
            description=(
                "识别用户意图类型。返回 BUSINESS（业务相关）、GENERAL（一般对话）"
                "或 CONFIRM（需要确认）三种类型及置信度。"
            ),
            args_schema=IntentClassifierInput,
            **kwargs
        )

    def _run_impl(self, user_message: str, history: list = None) -> IntentClassifierOutput:
        """
        执行意图分类

        Args:
            user_message: 用户消息

        Returns:
            IntentClassifierOutput: 分类结果
        """
        history = history or []

        # 先快速判断是否可能为 REMEMBER（记住指令不需要查知识库）
        _remember_start_patterns = [
            r"^记住", r"^记住[：:]",
            r"^请记住", r"^请记住[：:]",
            r"^帮我记住", r"^帮我记住[：:]",
            r"^记一下", r"^记一下[：:]",
            r"^记下来", r"^记下来[：:]",
            r"^把这个记下来", r"^把这个记下来[：:]",
        ]
        _is_likely_remember = any(
            re.search(p, user_message) for p in _remember_start_patterns
        )

        # 非 REMEMBER 时，查知识库作为上下文辅助分类
        if _is_likely_remember:
            knowledge_text = "（记住指令，无需知识库参考）"
        else:
            knowledge_text = self._search_knowledge_for_classifier(user_message)

        # 使用结构化 prompt 模板
        from config.tool_registry import get_registry
        registry = get_registry()
        tools = registry.list_tools_with_status()
        available_tools_text = "\n".join([
            f"- {t['name']}: {t.get('description', '无描述')}" + ("（已启用）" if t["enabled"] else "（已禁用）")
            for t in tools
        ]) if tools else "（无）"

        prompt = build_intent_classifier_prompt(
            user_message=user_message,
            history=history,
            context={},
            knowledge_text=knowledge_text,
            available_tools_text=available_tools_text
        )

        response = self._call_llm(
            prompt=prompt,
            system=INTENT_CLASSIFIER_SYSTEM,
            temperature=0.1
        )
        intent_type, confidence, reason = self._parse_response(response)
        
        print("----------------意图分类解析结果----------------")
        print(intent_type, confidence, reason)
        print("----------------")

        # 特殊处理：用户明确回答"是的/对/ok/好"等，确认了之前的意图
        # 这类回答应该直接进入 BUSINESS，而不是继续 CONFIRM 循环
        if intent_type == "CONFIRM":
            confirm_words = ["是的", "对的", "好", "ok", "好呀", "确认", "是", "yep", "yeah", "exactly"]
            if any(word in user_message for word in confirm_words):
                intent_type = "BUSINESS"
                confidence = 0.9

        return IntentClassifierOutput(
            intent_type=intent_type,
            confidence=confidence,
            reason=reason
        )

    def _search_knowledge_for_classifier(self, query: str, top_k: int = 3) -> str:
        """
        为意图分类阶段搜索知识库

        Args:
            query: 查询文本
            top_k: 返回条数

        Returns:
            str: 格式化后的知识库上下文，如果查询失败返回提示语
        """
        try:
            from knowledge import get_knowledge_manager
            manager = get_knowledge_manager()
            results = manager.search(query=query, top_k=top_k)
            if not results:
                return "（知识库中未找到相关内容）"

            parts = ["\n【知识库参考内容】"]
            for i, r in enumerate(results, 1):
                parts.append(f"\n--- 知识 {i} ---")
                if r.get("title"):
                    parts.append(f"标题：{r['title']}")
                if r.get("category"):
                    parts.append(f"分类：{r['category']}")
                parts.append(f"内容：{r.get('content', '')}")
                parts.append(f"相关度：{r.get('score', 0):.2f}")
            return "".join(parts)
        except Exception:
            return "（知识库查询失败，不影响分类）"

    def _parse_response(self, response: str):
        """
        解析 LLM 返回的 JSON 结构化输出，提取意图类型、置信度、理由

        Args:
            response: LLM 原始返回（JSON 格式，如 {"intent": "BUSINESS", "confidence": 0.9, "reason": "..."}）

        Returns:
            Tuple[str, float, str]: (意图类型, 置信度, 理由)
        """
        text = response.strip()

        # print("-------------------------------------")
        # print("意图判断：", text)
        # print("-------------------------------------")

        # 优先尝试 JSON 解析
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                intent_type = data.get("intent", "GENERAL").strip().upper()
                confidence = float(data.get("confidence", 0.5))
                reason = data.get("reason", "").strip()

                # 限制置信度范围
                confidence = max(0.0, min(1.0, confidence))

                # 验证 intent 合法性
                if intent_type not in ("BUSINESS", "GENERAL", "CONFIRM", "REMEMBER"):
                    intent_type = "GENERAL"

                return intent_type, confidence, reason
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        # JSON 解析失败时降级为 GENERAL（不应该发生）
        return "GENERAL", 0.5, ""

    def _format_history(self, history: list) -> str:
        if not history:
            return "（无历史消息）"
        lines = []
        for m in history[-6:]:  # 最多显示最近6条
            role = "用户" if m.get("role") == "user" else "助手"
            content = m.get("content", "")[:100]
            lines.append(f"{role}：{content}")
        return "\n".join(lines) or "（无）"
