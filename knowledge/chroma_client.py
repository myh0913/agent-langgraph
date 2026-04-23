"""
ChromaDB 客户端
管理知识的存储和检索
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

import chromadb
from chromadb.config import Settings

from .config import knowledge_settings
from .embedder import get_embedder

logger = logging.getLogger(__name__)


class ChromaClient:
    """
    ChromaDB 知识库客户端
    嵌入式模式，数据持久化到本地
    """

    def __init__(
        self,
        persist_dir: str = None,
        collection_name: str = None
    ):
        self.persist_dir = Path(persist_dir or knowledge_settings.CHROMA_PERSIST_DIR)
        self.collection_name = collection_name or knowledge_settings.CHROMA_COLLECTION

        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = None
        self._collection = None
        self._embedder = None

    @property
    def client(self):
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            logger.info(f"ChromaDB 初始化完成: {self.persist_dir}")
        return self._client

    @property
    def embedder(self):
        if self._embedder is None:
            self._embedder = get_embedder()
        return self._embedder

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self._get_or_create_collection()
        return self._collection

    def _get_or_create_collection(self):
        """获取或创建 Collection"""
        try:
            return self.client.get_collection(name=self.collection_name)
        except Exception:
            logger.info(f"创建 Collection: {self.collection_name}")
            return self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Temp Agent Knowledge Base"}
            )

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        添加知识块到向量库

        Args:
            chunks: 分块列表，每块包含 id, content, metadata 等

        Returns:
            Dict: 成功/失败数量
        """
        if not chunks:
            return {"success": 0, "failed": 0}

        # 批量生成向量
        texts = [c["content"] for c in chunks]
        embeddings = self.embedder.embed_batch(texts)

        # 构建 ChromaDB 格式数据
        ids = [c["id"] for c in chunks]
        metadatas = []
        for c in chunks:
            tags = c.get("tags", [])
            if isinstance(tags, list):
                tags = ",".join(tags)
            
            metadatas.append({
                "source": c.get("source", ""),
                "category": c.get("category", ""),
                "tags": tags or "",
                "title": c.get("title", ""),
                "created_at": c.get("created_at", datetime.now().isoformat()),
            })

        # 写入
        try:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            logger.info(f"写入 ChromaDB: {len(chunks)} 条")
            return {"success": len(chunks), "failed": 0}
        except Exception as e:
            logger.error(f"写入失败: {e}")
            return {"success": 0, "failed": len(chunks)}

    def search(
        self,
        query: str,
        top_k: int = None,
        category: str = None,
        tags: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        语义搜索知识

        Args:
            query: 查询文本
            top_k: 返回条数
            category: 按分类过滤
            tags: 按标签过滤（支持多个，匹配任一即可）

        Returns:
            List[Dict]: 搜索结果
        """
        top_k = top_k or knowledge_settings.SEARCH_TOP_K

        # 生成查询向量
        query_embedding = self.embedder.embed(query)

        # 构建过滤条件（ChromaDB where 语法）
        filter_where = {}
        if category:
            filter_where["category"] = category

        try:
            # 执行搜索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_where if filter_where else None,
                include=["documents", "metadatas", "distances"]
            )

            # 格式化结果
            formatted = []
            
            # ChromaDB 返回格式: {"ids": [[...]], "documents": [[...]], "metadatas": [[...]], "distances": [[...]]}
            ids_list = results.get("ids", [[]])[0] or []
            docs_list = results.get("documents", [[]])[0] or []
            metas_list = results.get("metadatas", [[]])[0] or []
            dists_list = results.get("distances", [[]])[0] or []

            for i, doc_id in enumerate(ids_list):
                if i >= len(docs_list):
                    continue

                meta = metas_list[i] if i < len(metas_list) else {}
                tags_str = meta.get("tags", "") or ""
                
                # 过滤标签（如果指定了 tags，需要匹配任一）
                if tags:
                    tag_list = [t.strip() for t in tags_str.split(",") if t.strip()]
                    if not any(t in tag_list for t in tags):
                        continue

                # 距离转相似度（余弦距离：0=完全相同，2=完全相反）
                distance = dists_list[i] if i < len(dists_list) else 1.0
                score = max(0.0, 1.0 - distance / 2.0)  # 归一化到 0-1

                formatted.append({
                    "id": doc_id,
                    "content": docs_list[i],
                    "title": meta.get("title", ""),
                    "category": meta.get("category", ""),
                    "tags": [t for t in tags_str.split(",") if t],
                    "source": meta.get("source", ""),
                    "score": round(score, 4),
                    "created_at": meta.get("created_at", ""),
                })

            # 按分数排序
            formatted.sort(key=lambda x: x["score"], reverse=True)

            # 过滤低分结果
            min_score = knowledge_settings.SEARCH_SCORE_THRESHOLD
            formatted = [r for r in formatted if r["score"] >= min_score]

            return formatted

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    def delete_chunk(self, chunk_id: str) -> bool:
        """删除单个 Chunk"""
        try:
            self.collection.delete(ids=[chunk_id])
            return True
        except Exception as e:
            logger.error(f"删除失败 {chunk_id}: {e}")
            return False

    def count(self) -> int:
        """获取总条数"""
        try:
            return self.collection.count()
        except Exception:
            return 0

    def clear(self):
        """清空 Collection（重建）"""
        try:
            self.client.delete_collection(self.collection_name)
            self._collection = None
            logger.info("Collection 已清空")
        except Exception as e:
            logger.error(f"清空失败: {e}")

    def rebuild(self):
        """重建 Collection"""
        self.clear()
        self._collection = self._get_or_create_collection()
        logger.info("Collection 已重建")


# 全局单例
_chroma_client = None


def get_chroma_client() -> ChromaClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = ChromaClient()
    return _chroma_client