"""
API 模块
"""
from .routes import router
from .knowledge_routes import router as knowledge_router

__all__ = ["router", "knowledge_router"]
