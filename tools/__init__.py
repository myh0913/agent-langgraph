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
_registry.register_class("currency_converter", CurrencyConverterSkill, enabled=True, description="货币转换工具（汇率查询、货币换算）。当用户问汇率、货币转换时必须使用，如：'320美元是多少人民币'、'美元兑日元汇率'、'EUR to CNY rate'。输入格式：{'amount': 100, 'from_currency': 'USD', 'to_currency': 'EUR'}")


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