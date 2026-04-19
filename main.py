"""
Agent 主入口
启动 API 服务和定时任务调度器
"""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config.settings import settings
from api import router, knowledge_router
from tasks import TaskScheduler
from memory import SessionManager

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan 上下文管理器
    替代已废弃的 @app.on_event("startup") / @app.on_event("shutdown")
    """
    # ---- 启动 ----
    logger.info("正在启动 Agent 服务...")

    # 初始化会话管理器（确保数据库表创建）
    session_manager = SessionManager()

    # 启动定时任务调度器
    scheduler = TaskScheduler()
    if settings.SCHEDULER_ENABLED:
        scheduler.start()
        logger.info("定时任务调度器已启动")

    logger.info("Agent 服务启动完成")

    yield  # ← 应用在这里正常运行

    # ---- 关闭 ----
    logger.info("正在关闭 Agent 服务...")
    if settings.SCHEDULER_ENABLED:
        scheduler.stop()
    logger.info("Agent 服务已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="Temp Agent API",
    description="基于 LangGraph 的 Agent 系统",
    version="1.0.0",
    lifespan=lifespan,   # ← 注册 lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix=settings.API_PREFIX)
app.include_router(knowledge_router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "FI-Agent",
        "version": "1.0.1",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


def main():
    """主函数"""
    logger.info(f"启动服务，监听 {settings.API_HOST}:{settings.API_PORT}")

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
