"""
LangGraph 边定义
定义节点之间的流转逻辑
"""
from typing import Literal
from graph.nodes import AgentState


def should_continue(state: AgentState) -> Literal["business_handler", "intent_confirm", "response", "remember_handler"]:
    """
    根据意图类型决定下一步流向

    Returns:
        "business_handler" - 业务意图，转到业务处理
        "intent_confirm" - 需要确认，转到意图确认
        "response" - 直接回复
        "remember_handler" - 记住指令，转到记忆写入
    """
    intent_type = state.get("intent_type", "GENERAL")
    confidence = state.get("confidence", 0.0)

    # REMEMBER 优先级最高，写入知识库
    if intent_type == "REMEMBER":
        return "remember_handler"

    # BUSINESS 意图始终走业务处理器（会先查知识库）
    if intent_type == "BUSINESS":
        return "business_handler"

    # CONFIRM 和低置信度走确认节点
    if intent_type == "CONFIRM" or confidence < 0.5:
        return "intent_confirm"

    # GENERAL 走通用回复
    return "response"

def route_intent(state: AgentState) -> str:
    """
    路由函数，用于 StateGraph 的 conditional_edges
    """
    return should_continue(state)
