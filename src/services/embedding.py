# src/services/embedding.py
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from typing import List

_MODEL_NAME = "intfloat/multilingual-e5-base"


@lru_cache(maxsize=1)  # 애플리케이션 생명주기 동안 1회만 로딩
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(_MODEL_NAME)


def embed(text: str) -> List[float]:
    """
    문자열 → 768-차원 벡터(List[float])
    """
    model = _get_model()
    return model.encode(text, normalize_embeddings=True).tolist()
