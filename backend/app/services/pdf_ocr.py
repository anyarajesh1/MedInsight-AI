"""
Extract text from medical PDFs: native text first, then OCR for scanned pages.
"""
import io
from pathlib import Path
from typing import List, Tuple

from pypdf import PdfReader

from app.core.config import settings
from app.services.pii_redaction import redact_pii

# Optional OCR
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def extract_text_from_pdf_bytes(data: bytes) -> Tuple[str, bool]:
    """
    Extract text from PDF. If a page has no/minimal text, run OCR on that page.
    Returns (full_text, used_ocr).
    """
    reader = PdfReader(io.BytesIO(data))
    chunks: List[str] = []
    used_ocr = False

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = text.strip()
        # Heuristic: if very little text, treat as scanned and run OCR
        if len(text) < 100 and OCR_AVAILABLE:
            try:
                images = convert_from_path(
                    io.BytesIO(data),
                    first_page=i + 1,
                    last_page=i + 1,
                    dpi=200,
                )
                if images:
                    page_text = pytesseract.image_to_string(
                        images[0],
                        lang=settings.tesseract_lang,
                    )
                    if page_text.strip():
                        text = page_text.strip()
                        used_ocr = True
            except Exception:
                pass
        if text:
            chunks.append(text)

    full_text = "\n\n".join(chunks)
    return full_text, used_ocr


def extract_and_redact_pdf(data: bytes) -> Tuple[str, bool]:
    """
    Extract text from PDF (with OCR fallback), then redact PII.
    Returns (redacted_text, used_ocr).
    """
    full_text, used_ocr = extract_text_from_pdf_bytes(data)
    redacted = redact_pii(full_text)
    return redacted, used_ocr
