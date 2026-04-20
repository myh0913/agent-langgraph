"""
API 路由定义
使用 FastAPI 定义 REST API 接口
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from memory import SessionManager, ContextCompressor
from graph import create_agent_graph
from config.settings import settings
from config.llm import get_llm_client
from .response import ApiResponse

router = APIRouter()

# 全局组件
session_manager = SessionManager()
llm_client = get_llm_client()
compressor = ContextCompressor()

# 线程池用于并发控制
executor = ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENT_REQUESTS)

# ============== 请求模型 ==============

class MessageRequest(BaseModel):
    """发送消息请求"""
    user_id: str = Field(..., description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID，为空则创建新会话")
    message: str = Field(..., description="用户消息")
    context: Optional[Dict[str, Any]] = Field(default=None, description="额外上下文")


# ============== 路由 ==============

@router.post("/message")
async def send_message(request: MessageRequest):
    """
    发送消息并获取响应

    流程：
    1. 获取或创建会话
    2. 检查上下文压缩
    3. 执行 Agent 图
    4. 保存消息到历史
    5. 返回响应
    """
    # 获取或创建会话
    session_id = session_manager.get_or_create_session(
        user_id=request.user_id,
        session_id=request.session_id
    )
    # 获取历史消息
    history = session_manager.get_history(session_id)

    # 检查是否需要压缩（传入 LLM 客户端）
    was_compressed = False
    original_count = len(history)
    if compressor.should_compress(history):
        compressed, was_compressed = compressor.compress(history, llm_client=llm_client)
        if was_compressed:
            history = compressed

    # 构建 Agent 状态
    agent_input = {
        "user_id": request.user_id,
        "session_id": session_id,
        "messages": history,
        "current_message": request.message,
        "intent_type": "",
        "confidence": 0.0,
        "context": request.context or {},
        "response": ""
    }

    # 计算发送给 LLM 的 token 数量
    token_count = compressor.count_tokens(agent_input["messages"])

    # 执行 Agent 图
    try:
        graph = create_agent_graph()

        # 在线程池中执行，避免阻塞
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            lambda: graph.invoke(agent_input)
        )

        response_text = result.get("response", "抱歉，我没有理解您的意思。")
        intent_type = result.get("intent_type", "UNKNOWN")

    except Exception as e:
        return ApiResponse.error(message=f"Agent 执行错误: {str(e)}", code=500)

    # 保存消息到历史
    session_manager.add_message(session_id, "user", request.message)
    session_manager.add_message(session_id, "assistant", response_text)

    return ApiResponse.success(
        data={
            "session_id": session_id,
            "response": response_text,
            "timestamp": datetime.now().isoformat(),
            "intent_type": intent_type,
            "context_info": {
                "compressed": was_compressed,
                "original_count": original_count,
                "current_count": len(history),
                "token_limit": settings.CONTEXT_TOKEN_LIMIT,
                "token_count": token_count
            },
            "llm_input": {
                "messages": agent_input["messages"]
            }
        }
    )


@router.get("/history/{user_id}/{session_id}")
async def get_history(user_id: str, session_id: str, limit: Optional[int] = None):
    """获取会话历史"""
    messages = session_manager.get_history(session_id, limit)

    if not messages:
        # 验证会话是否存在
        sessions = session_manager.get_user_sessions(user_id, limit=1000)
        if not any(s["session_id"] == session_id for s in sessions):
            return ApiResponse.error(message="会话不存在", code=500)

    return ApiResponse.success(
        data={"session_id": session_id, "messages": messages}
    )


@router.get("/sessions/{user_id}")
async def list_sessions(user_id: str, limit: int = 10):
    """获取用户的所有会话"""
    sessions = session_manager.get_user_sessions(user_id, limit=limit)

    return ApiResponse.success(
        data={"user_id": user_id, "sessions": sessions}
    )


@router.delete("/session/{user_id}/{session_id}")
async def delete_session(user_id: str, session_id: str):
    """删除会话"""
    success = session_manager.delete_session(user_id, session_id)
    if not success:
        return ApiResponse.error(message="会话不存在或无权删除", code=500)
    return ApiResponse.success(message="会话已删除")


@router.get("/skills")
async def list_skills():
    """列出所有已注册的 Skills/Tools 及其状态"""
    from config.tool_registry import get_registry
    registry = get_registry()
    tools = registry.list_tools_with_status()
    return ApiResponse.success(data={"skills": tools})


@router.get("/skills/{name}")
async def get_skill(name: str):
    """获取指定 Skill 的详情"""
    from config.tool_registry import get_registry
    registry = get_registry()
    try:
        tool = registry.get(name)
        cfg = registry.get_config(name)
        return ApiResponse.success(data={
            "name": name,
            "enabled": cfg.enabled if cfg else False,
            "description": cfg.description if cfg else tool.description,
            "schema": tool.args_schema.schema() if hasattr(tool, "args_schema") else None
        })
    except KeyError:
        return ApiResponse.error(message=f"Skill '{name}' 不存在", code=404)


@router.post("/skills/{name}/enable")
async def enable_skill(name: str):
    """启用指定 Skill"""
    from config.tool_registry import get_registry
    registry = get_registry()
    success = registry.set_enabled(name, True)
    if not success:
        return ApiResponse.error(message=f"Skill '{name}' 不存在", code=404)
    return ApiResponse.success(message=f"Skill '{name}' 已启用")


@router.post("/skills/{name}/disable")
async def disable_skill(name: str):
    """禁用指定 Skill"""
    from config.tool_registry import get_registry
    registry = get_registry()
    success = registry.set_enabled(name, False)
    if not success:
        return ApiResponse.error(message=f"Skill '{name}' 不存在", code=404)
    return ApiResponse.success(message=f"Skill '{name}' 已禁用")


@router.get("/tasks")
async def list_tasks():
    """列出所有定时任务"""
    from tasks import TaskScheduler
    scheduler = TaskScheduler()
    # TODO: 获取实际任务列表
    return ApiResponse.success(data={"tasks": [], "message": "任务列表获取功能待实现"})


@router.post("/tasks")
async def create_task(task_data: Dict[str, Any]):
    """创建定时任务"""
    # TODO: 实现创建任务逻辑
    return ApiResponse.success(message="任务创建功能待实现")
