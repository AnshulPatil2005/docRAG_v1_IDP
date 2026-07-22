from __future__ import annotations

from typing import List, Optional

from sentence_transformers import SentenceTransformer

from .. import config

_model: Optional[SentenceTransformer] = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def embed(texts: List[str]) -> List[List[float]]:
    return get_model().encode(texts, normalize_embeddings=True).tolist()
