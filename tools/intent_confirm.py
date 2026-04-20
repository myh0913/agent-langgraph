"""
意图确认工具
当意图不明确时，追问用户提供选择
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from config.prompts import INTENT_CONFIRM_SYSTEM
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

        prompt = f"""用户说：{user_message}{history_text}{context_str}

用户的意图不够明确。请分析后：
1. 如果能根据上下文合理推断用户意图，给出最可能的选择
2. 如果无法推断，追问用户或提供选项让用户选择

请用自然语言回复，格式：
- 追问时直接写问题，不要加 prefix
- 提供选项时列出选项并标号
- 能推断时直接确认
"""

        response = self._call_llm(
            prompt=prompt,
            system=INTENT_CONFIRM_SYSTEM,
            temperature=0.7
        )

        return self._parse_response(response)

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
