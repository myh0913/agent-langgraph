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
1. 如果能根据上下文合理推断用户意图，给出最可能的选择（selected）
2. 如果无法推断，通过 prompt 追问用户，或提供 options 列表让用户选择

回复格式（只需返回实际存在的字段，不要空行）：
- 如果追问：prompt = "你的问题"
- 如果提供选项：options = ["选项1", "选项2", "选项3"]
- 如果推断出意图：selected = "推断的意图" + prompt = "确认：..."
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
            response: LLM 原始返回

        Returns:
            IntentConfirmOutput: 解析后的结果
        """
        text = response.strip()

        prompt = None
        options = None
        selected = None

        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("prompt"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    prompt = parts[1].strip().strip('"').strip("'")
            elif line.startswith("options"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    try:
                        options_str = parts[1].strip().strip("[]")
                        options = [
                            o.strip().strip('"').strip("'")
                            for o in options_str.split(",")
                        ]
                    except Exception:
                        pass
            elif line.startswith("selected"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    selected = parts[1].strip().strip('"').strip("'")

        needs_response = bool(prompt) or (options is not None and len(options) > 0)

        return IntentConfirmOutput(
            needs_response=needs_response,
            prompt=prompt,
            options=options,
            selected=selected
        )
