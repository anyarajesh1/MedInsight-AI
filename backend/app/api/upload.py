"""
Upload medical lab PDFs. Extract text (with OCR fallback), redact PII, chunk and add to vector store.
"""
import uuid

from fastapi import APIRouter, File, UploadFile, HTTPException

from app.services.pdf_ocr import extract_and_redact_pdf
from app.services.vector_store import get_documents_vector_store, get_text_splitter

router = APIRouter()


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        text, used_ocr = extract_and_redact_pdf(content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"PDF processing failed: {str(e)}")

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted. Ensure the PDF contains text or is a clear scanned image.",
        )

    splitter = get_text_splitter()
    chunks = splitter.split_text(text)
    if not chunks:
        raise HTTPException(status_code=422, detail="No content chunks after splitting")

    doc_id = str(uuid.uuid4())
    store = get_documents_vector_store()
    metadatas = [{"doc_id": doc_id, "chunk_idx": i, "used_ocr": used_ocr} for i in range(len(chunks))]
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    store.add_texts(texts=chunks, metadatas=metadatas, ids=ids)

    # Privacy-first: we do not persist the original PDF; only redacted text is stored in the vector DB.

    return {
        "doc_id": doc_id,
        "chunks_indexed": len(chunks),
        "used_ocr": used_ocr,
        "message": "Document processed with PII redaction and added to the knowledge base.",
    }
