from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .llm import chat_with_citations


def _fallback_answer(doc_id: str, question: str) -> Tuple[str, float]:
    return f"No evidence found in [{doc_id}]. The document may still be processing.", 0.0


async def qa(doc_id: str, question: str) -> Tuple[str, float, List[Dict[str, Any]]]:
    hits: List[Dict[str, Any]] = []
    try:
        from .qdrant import search_spans
        hits = search_spans(doc_id, question, top_k=6) or []
    except Exception:
        hits = []

    if not hits:
        text, conf = _fallback_answer(doc_id, question)
        return text, conf, []

    evidence_lines = []
    for h in hits[:4]:
        chip = f"{doc_id}:{h.get('page', 1)}:{h.get('start', 0)}-{h.get('end', 0)}"
        evidence_lines.append(f'- "{h.get("text", "")}" [{chip}]')

    system = (
        "Answer briefly using only the provided evidence. "
        "Always cite sources like [D:page:start-end]. If uncertain, say Unknown."
    )
    prompt = f"Question: {question}\nEvidence:\n" + "\n".join(evidence_lines)

    try:
        text, conf = await chat_with_citations(system, prompt)
        if not text:
            text, conf = _fallback_answer(doc_id, question)
    except Exception:
        text, conf = _fallback_answer(doc_id, question)

    return text, conf, hits
