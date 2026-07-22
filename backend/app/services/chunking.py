from __future__ import annotations

from typing import List


def chunk_text(text: str, chunk_tokens: int, overlap_tokens: int) -> List[str]:
    """
    Flat token-based chunking: slide a fixed-size window of
    whitespace-separated tokens over the whole document with no awareness
    of section/heading boundaries. A chunk can freely straddle the
    abstract, methods, and references of a paper.
    """
    tokens = text.split()
    if not tokens:
        return []

    chunks: List[str] = []
    step = max(chunk_tokens - overlap_tokens, 1)
    for start in range(0, len(tokens), step):
        window = tokens[start : start + chunk_tokens]
        if not window:
            break
        chunks.append(" ".join(window))
        if start + chunk_tokens >= len(tokens):
            break
    return chunks
