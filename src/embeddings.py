"""向量嵌入引擎 — sentence-transformers 本地推理（首次加载 ~2s，后续毫秒级）"""
import numpy as np
from sentence_transformers import SentenceTransformer
from .config import EMBEDDING_MODEL

# 模块级单例缓存，避免重复加载
_model_cache: dict[str, SentenceTransformer] = {}


class EmbeddingEngine:
    """轻量语义嵌入引擎（多语言 MiniLM-L12, 118MB）"""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or EMBEDDING_MODEL

    @property
    def model(self) -> SentenceTransformer:
        if self.model_name not in _model_cache:
            _model_cache[self.model_name] = SentenceTransformer(self.model_name)
        return _model_cache[self.model_name]

    @property
    def dim(self) -> int:
        return self.model.get_sentence_embedding_dimension()  # noqa

    def embed(self, text: str) -> np.ndarray:
        return self.model.encode(text, normalize_embeddings=True)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, normalize_embeddings=True,
                                 show_progress_bar=len(texts) > 50)

    @staticmethod
    def similarity(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b))
