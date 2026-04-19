"""
工具模块
统一注册和管理所有 Tools
"""
from config.tool_registry import get_registry
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

# 注册所有工具到全局注册表（延迟实例化）
_registry = get_registry()
_registry.register_class("intent_classifier", IntentClassifierNode)
_registry.register_class("intent_confirm", IntentConfirmNode)
_registry.register_class("business_handler", BusinessHandlerNode)

__all__ = [
    "IntentClassifierNode",
    "IntentConfirmNode",
    "BusinessHandlerNode",
    "BaseToolNode",
    "IntentClassifierInput",
    "IntentClassifierOutput",
    "IntentConfirmInput",
    "IntentConfirmOutput",
    "BusinessHandlerInput",
    "BusinessHandlerOutput",
    "get_registry",
]
