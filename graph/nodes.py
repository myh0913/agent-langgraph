"""
LangGraph 节点定义
使用工具注册表获取工具实例（延迟加载），而非每次新建
"""
from typing import TypedDict
from config.tool_registry import get_registry
from config.prompts import GENERAL_HANDLER_SYSTEM, build_general_response_prompt


class AgentState(TypedDict):
    """Agent 状态定义，在图的各节点之间传递"""
    user_id: str                      # 用户ID，用于会话隔离
    session_id: str                   # 会话ID
    token: str                        # 用户认证 token
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
        token=state.get("token", ""),
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


def remember_handler_node(state: AgentState) -> AgentState:
    """
    记住指令节点
    当意图识别为 REMEMBER 时，将用户要求记住的内容写入知识库
    """
    from knowledge.importers import get_remember_handler

    handler = get_remember_handler()
    result = handler.handle(state["current_message"])

    if not result or not result.get("matched"):
        state["response"] = "抱歉，我没有理解您的记住指令，请尝试说「记住xxx」。"
    else:
        import_result = result.get("result", {})
        if import_result.get("success"):
            state["response"] = f"好的，我已经记住：{result.get('content', '')}"
        else:
            state["response"] = f"记住失败：{import_result.get('error', '未知错误')}"

    return state


def response_node(state: AgentState) -> AgentState:
    """
    最终响应节点
    生成返回给用户的最终响应
    """
    if state.get("response"):
        return state

    intent_type = state.get("intent_type", "GENERAL")
    history = state.get("messages", [])
    user_message = state.get("current_message", "")

    # GENERAL 意图：走 LLM + history 生成 contextual 回复
    if intent_type == "GENERAL":
        from config.llm import get_llm_client
        from config.tool_registry import get_registry
        registry = get_registry()
        tools = registry.list_tools_with_status()
        available_tools_text = "\n".join([
            f"- {t['name']}: {t.get('description', '无描述')}" + ("（已启用）" if t["enabled"] else "（已禁用）")
            for t in tools
        ]) if tools else "（无）"

        llm = get_llm_client()
        prompt = build_general_response_prompt(
            user_message=user_message,
            history=history,
            context=state.get("context", {}),
            knowledge_text="",
            available_tools_text=available_tools_text
        )
        response = llm.chat(prompt=prompt, system=GENERAL_HANDLER_SYSTEM, temperature=0.7)
        state["response"] = response
    else:
        state["response"] = "您好！请问有什么可以帮您的？"

    return state
