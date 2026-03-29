"""
Query endpoint: run RAG and return answer with Source section.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.pii_redaction import redact_pii
from app.services.rag_service import query_rag

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


class SourceItem(BaseModel):
    source: str
    term: str = ""


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    technical_context_preview: str = ""


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")
    # Redact PII from question before processing (privacy-first)
    question = redact_pii(request.question.strip())
    try:
        result = query_rag(question)
        return QueryResponse(
            answer=result["answer"],
            sources=[SourceItem(source=s["source"], term=s.get("term", "")) for s in result["sources"]],
            technical_context_preview=result.get("technical_context_preview", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
