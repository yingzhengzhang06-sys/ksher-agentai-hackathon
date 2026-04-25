"""
记忆系统测试 — Week 2 验证

验证项：
1. VectorStore: add / query / count
2. MemoryManager: store / query / recall / store_knowledge
3. ShortTermMemory: set / get / TTL
4. LongTermMemory: store / query / get_by_category
5. EpisodicMemory: record / recent_events
6. EmbeddingService: encode / similarity
7. KnowledgeLoader: 向量检索模式
8. BaseAgent: memory_manager 注入
"""
import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.memory.vector_store import VectorStore
from core.memory.short_term import ShortTermMemory
from core.memory.long_term import LongTermMemory
from core.memory.episodic import EpisodicMemory
from core.memory import MemoryManager
from services.embedding_service import EmbeddingService, get_embedding_service


@pytest.fixture(autouse=True)
def clean_memory_dbs():
    """清理记忆系统数据库"""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    memory_db = os.path.join(data_dir, "memory.db")
    chroma_dir = os.path.join(data_dir, "chroma")

    for path in [memory_db]:
        if os.path.exists(path):
            os.remove(path)
    for d in [chroma_dir]:
        if os.path.exists(d):
            shutil.rmtree(d)

    yield


def _unique_mm():
    """创建使用唯一 ChromaDB 路径的 MemoryManager，避免测试间文件锁冲突"""
    import uuid
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    persist_dir = os.path.join(data_dir, f"chroma_test_{uuid.uuid4().hex[:8]}")
    return MemoryManager(persist_dir=persist_dir)


# ---------- VectorStore ----------

class TestVectorStore:
    def test_add_and_query(self):
        vs = VectorStore(persist_dir="/tmp/test_chroma")
        vs.add(
            collection_name="test_collection",
            documents=["Ksher 是东南亚跨境支付专家", "泰国 B2C 市场增长迅速"],
            ids=["doc1", "doc2"],
        )

        results = vs.query("test_collection", "东南亚支付", top_k=2)
        assert len(results) > 0
        assert "支付" in results[0]["document"] or "东南亚" in results[0]["document"]

    def test_query_empty_collection(self):
        vs = VectorStore(persist_dir="/tmp/test_chroma_empty")
        results = vs.query("empty", "test", top_k=5)
        assert results == []

    def test_count(self):
        vs = VectorStore(persist_dir="/tmp/test_chroma_count")
        vs.add(
            collection_name="count_test",
            documents=["doc1", "doc2"],
            ids=["id1", "id2"],
        )
        count = vs.count("count_test")
        assert count >= 2


# ---------- MemoryManager ----------

class TestMemoryManager:
    def test_store_and_query(self):
        mm = _unique_mm()
        mm.store(
            content="Ksher 泰国本地牌照优势：直接清算，费率低至 0.4%",
            memory_type="semantic",
            category="competitor",
            metadata={"agent_name": "content"},
            importance=0.8,
        )

        results = mm.query("泰国跨境支付牌照", memory_types=["semantic"], top_k=3)
        assert len(results) > 0
        assert "泰国" in results[0]["content"] or "牌照" in results[0]["content"]

    def test_store_knowledge(self):
        mm = _unique_mm()
        result = mm.store_knowledge([
            {"text": "B2C 跨境电商退货率约 15%", "source": "industry_report", "metadata": {"year": "2026"}},
            {"text": "泰国消费者偏好移动支付", "source": "payment_survey", "metadata": {"country": "thailand"}},
        ])
        assert result["success"] is True
        assert result["count"] == 2

        # 验证可检索
        hits = mm.query("泰国移动支付", memory_types=["semantic"], top_k=2)
        assert len(hits) > 0

    def test_recall_events(self):
        mm = _unique_mm()
        mm.store(
            content="2026-04-22 生成朋友圈素材：泰国B2C主题",
            memory_type="episodic",
            category="content_generation",
            metadata={"material_id": "2026-W17-1"},
        )

        events = mm.recall(material_id="2026-W17-1", days=1)
        assert len(events) >= 1

    def test_working_memory(self):
        mm = _unique_mm()
        mm.set_working_memory("session_001", "current_theme", "泰国B2C", ttl=3600)
        wm = mm.get_working_memory("session_001")
        assert wm.get("current_theme") == "泰国B2C"


