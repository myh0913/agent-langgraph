"""
工具模块
统一注册和管理所有 Tools/Skills
"""
from config.tool_registry import get_registry, set_tool_enabled
from .base import BaseToolNode
from .intent_classifier import (
    IntentClassifierNode,
    IntentClassifierInput,
    IntentClassifierOutput,
)
from .intent_confirm import (
    IntentConfirmNode,
    IntentConfirmInput,
    IntentConfirmOutput,
)
from .business_handler import (
    BusinessHandlerNode,
    BusinessHandlerInput,
    BusinessHandlerOutput,
)

# 注册内置工具
_registry = get_registry()
_registry.register_class("intent_classifier", IntentClassifierNode, enabled=True)
_registry.register_class("intent_confirm", IntentConfirmNode, enabled=True)
_registry.register_class("business_handler", BusinessHandlerNode, enabled=True)

# 注册 Skills（从 skills/ 目录导入）
from skills.currency_converter import CurrencyConverterSkill
_registry.register_class("currency_converter", CurrencyConverterSkill, enabled=True, description="提供货币转换功能，输入示例：{{'amount': 100, 'from_currency': 'USD', 'to_currency': 'EUR'}}")


__all__ = [
    "IntentClassifierNode",
    "IntentConfirmNode",
    "BusinessHandlerNode",
    "CurrencyConverterSkill",
    "BaseToolNode",
    "IntentClassifierInput",
    "IntentClassifierOutput",
    "IntentConfirmInput",
    "IntentConfirmOutput",
    "BusinessHandlerInput",
    "BusinessHandlerOutput",
    "CurrencyConverterInput",
    "CurrencyConverterOutput",
    "get_registry",
    "set_tool_enabled",
]