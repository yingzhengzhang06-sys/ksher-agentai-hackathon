"""
ChromaDB 向量存储封装

Collections:
- knowledge_base: 知识库向量索引
- content_history: 历史生成内容向量
- performance_memory: 内容效果记忆
"""
import logging
from typing import Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    ChromaDB 客户端封装。本地持久化，零外部依赖。
    """

    def __init__(self, persist_dir: str):
        self.persist_dir = persist_dir
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collections: dict = {}

    def _get_collection(self, collection_name: str):
        """获取或创建集合（缓存）"""
        if collection_name not in self._collections:
            self._collections[collection_name] = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[collection_name]

    def add(
        self,
        collection_name: str,
        documents: list[str],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ) -> dict:
        """
        向集合添加文档。

        ChromaDB 会自动使用内置的 embedding 函数（all-MiniLM-L6-v2）。
        """
        try:
            collection = self._get_collection(collection_name)
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids or [f"auto_{i}" for i in range(len(documents))],
            )
            return {"success": True, "count": len(documents), "error": ""}
        except Exception as e:
            logger.error(f"[VectorStore] add 失败 ({collection_name}): {e}")
            return {"success": False, "count": 0, "error": str(e)}

    def query(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 5,
        filters: Optional[dict] = None,
    ) -> list[dict]:
        """
        语义检索。

        Returns:
            [{"id": str, "document": str, "metadata": dict, "score": float}]
        """
        try:
            collection = self._get_collection(collection_name)
            results = collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=filters,
            )

            hits = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    hits.append({
                        "id": doc_id,
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                        "score": results["distances"][0][i] if results.get("distances") else 0.0,
                    })
            return hits
        except Exception as e:
            logger.error(f"[VectorStore] query 失败 ({collection_name}): {e}")
            return []

    def delete(self, collection_name: str, ids: list[str]) -> dict:
        """按 ID 删除文档。"""
        try:
            collection = self._get_collection(collection_name)
            collection.delete(ids=ids)
            return {"success": True, "error": ""}
        except Exception as e:
            logger.error(f"[VectorStore] delete 失败: {e}")
            return {"success": False, "error": str(e)}

    def count(self, collection_name: str) -> int:
        """获取集合文档数。"""
        try:
            collection = self._get_collection(collection_name)
            return collection.count()
        except Exception:
            return 0

    def peek(self, collection_name: str, limit: int = 5) -> list[dict]:
        """查看集合中的部分文档。"""
        try:
            collection = self._get_collection(collection_name)
            results = collection.peek(limit=limit)
            docs = []
            for i, doc_id in enumerate(results.get("ids", [])):
                docs.append({
                    "id": doc_id,
                    "document": results["documents"][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][i] if results.get("metadatas") else {},
                })
            return docs
        except Exception:
            return []
