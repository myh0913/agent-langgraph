"""
知识库模块
提供 RAG 知识检索能力
"""
from .chunker import TextChunker
from .embedder import LocalEmbedder, get_embedder
from .chroma_client import ChromaClient, get_chroma_client
from .manager import KnowledgeManager, get_knowledge_manager
from .importers import (
    FileImporter, TextImporter, ApiImporter, RememberHandler,
    get_file_importer, get_text_importer, get_api_importer, get_remember_handler
)

__all__ = [
    # 核心组件
    "TextChunker",
    "LocalEmbedder",
    "get_embedder",
    "ChromaClient",
    "get_chroma_client",
    "KnowledgeManager",
    "get_knowledge_manager",
    # 导入器
    "FileImporter",
    "TextImporter",
    "ApiImporter",
    "RememberHandler",
    "get_file_importer",
    "get_text_importer",
    "get_api_importer",
    "get_remember_handler",
]