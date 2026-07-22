from __future__ import annotations

from typing import List

import httpx

from .. import config

SYSTEM_PROMPT = (
    "You are a helpful assistant. Use the following context to answer the "
    "user's question. If the answer is not in the context, say you don't know."
)


async def generate_answer(question: str, context_chunks: List[str]) -> str:
    context = "\n---\n".join(context_chunks)
    prompt = f"Context:\n{context}\n\nQuestion: {question}"

    url = f"{config.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.0},
    }
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    return (data.get("message") or {}).get("content", "").strip()
