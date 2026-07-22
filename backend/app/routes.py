from __future__ import annotations

import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, field_validator

from . import config
from .services.chunking import chunk_text
from .services.llm import generate_answer
from .services.pdf_extract import extract_text
from .services.vector_store import search, store_chunks

router = APIRouter()


class AskRequest(BaseModel):
    doc_id: Optional[str] = None
    question: str

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("question must not be empty")
        return v


class AskResponse(BaseModel):
    answer: str
    sources: List[dict]


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    doc_id = uuid.uuid4().hex
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    pdf_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}.pdf")
    with open(pdf_path, "wb") as out_file:
        out_file.write(await file.read())

    # No task queue in this version -- OCR-free extraction is fast enough
    # to run inline, but this does mean the request blocks until every
    # chunk is embedded and stored.
    text = extract_text(pdf_path)
    chunks = chunk_text(text, config.CHUNK_TOKENS, config.CHUNK_OVERLAP_TOKENS)
    stored = store_chunks(doc_id, chunks)

    return {"doc_id": doc_id, "chunks_stored": stored}


@router.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest):
    hits = search(body.question, top_k=config.RAG_TOP_K, doc_id=body.doc_id)
    if not hits:
        raise HTTPException(
            status_code=404, detail="No matching content found. Upload a document first."
        )

    context_chunks = [hit.get("text", "") for hit in hits]
    answer = await generate_answer(body.question, context_chunks)

    sources = [
        {
            "doc_id": hit.get("doc_id"),
            "chunk_index": hit.get("chunk_index"),
            "text_snippet": hit.get("text", "")[:200],
        }
        for hit in hits
    ]
    return {"answer": answer, "sources": sources}
