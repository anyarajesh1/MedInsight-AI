"""
ChromaDB vector store for medical dictionary (knowledge base) and user documents.
"""
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import settings


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )


def get_chroma_client():
    persist = str(settings.chroma_persist_dir)
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=persist,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_medical_vector_store():
    """Vector store for medical dictionary (ingested once)."""
    client = get_chroma_client()
    return Chroma(
        client=client,
        collection_name=settings.medical_collection_name,
        embedding_function=get_embeddings(),
    )


def get_documents_vector_store():
    """Vector store for user-uploaded document chunks."""
    client = get_chroma_client()
    return Chroma(
        client=client,
        collection_name=settings.documents_collection_name,
        embedding_function=get_embeddings(),
    )


def get_all_document_chunks():
    """Get all chunks from user documents (for full-document extraction)."""
    try:
        client = get_chroma_client()
        coll = client.get_or_create_collection(name=settings.documents_collection_name)
        data = coll.get(include=["documents", "metadatas"], limit=1000)
    except Exception:
        return []
    if not data or not data.get("documents"):
        return []
    from langchain_core.documents import Document
    metas = data.get("metadatas") or [{}] * len(data["documents"])
    return [
        Document(page_content=doc, metadata=meta or {})
        for doc, meta in zip(data["documents"], metas)
    ]


def get_text_splitter():
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


async def ensure_vector_store():
    """Ensure data dir and Chroma persist dir exist; optionally run medical ingest."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
