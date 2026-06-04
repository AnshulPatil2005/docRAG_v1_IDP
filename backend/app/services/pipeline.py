from __future__ import annotations

import os
from celery import chain, shared_task
from .ocr import run as ocr_run
from .embeddings import run as emb_run


@shared_task(name="app.services.pipeline.task_ocr")
def task_ocr(doc_id):
    return ocr_run(doc_id)


@shared_task(name="app.services.pipeline.task_emb")
def task_emb(doc_id):
    return emb_run(doc_id)


def _run_sync(doc_id: str):
    task_ocr(doc_id)
    task_emb(doc_id)
    return {"doc_id": doc_id, "mode": "sync"}


def enqueue_ingestion(doc_id: str):
    if os.getenv("PIPELINE_MODE", "async").lower() == "sync":
        return _run_sync(doc_id)
    try:
        return chain(
            task_ocr.si(doc_id),  # type: ignore
            task_emb.si(doc_id),  # type: ignore
        ).apply_async()
    except Exception:
        return _run_sync(doc_id)
