#!/usr/bin/env python3
"""
Ingest medical dictionary (NIH/Mayo style) into ChromaDB for RAG.
Run from backend folder with venv activated. Use the venv's Python (not system):
  cd backend
  source .venv/bin/activate
  .venv/bin/python -m scripts.ingest_medical_dict
  # If 'python' is aliased to system Python, use .venv/bin/python as above.
"""
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from app.core.config import settings
except ImportError as e:
    print("Import error. Make sure you're in the backend folder and the venv is activated:")
    print("  cd backend")
    print("  source .venv/bin/activate")
    print("  pip install -r requirements.txt")
    print("  .venv/bin/python -m scripts.ingest_medical_dict")
    sys.exit(1)

from app.services.vector_store import (
    get_chroma_client,
    get_embeddings,
    get_text_splitter,
)


def load_medical_entries():
    data_path = settings.data_dir / "medical_dictionary_sample.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Medical dictionary not found: {data_path}")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    entries = load_medical_entries()
    text_splitter = get_text_splitter()
    embeddings = get_embeddings()
    client = get_chroma_client()

    collection_name = settings.medical_collection_name
    # Create or get collection
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "Medical dictionary (NIH/Mayo style)"},
    )

    ids = []
    documents = []
    metadatas = []

    for i, entry in enumerate(entries):
        term = entry.get("term", "")
        definition = entry.get("definition", "")
        source = entry.get("source", "Medical reference")
        category = entry.get("category", "")
        low_int = entry.get("low_interpretation", "")
        high_int = entry.get("high_interpretation", "")
        rec_low = entry.get("recommendations_low", "")
        rec_high = entry.get("recommendations_high", "")
        normal = entry.get("normal_range", "")
        parts = [f"Term: {term}\nDefinition: {definition}\nNormal range: {normal}\nSource: {source}"]
        if low_int:
            parts.append(f"Low: {low_int}\nRecommendations for low: {rec_low}")
        if high_int:
            parts.append(f"High: {high_int}\nRecommendations for high: {rec_high}")
        text = "\n".join(parts)
        chunk_id = f"med_{i}_{term.replace(' ', '_')[:30]}"
        ids.append(chunk_id)
        documents.append(text)
        metadatas.append({
            "term": term,
            "source": source,
            "category": category,
        })

    # Embed and add
    emb = embeddings.embed_documents(documents)
    collection.upsert(ids=ids, documents=documents, embeddings=emb, metadatas=metadatas)
    print(f"Ingested {len(ids)} medical dictionary entries into '{collection_name}'.")


if __name__ == "__main__":
    main()
