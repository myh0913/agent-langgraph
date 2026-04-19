"""
LangGraph 节点定义
使用工具注册表获取工具实例（延迟加载），而非每次新建
"""
from typing import TypedDict
from config.tool_registry import get_registry


class AgentState(TypedDict):
    """Agent 状态定义，在图的各节点之间传递"""
    user_id: str                      # 用户ID，用于会话隔离
    session_id: str                   # 会话ID
    messages: list                    # 消息历史
    current_message: str              # 当前用户消息
    intent_type: str                  # 识别的意图类型
    confidence: float                 # 意图分类置信度
    context: dict                     # 额外的上下文信息
    response: str                     # 最终响应
    tools_used: list[str]            # 调用过的工具/Skills 列表
    knowledge_used: list[str]         # 参考过的知识库内容 ID 列表


def intent_classifier_node(state: AgentState) -> AgentState:
    """
    意图分类节点
    判断用户意图是 BUSINESS / GENERAL / CONFIRM
    """
    registry = get_registry()
    classifier = registry.get("intent_classifier")

    result = classifier._run(
        user_message=state["current_message"],
        history=state.get("messages", [])
    )

    state["intent_type"] = result.intent_type
    state["confidence"] = result.confidence

    return state


def business_handler_node(state: AgentState) -> AgentState:
    """
    业务处理节点
    处理业务相关的请求，调用后端 API
    """
    registry = get_registry()
    handler = registry.get("business_handler")

    result = handler._run(
        user_message=state["current_message"],
        session_id=state["session_id"],
        history=state.get("messages", []),
        context=state.get("context")
    )

    state["response"] = result.response
    state["tools_used"] = result.tools_used
    state["knowledge_used"] = getattr(result, 'knowledge_used', [])
    if result.data:
        state["context"] = {"data": result.data}

    return state


def intent_confirm_node(state: AgentState) -> AgentState:
    """
    意图确认节点
    当意图不明确时，追问或提供选择
    """
    registry = get_registry()
    confirm = registry.get("intent_confirm")

    result = confirm._run(
        user_message=state["current_message"],
        history=state.get("messages", []),
        context=state.get("context")
    )

    if result.needs_response and result.prompt:
        state["response"] = result.prompt
    elif result.selected:
        state["response"] = f"您是否想说：{result.selected}"
    else:
        state["response"] = "您的需求我还需要进一步了解，请问您想了解哪方面的内容？"

    return state


def response_node(state: AgentState) -> AgentState:
    """
    最终响应节点
    生成返回给用户的最终响应
    """
    if state.get("response"):
        return state

    state["response"] = "您好！请问有什么可以帮您的？"
    return state
