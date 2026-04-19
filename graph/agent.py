"""
Agent 图创建
定义整个处理流程的结构
"""
from langgraph.graph import StateGraph, END
from .nodes import (
    AgentState,
    intent_classifier_node,
    business_handler_node,
    intent_confirm_node,
    response_node
)
from .edges import should_continue, route_intent

def create_agent_graph():
    """
    创建 Agent 处理图
    
    流程:
    用户消息 -> 意图分类 -> (根据意图)
        -> BUSINESS: 业务处理 -> 响应
        -> CONFIRM: 意图确认 -> 响应
        -> GENERAL: 直接响应
    """
    # 创建图
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("intent_classifier", intent_classifier_node)
    workflow.add_node("business_handler", business_handler_node)
    workflow.add_node("intent_confirm", intent_confirm_node)
    workflow.add_node("response", response_node)
    
    # 设置入口点
    workflow.set_entry_point("intent_classifier")
    
    # 添加条件边（意图分类后根据意图类型分流）
    workflow.add_conditional_edges(
        "intent_classifier",
        route_intent,
        {
            "business_handler": "business_handler",
            "intent_confirm": "intent_confirm",
            "response": "response"
        }
    )
    
    # 业务处理和意图确认后都到响应节点
    workflow.add_edge("business_handler", "response")
    workflow.add_edge("intent_confirm", "response")
    
    # 响应节点是终点
    workflow.add_edge("response", END)
    
    # 编译图
    return workflow.compile()
