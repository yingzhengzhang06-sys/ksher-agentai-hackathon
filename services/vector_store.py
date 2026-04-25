"""
向量数据库服务 — ChromaDB封装
用于RAG检索：将知识库文档向量化存储，支持语义检索
"""
import os
import hashlib
import glob
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

# ChromaDB
import chromadb
from chromadb.config import Settings

# Embedding模型
from sentence_transformers import SentenceTransformer

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class DocumentChunk:
    """文档分块数据结构"""
    id: str
    text: str
    metadata: Dict[str, Any]


class VectorStore:
    """
    向量数据库封装
    - 使用ChromaDB持久化存储
    - 使用sentence-transformers生成embedding
    - 支持知识库文档的增删改查
    """

    # 默认embedding模型（轻量级多语言模型，支持中英文）
    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # 分块大小（字符数）
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50

    def __init__(
        self,
        collection_name: str = "ksher_knowledge",
        db_path: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """
        初始化向量数据库

        Args:
            collection_name: ChromaDB集合名
            db_path: 数据库持久化路径，默认项目目录下的data/vector_db
            model_name: Embedding模型名
        """
        self.collection_name = collection_name
        self.db_path = db_path or os.path.join(PROJECT_ROOT, "data", "vector_db")
        self.model_name = model_name or self.DEFAULT_MODEL

        # 确保目录存在
        os.makedirs(self.db_path, exist_ok=True)

        # 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False),
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},  # 使用余弦相似度
        )

        # 延迟加载embedding模型（首次使用时加载）
        self._embedding_model: Optional[SentenceTransformer] = None

    @property
    def embedding_model(self) -> SentenceTransformer:
        """懒加载embedding模型"""
        if self._embedding_model is None:
            # 检查是否有本地缓存
            cache_dir = os.path.join(PROJECT_ROOT, "data", "models")
            os.makedirs(cache_dir, exist_ok=True)
            self._embedding_model = SentenceTransformer(
                self.model_name,
                cache_folder=cache_dir,
            )
        return self._embedding_model

    def _generate_embedding(self, texts: List[str]) -> List[List[float]]:
        """生成文本的embedding向量"""
        if not texts:
            return []
        embeddings = self.embedding_model.encode(
            texts,
            normalize_embeddings=True,  # L2归一化
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def _chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """
        将长文本分块（按段落优先，然后按字符切分）

        策略：
        1. 先按段落分割（\n\n）
        2. 段落过长则按句子分割
        3. 句子仍过长则按字符切分
        """
        chunk_size = chunk_size or self.CHUNK_SIZE
        overlap = overlap or self.CHUNK_OVERLAP

        # 先按段落分割
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # 如果当前段落本身就很长，需要进一步切分
            if len(para) > chunk_size * 1.5:
                # 按句子分割
                sentences = [s.strip() for s in para.split("。") if s.strip()]
                for sent in sentences:
                    sent += "。"
                    if len(current_chunk) + len(sent) < chunk_size:
                        current_chunk += sent
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sent
            else:
                if len(current_chunk) + len(para) < chunk_size:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text[:chunk_size]]

    def add_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: Optional[int] = None,
    ) -> int:
        """
        添加文档到向量数据库（自动分块）

        Args:
            doc_id: 文档唯一标识
            text: 文档内容
            metadata: 元数据（如来源文件、类别、Agent关联等）
            chunk_size: 分块大小

        Returns:
            添加的chunk数量
        """
        metadata = metadata or {}

        # 分块
        chunks = self._chunk_text(text, chunk_size)

        # 生成chunk ID和embedding
        chunk_ids = []
        chunk_texts = []
        chunk_metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            chunk_ids.append(chunk_id)
            chunk_texts.append(chunk)

            # 合并元数据
            meta = {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "doc_id": doc_id,
            }
            chunk_metadatas.append(meta)

        # 生成embedding并插入
        embeddings = self._generate_embedding(chunk_texts)

        self.collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=chunk_metadatas,
        )

        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        语义检索

        Args:
            query: 查询文本
            top_k: 返回结果数
            filters: 过滤条件（如 {"category": "faq"}）

        Returns:
            检索结果列表，每项包含text/score/metadata
        """
        query_embedding = self._generate_embedding([query])[0]

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters,
            include=["documents", "metadatas", "distances"],
        )

        # 格式化结果
        output = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                # cosine距离转相似度分数 (1 - distance)
                distance = results["distances"][0][i]
                score = 1.0 - distance  # 余弦相似度

                output.append({
                    "id": doc_id,
                    "text": results["documents"][0][i],
                    "score": round(score, 4),
                    "metadata": results["metadatas"][0][i],
                })

        return output

    def delete_document(self, doc_id: str) -> bool:
        """删除文档（删除该文档的所有chunk）"""
        try:
            self.collection.delete(where={"doc_id": doc_id})
            return True
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        count = self.collection.count()
        return {
            "collection_name": self.collection_name,
            "total_documents": count,
            "db_path": self.db_path,
            "model": self.model_name,
        }

    def list_documents(self) -> List[str]:
        """列出所有文档ID（去重）"""
        all_meta = self.collection.get(include=["metadatas"])
        if not all_meta["metadatas"]:
            return []
        doc_ids = set()
        for meta in all_meta["metadatas"]:
            doc_ids.add(meta.get("doc_id", "unknown"))
        return sorted(list(doc_ids))


class KnowledgeIndexer:
    """
    知识库批量索引器
    将knowledge/目录下的所有Markdown文件索引到向量数据库
    """

    # 文件路径 → 文档类别的映射规则
    CATEGORY_MAP = {
        "base/": "company",
        "b2c/": "product",
        "b2b/": "product",
        "service_trade/": "product",
        "products/": "product",
        "competitors/": "competitor",
        "operations/": "operations",
        "strategy/": "strategy",
        "demo_scenarios/": "demo",
        "video_center/": "training",
    }

    # Agent关联映射
    AGENT_MAP = {
        "company": ["speech", "proposal", "content", "knowledge"],
        "product": ["speech", "cost", "proposal", "knowledge"],
        "competitor": ["cost", "objection", "proposal"],
        "operations": ["knowledge", "objection"],
        "strategy": ["speech", "proposal", "content"],
        "demo": ["speech", "proposal"],
        "training": ["content", "knowledge"],
    }

    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.store = vector_store or VectorStore()

    def _detect_category(self, filepath: str) -> str:
        """根据文件路径检测文档类别"""
        for prefix, cat in self.CATEGORY_MAP.items():
            if prefix in filepath:
                return cat
        return "general"

    def _detect_agents(self, category: str) -> List[str]:
        """根据类别获取关联的Agent列表"""
        return self.AGENT_MAP.get(category, ["knowledge"])

    def index_file(self, filepath: str) -> int:
        """索引单个文件"""
        if not os.path.exists(filepath):
            return 0

        # 读取文件
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            return 0

        # 提取文件名和类别
        filename = os.path.basename(filepath)
        category = self._detect_category(filepath)
        agents = self._detect_agents(category)
        rel_path = os.path.relpath(filepath, PROJECT_ROOT)

        # 生成doc_id
        doc_id = hashlib.md5(rel_path.encode()).hexdigest()[:16]

        # 元数据
        metadata = {
            "source_file": rel_path,
            "filename": filename,
            "category": category,
            "agents": ",".join(agents),
        }

        # 添加到向量数据库
        chunk_count = self.store.add_document(
            doc_id=doc_id,
            text=content,
            metadata=metadata,
        )

        return chunk_count

    def index_directory(self, knowledge_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        批量索引知识库目录下的所有Markdown文件

        Returns:
            {"indexed": int, "skipped": int, "chunks": int, "errors": List[str]}
        """
        knowledge_dir = knowledge_dir or os.path.join(PROJECT_ROOT, "knowledge")

        # 查找所有.md文件（排除隐藏文件）
        pattern = os.path.join(knowledge_dir, "**", "*.md")
        files = glob.glob(pattern, recursive=True)
        files = [f for f in files if not os.path.basename(f).startswith(".")]

        indexed = 0
        skipped = 0
        total_chunks = 0
        errors = []

        for filepath in sorted(files):
            try:
                chunk_count = self.index_file(filepath)
                if chunk_count > 0:
                    indexed += 1
                    total_chunks += chunk_count
                else:
                    skipped += 1
            except Exception as e:
                errors.append(f"{filepath}: {str(e)}")
                skipped += 1

        return {
            "indexed": indexed,
            "skipped": skipped,
            "chunks": total_chunks,
            "errors": errors,
        }


