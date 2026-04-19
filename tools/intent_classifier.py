"""
意图分类工具
使用 LLM 判断用户意图类型
"""
import re
from typing import Literal
from pydantic import BaseModel, Field
from config.prompts import INTENT_CLASSIFIER_SYSTEM
from .base import BaseToolNode


class IntentClassifierInput(BaseModel):
    """意图分类输入"""
    user_message: str = Field(description="用户发送的原始消息")
    history: list = Field(default_factory=list, description="对话历史")


class IntentClassifierOutput(BaseModel):
    """意图分类输出"""
    intent_type: Literal["BUSINESS", "GENERAL", "CONFIRM"] = Field(
        description="意图类型: BUSINESS=业务相关, GENERAL=一般对话, CONFIRM=需确认"
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

        prompt = f"""用户消息：{user_message}

对话历史（共 {len(history)} 条消息）：
{self._format_history(history)}

请判断这条消息的意图类型，只返回以下格式（不要有其他内容）：
BUSINESS - 业务相关，需要调用工具或API获取数据
GENERAL - 一般对话，闲聊、问候等与业务无关
CONFIRM - 需要确认，消息模糊或需要用户提供更多信息

同时给出你的置信度（0到1之间）和简短理由。"""

        response = self._call_llm(
            prompt=prompt,
            system=INTENT_CLASSIFIER_SYSTEM,
            temperature=0.1
        )

        intent_type, confidence, reason = self._parse_response(response)

        return IntentClassifierOutput(
            intent_type=intent_type,
            confidence=confidence,
            reason=reason
        )

    def _parse_response(self, response: str):
        """
        解析 LLM 返回文本，提取意图类型、置信度、理由

        Args:
            response: LLM 原始返回

        Returns:
            Tuple[str, float, str]: (意图类型, 置信度, 理由)
        """
        text = response.strip()

        intent_type = "GENERAL"
        confidence = 0.5
        reason = ""

        for line in text.split("\n"):
            line_upper = line.strip().upper()
            if "BUSINESS" in line_upper and intent_type != "CONFIRM":
                intent_type = "BUSINESS"
            elif "CONFIRM" in line_upper:
                intent_type = "CONFIRM"
            elif "GENERAL" in line_upper and intent_type == "GENERAL":
                intent_type = "GENERAL"

            # 提取置信度
            matches = re.findall(r"(?:^|\s)(0(?:\.\d+)?|1(?:\.0+)?)(?:\s|$|,)", line)
            for m in matches:
                try:
                    confidence = float(m)
                    if confidence > 1:
                        confidence = 1.0
                except ValueError:
                    pass

        return intent_type, confidence, reason

    def _format_history(self, history: list) -> str:
        if not history:
            return "（无历史消息）"
        lines = []
        for m in history[-6:]:  # 最多显示最近6条
            role = "用户" if m.get("role") == "user" else "助手"
            content = m.get("content", "")[:100]
            lines.append(f"{role}：{content}")
        return "\n".join(lines) or "（无）"
