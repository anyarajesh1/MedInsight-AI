"""
Med Insight AI - FastAPI application entry point.
Privacy-first medical document analysis with RAG.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import upload, query, health
from app.core.config import settings
from app.services.vector_store import ensure_vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize vector store on startup."""
    await ensure_vector_store()
    yield
    # Optional: cleanup


app = FastAPI(
    title="Med Insight AI",
    description="Privacy-first medical document analysis with RAG and source citations",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PII redaction is applied in the upload/processing pipeline (see services)

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(query.router, prefix="/api", tags=["Query"])
