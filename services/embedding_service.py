"""
Embedding 服务 — 本地 sentence-transformers 封装

使用 all-MiniLM-L6-v2 模型，22MB，无外部 API 依赖。
支持文本 → 向量，用于语义检索。
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 模型名（22MB，本地缓存）
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingService:
    """
    本地 Embedding 生成器。

    首次使用时会自动下载模型（约 22MB）。
    """

    _instance = None
    _model = None

    def __new__(cls, model_name: str = DEFAULT_MODEL):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.model_name = model_name
            cls._instance._model = None
        return cls._instance

    def _load_model(self):
        """懒加载模型"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"[EmbeddingService] 加载模型: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                logger.info("[EmbeddingService] 模型加载完成")
            except Exception as e:
                logger.error(f"[EmbeddingService] 模型加载失败: {e}")
                raise
        return self._model

    def encode(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        将文本列表编码为向量。

        Args:
            texts: 文本列表
            batch_size: 批大小

        Returns:
            向量列表（每个向量 384 维）
        """
        model = self._load_model()
        if not texts:
            return []
        # 过滤空文本
        texts = [t.strip() for t in texts if t and t.strip()]
        if not texts:
            return []
        embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
        return embeddings.tolist()

    def encode_single(self, text: str) -> Optional[list[float]]:
        """单条文本编码"""
        if not text or not text.strip():
            return None
        results = self.encode([text])
        return results[0] if results else None

    def similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的余弦相似度。

        Returns:
            相似度分数，范围 [-1, 1]
        """
        import numpy as np
        emb1 = self.encode_single(text1)
        emb2 = self.encode_single(text2)
        if emb1 is None or emb2 is None:
            return 0.0
        v1 = np.array(emb1)
        v2 = np.array(emb2)
        dot = np.dot(v1, v2)
        norm = np.linalg.norm(v1) * np.linalg.norm(v2)
        return float(dot / norm) if norm > 0 else 0.0


# 便捷函数
def get_embedding_service() -> EmbeddingService:
    """获取 EmbeddingService 单例"""
    return EmbeddingService()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """快捷编码文本列表"""
    return get_embedding_service().encode(texts)


def embed_text(text: str) -> Optional[list[float]]:
    """快捷编码单条文本"""
    return get_embedding_service().encode_single(text)
