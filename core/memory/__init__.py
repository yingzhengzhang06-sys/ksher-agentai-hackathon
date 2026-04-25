"""
记忆系统统一入口 — MemoryManager

对外提供简洁接口：
- query(query_text, memory_types=[], top_k=5) → 检索相关记忆
- store(content, memory_type, category, metadata={}) → 存储记忆
- recall(material_id, days=7) → 按时间回溯事件记忆
- get_working_memory(session_id) → 获取会话级工作记忆
"""
import logging
import uuid
from typing import Any, Optional

from config import DATA_DIR

from .vector_store import VectorStore
from .short_term import ShortTermMemory
from .long_term import LongTermMemory
from .episodic import EpisodicMemory

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    记忆管理器 — 协调多种记忆类型的存取。

    初始化时自动创建所需的数据库表和向量集合。
    """

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or f"{DATA_DIR}/chroma"
        self.vector_store = VectorStore(persist_dir=self.persist_dir)
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.episodic = EpisodicMemory()

    # ---------- 查询接口 ----------

    def query(
        self,
        query_text: str,
        memory_types: Optional[list[str]] = None,
        top_k: int = 5,
        agent_name: Optional[str] = None,
    ) -> list[dict]:
        """
        语义检索记忆。

        默认同时检索向量库和长期记忆，按相关性排序。

        Args:
            query_text: 查询文本
            memory_types: 记忆类型过滤 ['semantic', 'episodic', 'content_history', ...]
            top_k: 返回条数
            agent_name: 可选的Agent过滤

        Returns:
            [{"content": str, "memory_type": str, "score": float, ...}]
        """
        memory_types = memory_types or ["semantic", "content_history"]
        results = []

        # 1. 向量检索（知识库 + 内容历史）
        for collection_name in self._map_to_collections(memory_types):
            hits = self.vector_store.query(collection_name, query_text, top_k=top_k)
            for hit in hits:
                results.append({
                    "content": hit["document"],
                    "memory_type": collection_name,
                    "score": hit["score"],
                    "metadata": hit.get("metadata", {}),
                })

        # 2. 长期记忆检索
        if "semantic" in memory_types:
            lt_results = self.long_term.query(query_text, top_k=top_k, agent_name=agent_name)
            results.extend(lt_results)

        # 按 score 降序，取 top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def recall(self, material_id: Optional[str] = None, days: int = 7, limit: int = 20) -> list[dict]:
        """
        回溯事件记忆。

        Args:
            material_id: 可选的素材ID过滤
            days: 回溯天数
            limit: 最大条数

        Returns:
            事件记忆列表
        """
        return self.episodic.recent_events(material_id=material_id, days=days, limit=limit)

    def get_working_memory(self, session_id: str) -> dict:
        """获取会话级工作记忆。"""
        return self.short_term.get(session_id)

    # ---------- 存储接口 ----------

    def store(
        self,
        content: str,
        memory_type: str,
        category: str,
        metadata: Optional[dict] = None,
        importance: float = 0.5,
    ) -> dict:
        """
        统一存储接口。

        Args:
            content: 记忆内容
            memory_type: 'episodic' | 'semantic' | 'procedural' | 'content_history' | 'performance'
            category: 分类标签，如 'content_performance', 'competitor', 'industry_trend'
            metadata: 额外元数据
            importance: 重要性评分 0-1

        Returns:
            {"success": bool, "embedding_id": str, "error": str}
        """
        metadata = metadata or {}
        embedding_id = str(uuid.uuid4())

        # 1. 存入向量库（所有类型都索引）
        collection = self._memory_type_to_collection(memory_type)
        vector_result = self.vector_store.add(
            collection_name=collection,
            documents=[content],
            metadatas=[{**metadata, "memory_type": memory_type, "category": category}],
            ids=[embedding_id],
        )
        if not vector_result["success"]:
            logger.error(f"[MemoryManager] 向量存储失败: {vector_result['error']}")

        # 2. 长期记忆持久化（semantic/episodic/performance）
        if memory_type in ("semantic", "episodic", "performance"):
            self.long_term.store(
                memory_type=memory_type,
                category=category,
                content=content,
                embedding_id=embedding_id,
                metadata=metadata,
                importance_score=importance,
            )

        # 3. 事件记忆记录（episodic）
        if memory_type == "episodic":
            self.episodic.record(
                event_type=category,
                description=content,
                material_id=metadata.get("material_id"),
                metadata=metadata,
            )

        logger.info(f"[MemoryManager] 存储记忆: {memory_type}/{category}, id={embedding_id}")
        return {"success": True, "embedding_id": embedding_id, "error": ""}

    def store_knowledge(self, chunks: list[dict]) -> dict:
        """
        批量存储知识库片段到向量索引。

        Args:
            chunks: [{"text": str, "source": str, "metadata": dict}]

        Returns:
            {"success": bool, "count": int, "error": str}
        """
        docs = [c["text"] for c in chunks]
        metas = [{"source": c.get("source", ""), **c.get("metadata", {})} for c in chunks]
        ids = [str(uuid.uuid4()) for _ in chunks]

        result = self.vector_store.add(
            collection_name="knowledge_base",
            documents=docs,
            metadatas=metas,
            ids=ids,
        )
        if result["success"]:
            logger.info(f"[MemoryManager] 知识库索引: {len(chunks)} 条")
        return result

    def set_working_memory(self, session_id: str, key: str, value: Any, ttl: int = 3600) -> None:
        """设置会话级工作记忆。"""
        self.short_term.set(session_id, key, value, ttl=ttl)

    # ---------- 内部辅助 ----------

    def _map_to_collections(self, memory_types: list[str]) -> list[str]:
        """记忆类型 → ChromaDB collection 名称映射。"""
        mapping = {
            "semantic": ["knowledge_base"],
            "content_history": ["content_history"],
            "performance": ["performance_memory"],
            "episodic": ["content_history", "performance_memory"],
            "procedural": ["knowledge_base"],
        }
        collections = set()
        for mt in memory_types:
            for c in mapping.get(mt, []):
                collections.add(c)
        return list(collections)

    def _memory_type_to_collection(self, memory_type: str) -> str:
        mapping = {
            "semantic": "knowledge_base",
            "content_history": "content_history",
            "performance": "performance_memory",
            "episodic": "content_history",
            "procedural": "knowledge_base",
        }
        return mapping.get(memory_type, "knowledge_base")


# 便捷函数：快速获取全局 MemoryManager 实例
_global_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    """获取全局 MemoryManager（单例）。"""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = MemoryManager()
    return _global_memory_manager
