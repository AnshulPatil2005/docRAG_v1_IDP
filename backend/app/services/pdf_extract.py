from __future__ import annotations

import fitz  # PyMuPDF


def extract_text(pdf_path: str) -> str:
    """
    Extracts the text layer from every page and concatenates it into one
    string. Pure PyMuPDF, no OCR fallback -- a scanned/image-only PDF will
    yield little or no text.
    """
    doc = fitz.open(pdf_path)
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()
