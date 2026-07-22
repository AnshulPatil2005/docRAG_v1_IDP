import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from app.main import app
from app.services.chunking import chunk_text

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_rejects_non_pdf():
    response = client.post(
        "/upload", files={"file": ("notes.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 400


def test_ask_rejects_blank_question():
    response = client.post("/ask", json={"question": "   "})
    assert response.status_code == 422


def test_chunk_text_windows_with_overlap():
    text = " ".join(f"word{i}" for i in range(100))
    chunks = chunk_text(text, chunk_tokens=20, overlap_tokens=5)
    assert len(chunks) > 1
    # consecutive windows share their overlapping tokens
    assert chunks[0].split()[-5:] == chunks[1].split()[:5]


def test_chunk_text_empty_input():
    assert chunk_text("", chunk_tokens=20, overlap_tokens=5) == []
