"""
配置管理模块
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 环境变量
env_path = Path(__file__).parent.parent / "env" / ".env"
load_dotenv(env_path)

class Settings:
    """全局配置类"""
    
    # 项目根目录
    PROJECT_ROOT = Path(__file__).parent.parent
    
    # LLM 配置
    MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
    MODEL_API_KEY  = os.getenv("MODEL_API_KEY", "")
    MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1")
    
    # 上下文压缩配置
    CONTEXT_TOKEN_LIMIT = int(os.getenv("CONTEXT_TOKEN_LIMIT", "200000"))  # 触发压缩的 token 阈值
    COMPRESSION_KEEP_RECENT = int(os.getenv("COMPRESSION_KEEP_RECENT", "20"))  # 压缩后保留的最近消息数
    
    # 并发配置
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "3"))
    
    # 定时任务配置
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    SESSION_RETENTION_DAYS = int(os.getenv("SESSION_RETENTION_DAYS", "30"))
    
    # API 配置
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8008"))
    API_PREFIX = os.getenv("API_PREFIX", "/api/ai")

    # 后端业务接口配置
    BACKEND_API_HOST = os.getenv("BACKEND_API_HOST", "http://localhost:8080")
    BACKEND_API_PREFIX = os.getenv("BACKEND_API_PREFIX", "/api")

    # Redis 配置（会话存储）
    REDIS_URL = os.getenv("REDIS_URL", "redis://:fa@report@8.130.95.223:6380/0")

    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/agent.log")

settings = Settings()
