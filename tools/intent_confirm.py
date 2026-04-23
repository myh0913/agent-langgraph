"""
意图确认工具
当意图不明确时，追问用户提供选择
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from config.prompts import (
    INTENT_CONFIRM_SYSTEM,
    build_intent_confirm_prompt,
)
from .base import BaseToolNode


class IntentConfirmInput(BaseModel):
    """意图确认输入"""
    user_message: str = Field(description="用户发送的原始消息")
    history: list = Field(default_factory=list, description="对话历史")
    context: Optional[dict] = Field(default=None, description="当前对话上下文")


class IntentConfirmOutput(BaseModel):
    """意图确认输出"""
    needs_response: bool = Field(description="是否需要用户回复")
    prompt: Optional[str] = Field(default=None, description="追问提示语")
    options: Optional[List[str]] = Field(default=None, description="提供的选项列表")
    selected: Optional[str] = Field(default=None, description="自动选择的选项（如果能确定）")


class IntentConfirmNode(BaseToolNode):
    """意图确认工具节点"""

    def __init__(self, **kwargs):
        super().__init__(
            name="intent_confirm",
            description=(
                "当用户意图不明确时，通过追问、提供选择或引导来明确用户需求。"
            ),
            args_schema=IntentConfirmInput,
            **kwargs
        )

    def _run_impl(
        self,
        user_message: str,
        history: list = None,
        context: Optional[dict] = None
    ) -> IntentConfirmOutput:
        """
        执行意图确认

        Args:
            user_message: 用户消息
            context: 上下文信息

        Returns:
            IntentConfirmOutput: 确认结果
        """
        context_str = ""
        if context:
            context_str = f"\n当前上下文：{context}"

        history = history or []
        history_text = f"\n\n对话历史（共 {len(history)} 条消息）：\n{self._format_history(history)}" if history else "(无)"

        # 查询知识库
        try:
            from knowledge import get_knowledge_manager
            km = get_knowledge_manager()
            results = km.search(query=user_message, top_k=3)
            if results:
                parts = ["\n【知识库参考内容】"]
                for i, r in enumerate(results, 1):
                    parts.append(f"\n--- 知识 {i} ---")
                    if r.get("title"):
                        parts.append(f"标题：{r['title']}")
                    if r.get("category"):
                        parts.append(f"分类：{r['category']}")
                    parts.append(f"内容：{r.get('content', '')}")
                    parts.append(f"相关度：{r.get('score', 0):.2f}")
                knowledge_text = "".join(parts)
            else:
                knowledge_text = "（知识库中未找到相关内容）"
        except Exception:
            knowledge_text = "（知识库查询失败）"

        # 使用结构化 prompt 模板
        from config.tool_registry import get_registry
        registry = get_registry()
        tools = registry.list_tools_with_status()
        available_tools_text = "\n".join([
            f"- {t['name']}: {t.get('description', '无描述')}" + ("（已启用）" if t["enabled"] else "（已禁用）")
            for t in tools
        ]) if tools else "（无）"

        prompt = build_intent_confirm_prompt(
            user_message=user_message,
            history=history,
            context=context,
            knowledge_text=knowledge_text,
            available_tools_text=available_tools_text
        )

        response = self._call_llm(
            prompt=prompt,
            system=INTENT_CONFIRM_SYSTEM,
            temperature=0.7
        )

        res = self._parse_response(response)

        print("-------------------------------------")
        print("意图确认:", res)
        print("-------------------------------------")
        
        return res

    def _format_history(self, history: list) -> str:
        if not history:
            return "（无历史消息）"
        lines = []
        for m in history[-6:]:
            role = "用户" if m.get("role") == "user" else "助手"
            content = m.get("content", "")[:100]
            lines.append(f"{role}：{content}")
        return "\n".join(lines) or "（无）"

    def _parse_response(self, response: str) -> IntentConfirmOutput:
        """
        解析 LLM 返回

        Args:
            response: LLM 原始返回（现在是自然语言）

        Returns:
            IntentConfirmOutput: 解析后的结果
        """
        text = response.strip()

        if not text:
            return IntentConfirmOutput(needs_response=False)

        # 解析选项（检测 "1. xxx" 或 "选项1: xxx" 格式）
        options = None
        import re
        option_matches = re.findall(r'^\d+[.、]\s*(.+)$', text, re.MULTILINE)
        if option_matches:
            options = [o.strip() for o in option_matches]

        needs_response = True
        prompt = None
        selected = None

        # 如果是选项模式，设置 needs_response
        if options:
            return IntentConfirmOutput(
                needs_response=True,
                prompt=None,
                options=options,
                selected=None
            )

        # 否则把整个响应作为 prompt 返回（表示追问）
        return IntentConfirmOutput(
            needs_response=True,
            prompt=text,
            options=None,
            selected=None
        )