# ---------- ShortTermMemory ----------

class TestShortTermMemory:
    def test_set_and_get(self):
        stm = ShortTermMemory()
        stm.set("session_1", "key1", "value1", ttl=3600)
        result = stm.get("session_1")
        assert result["key1"] == "value1"

    def test_ttl_expiration(self):
        import time
        stm = ShortTermMemory()
        stm.set("session_2", "key2", "value2", ttl=1)
        time.sleep(1.1)
        result = stm.get("session_2")
        assert "key2" not in result

    def test_clear_session(self):
        stm = ShortTermMemory()
        stm.set("session_3", "key", "val", ttl=3600)
        stm.clear_session("session_3")
        result = stm.get("session_3")
        assert result == {}


# ---------- LongTermMemory ----------

class TestLongTermMemory:
    def test_store_and_query(self):
        lt = LongTermMemory()
        lt.store(
            memory_type="semantic",
            category="industry_trend",
            content="2026年东南亚跨境电商增长率预计达到 25%",
            importance_score=0.9,
        )

        results = lt.query("东南亚电商增长", top_k=5)
        assert len(results) > 0
        assert any("25%" in r["content"] for r in results)

    def test_get_by_category(self):
        lt = LongTermMemory()
        lt.store(
            memory_type="semantic",
            category="test_category",
            content="测试内容",
        )
        items = lt.get_by_category("test_category")
        assert len(items) >= 1
        assert items[0]["category"] == "test_category"


# ---------- EpisodicMemory ----------

class TestEpisodicMemory:
    def test_record_and_recent(self):
        em = EpisodicMemory()
        em.record(
            event_type="content_published",
            description="素材 2026-W17-1 已发布到朋友圈",
            material_id="2026-W17-1",
        )

        events = em.recent_events(material_id="2026-W17-1", days=1)
        assert len(events) >= 1
        assert events[0]["event_type"] == "content_published"

    def test_events_by_type(self):
        em = EpisodicMemory()
        em.record(event_type="competitor_alert", description="竞品 PingPong 发布新活动")
        items = em.get_events_by_type("competitor_alert", limit=10)
        assert len(items) >= 1


# ---------- EmbeddingService ----------

class TestEmbeddingService:
    def test_encode_single(self):
        svc = EmbeddingService()
        vec = svc.encode_single("Ksher 东南亚支付")
        assert vec is not None
        assert len(vec) > 0
        assert isinstance(vec[0], float)

    def test_similarity(self):
        svc = EmbeddingService()
        sim = svc.similarity("Ksher 泰国支付", "泰国跨境收款")
        assert sim > 0.3  # 语义相关

        sim_diff = svc.similarity("Ksher 泰国支付", "深度学习神经网络")
        assert sim_diff < sim  # 不相关

    def test_singleton(self):
        svc1 = EmbeddingService()
        svc2 = EmbeddingService()
        assert svc1 is svc2


# ---------- KnowledgeLoader + 向量检索 ----------

class TestKnowledgeLoaderVector:
    def test_vector_knowledge_query(self):
        from services.knowledge_loader import KnowledgeLoader

        mm = _unique_mm()
        mm.store_knowledge([
            {"text": "泰国 B2C 市场消费者偏好 Lazada 和 Shopee", "source": "market_report"},
        ])

        loader = KnowledgeLoader(memory_manager=mm)
        # _query_vector_knowledge 是内部方法，通过 load 间接调用
        # 由于 load 依赖文件系统，这里直接测试 _query_vector_knowledge
        result = loader._query_vector_knowledge("content", {"industry": "b2c", "target_country": "thailand"})
        assert result is not None
        assert len(result) > 0
        assert "泰国" in result or "B2C" in result

    def test_no_memory_manager_returns_none(self):
        from services.knowledge_loader import KnowledgeLoader
        loader = KnowledgeLoader()
        result = loader._query_vector_knowledge("content", {"industry": "b2c"})
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