def get_vector_store() -> VectorStore:
    """获取全局向量数据库实例（单例模式）"""
    if not hasattr(get_vector_store, "_instance"):
        get_vector_store._instance = VectorStore()
    return get_vector_store._instance


# ──────────────────────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────────────────────
def search_knowledge(query: str, top_k: int = 5, category: Optional[str] = None) -> List[Dict]:
    """快速搜索知识库"""
    store = get_vector_store()
    filters = {"category": category} if category else None
    return store.search(query, top_k=top_k, filters=filters)


def index_all_knowledge() -> Dict[str, Any]:
    """批量索引所有知识库文件"""
    indexer = KnowledgeIndexer()
    return indexer.index_directory()


# ──────────────────────────────────────────────────────────────
# 测试
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("VectorStore 测试")
    print("=" * 60)

    # 1. 测试向量数据库
    store = VectorStore()
    stats = store.get_stats()
    print(f"\n数据库状态: {stats}")

    # 2. 测试添加文档
    test_doc = """
# Ksher 泰国收款产品

Ksher在泰国持有央行支付牌照，支持泰铢（THB）本地收款。
费率：B2C标准0.80%，B2B标准0.40%
到账时效：T+1
最低手续费：15泰铢/笔

## 优势
- 本地牌照：Bank of Thailand颁发的支付牌照
- 本地账户：与SCB等泰国本地银行合作
- 快速到账：T+1工作日
"""
    chunks = store.add_document(
        doc_id="test_thailand",
        text=test_doc,
        metadata={"category": "product", "agents": "speech,cost"},
    )
    print(f"添加测试文档，分块数: {chunks}")

    # 3. 测试检索
    results = store.search("泰国收款费率是多少？", top_k=3)
    print(f"\n检索结果:")
    for r in results:
        print(f"  score={r['score']:.3f}: {r['text'][:80]}...")

    # 4. 批量索引（如果知识库目录存在）
    kb_dir = os.path.join(PROJECT_ROOT, "knowledge")
    if os.path.exists(kb_dir):
        print(f"\n开始批量索引知识库: {kb_dir}")
        indexer = KnowledgeIndexer(store)
        result = indexer.index_directory(kb_dir)
        print(f"索引完成: {result['indexed']}个文件, {result['chunks']}个chunks")
        if result["errors"]:
            print(f"错误: {result['errors'][:3]}")

        # 最终统计
        final_stats = store.get_stats()
        print(f"\n最终数据库状态: {final_stats}")
    else:
        print(f"\n知识库目录不存在: {kb_dir}")
