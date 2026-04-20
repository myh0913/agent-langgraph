"""
知识库配置
"""
import os
from pathlib import Path


class KnowledgeSettings:
    """知识库配置"""

    # 项目根目录
    PROJECT_ROOT = Path(__file__).parent.parent
    MODELS_DIR = PROJECT_ROOT / "models" / "sentence-transformers"

    # Embedding 模型配置（all-MiniLM-L6-v2）
    EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
    EMBEDDING_DEVICE = "cpu"
    EMBEDDING_DIM = 384

    # ChromaDB 配置
    CHROMA_PERSIST_DIR = PROJECT_ROOT / "knowledge" / "chroma"
    CHROMA_COLLECTION = "temp_agent_knowledge"

    # 分块配置
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
    CHUNK_MIN_LENGTH = 10  # 降低最小长度阈值，支持短内容

    # 检索配置
    SEARCH_TOP_K = 5
    SEARCH_SCORE_THRESHOLD = 0.7

    # 知识库目录
    KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
    SOURCES_DIR = KNOWLEDGE_DIR / "sources"
    CHUNKS_DIR = KNOWLEDGE_DIR / "chunks"

    # 索引配置
    INDEX_BATCH_SIZE = 100


knowledge_settings = KnowledgeSettings()