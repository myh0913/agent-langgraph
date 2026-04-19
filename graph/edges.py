"""
LangGraph 边定义
定义节点之间的流转逻辑
"""
from typing import Literal
from graph.nodes import AgentState


def should_continue(state: AgentState) -> Literal["business_handler", "intent_confirm", "response"]:
    """
    根据意图类型决定下一步流向
    
    Returns:
        "business_handler" - 业务意图，转到业务处理
        "intent_confirm" - 需要确认，转到意图确认
        "response" - 直接回复
    """
    intent_type = state.get("intent_type", "GENERAL")
    confidence = state.get("confidence", 0.0)
    
    if confidence < 0.5:
        # 置信度低，需要确认
        return "intent_confirm"
    
    if intent_type == "BUSINESS":
        return "business_handler"
    elif intent_type == "CONFIRM":
        return "intent_confirm"
    else:
        return "response"

def route_intent(state: AgentState) -> str:
    """
    路由函数，用于 StateGraph 的 conditional_edges
    """
    return should_continue(state)
