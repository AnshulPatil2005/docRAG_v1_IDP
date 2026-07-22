from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from .. import config
from .embeddings import embed

_client: Optional[QdrantClient] = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=config.QDRANT_URL)
    return _client


def ensure_collection() -> None:
    client = get_client()
    existing = {c.name for c in client.get_collections().collections}
    if config.QDRANT_COLLECTION not in existing:
        client.create_collection(
            config.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=config.EMBEDDING_DIM, distance=Distance.COSINE),
        )


def _point_id(doc_id: str, chunk_index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc_id}::{chunk_index}"))


def store_chunks(doc_id: str, chunks: List[str]) -> int:
    if not chunks:
        return 0
    ensure_collection()
    vectors = embed(chunks)
    points = [
        PointStruct(
            id=_point_id(doc_id, i),
            vector=vectors[i],
            payload={"doc_id": doc_id, "chunk_index": i, "text": chunks[i]},
        )
        for i in range(len(chunks))
    ]
    get_client().upsert(collection_name=config.QDRANT_COLLECTION, points=points, wait=True)
    return len(points)


def search(query: str, top_k: int, doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
    ensure_collection()
    vector = embed([query])[0]
    query_filter = None
    if doc_id:
        query_filter = Filter(must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))])
    hits = get_client().search(
        collection_name=config.QDRANT_COLLECTION,
        query_vector=vector,
        query_filter=query_filter,
        limit=top_k,
        with_payload=True,
    )
    return [hit.payload or {} for hit in hits]
