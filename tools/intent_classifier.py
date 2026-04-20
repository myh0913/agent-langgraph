"""
意图分类工具
使用 LLM 判断用户意图类型
"""
import re
from typing import Literal
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

        # 使用结构化 prompt 模板
        prompt = build_intent_classifier_prompt(
            user_message=user_message,
            history=history
        )

        response = self._call_llm(
            prompt=prompt,
            system=INTENT_CLASSIFIER_SYSTEM,
            temperature=0.1
        )

        intent_type, confidence, reason = self._parse_response(response)

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
            line_lower = line.strip().lower()
            if "BUSINESS" in line_upper and intent_type != "CONFIRM":
                intent_type = "BUSINESS"
            elif "CONFIRM" in line_upper:
                intent_type = "CONFIRM"
            elif "GENERAL" in line_upper and intent_type == "GENERAL":
                intent_type = "GENERAL"

            # 提取置信度（从形如 "置信度：0.8" 或 "0.85" 的文本中）
            if "置信度" in line or "confidence" in line_lower:
                nums = re.findall(r'0\.\d+|1\.0+', line)
                if nums:
                    try:
                        confidence = float(nums[0])
                        if confidence > 1:
                            confidence = 1.0
                    except ValueError:
                        pass

        # 特殊规则：用户明确回答"是的"之类，说明他们确认了意图，应该进入 BUSINESS
        # 而不是继续 CONFIRM 循环
        if intent_type == "CONFIRM" and confidence >= 0.6:
            # 检查是否在回复之前的确认问题
            user_msg_lower = text.lower()  # 这里不用，因为这里是解析 LLM 返回
            pass  # 这个规则需要在调用处处理，不在这里

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
