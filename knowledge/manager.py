"""
知识库管理器
"""
import logging
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime

from .config import knowledge_settings
from .chunker import TextChunker
from .chroma_client import get_chroma_client

logger = logging.getLogger(__name__)


class KnowledgeManager:
    """
    知识库管理器
    统一管理知识的导入、索引、检索
    """

    def __init__(self):
        self.chunker = TextChunker(
            chunk_size=knowledge_settings.CHUNK_SIZE,
            chunk_overlap=knowledge_settings.CHUNK_OVERLAP,
            min_chunk_length=knowledge_settings.CHUNK_MIN_LENGTH
        )
        self.chroma = get_chroma_client()

    def import_file(
        self,
        file_path: str,
        category: str = "",
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """导入单个知识文件"""
        tags = tags or []
        path = Path(file_path)

        if not path.exists():
            return {"success": False, "error": "文件不存在"}

        logger.info(f"导入知识文件: {file_path}")

        # 分块
        chunks = self.chunker.chunk_file(file_path)

        if not chunks:
            return {"success": False, "error": "分块失败或文件为空"}

        # 添加元数据
        for chunk in chunks:
            chunk["category"] = category
            chunk["tags"] = tags
            chunk["created_at"] = datetime.now().isoformat()

        # 写入 ChromaDB
        result = self.chroma.add_chunks(chunks)

        return {
            "success": True,
            "file": str(path),
            "total_chunks": len(chunks),
            "indexed": result["success"],
            "failed": result["failed"]
        }

    def import_directory(
        self,
        dir_path: str,
        category: str = "",
        tags: List[str] = None,
        recursive: bool = True,
        file_patterns: List[str] = ["*.md", "*.txt", "*.json"]
    ) -> Dict[str, Any]:
        """批量导入目录下的知识文件"""
        path = Path(dir_path)
        if not path.is_dir():
            return {"success": False, "error": "目录不存在"}

        tags = tags or []
        total_files = 0
        total_chunks = 0
        failed_files = []

        for pattern in file_patterns:
            files = path.rglob(pattern) if recursive else path.glob(pattern)

            for file_path in files:
                if "__pycache__" in str(file_path):
                    continue

                result = self.import_file(
                    str(file_path),
                    category=category,
                    tags=tags
                )

                if result.get("success"):
                    total_files += 1
                    total_chunks += result.get("total_chunks", 0)
                else:
                    failed_files.append({
                        "file": str(file_path),
                        "error": result.get("error", "未知错误")
                    })

        return {
            "success": True,
            "total_files": total_files,
            "total_chunks": total_chunks,
            "failed_count": len(failed_files),
            "failed_files": failed_files
        }

    def import_text(
        self,
        text: str,
        title: str = "",
        category: str = "",
        tags: List[str] = None,
        source: str = "manual"
    ) -> Dict[str, Any]:
        """直接导入文本"""
        tags = tags or []

        chunks = self.chunker.chunk_text(
            text,
            source=source,
            metadata={"title": title}
        )

        if not chunks:
            return {"success": False, "error": "分块失败或文本为空"}

        for chunk in chunks:
            chunk["category"] = category
            chunk["tags"] = tags
            chunk["created_at"] = datetime.now().isoformat()

        result = self.chroma.add_chunks(chunks)

        return {
            "success": True,
            "total_chunks": len(chunks),
            "indexed": result["success"],
            "failed": result["failed"]
        }

    def search(
        self,
        query: str,
        top_k: int = 5,
        category: str = None,
        tags: List[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索知识"""
        return self.chroma.search(
            query=query,
            top_k=top_k,
            category=category,
            tags=tags
        )

    def delete(self, chunk_id: str) -> bool:
        """删除知识块"""
        return self.chroma.delete_chunk(chunk_id)

    def delete_by_filter(self, category: str = None, tags: List[str] = None) -> int:
        """
        根据条件删除知识

        Args:
            category: 按分类删除
            tags: 按标签删除（匹配任一）

        Returns:
            int: 删除数量
        """
        deleted = 0
        # 搜索所有匹配的内容
        results = self.chroma.search(query="", top_k=1000, category=category, tags=tags)
        for r in results:
            if self.chroma.delete_chunk(r["id"]):
                deleted += 1
        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        return {
            "total_chunks": self.chroma.count(),
            "collection": knowledge_settings.CHROMA_COLLECTION,
            "persist_dir": str(knowledge_settings.CHROMA_PERSIST_DIR),
            "config": {
                "chunk_size": knowledge_settings.CHUNK_SIZE,
                "embedding_model": knowledge_settings.EMBEDDING_MODEL_NAME,
                "embedding_dim": knowledge_settings.EMBEDDING_DIM,
            }
        }

    def rebuild_index(self):
        """重建索引（清空后重新开始）"""
        logger.info("重建索引...")
        self.chroma.rebuild()


_knowledge_manager = None


def get_knowledge_manager() -> KnowledgeManager:
    global _knowledge_manager
    if _knowledge_manager is None:
        _knowledge_manager = KnowledgeManager()
    return _knowledge_manager