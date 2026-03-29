"""
RAG service: query medical dictionary + user document chunks; return focused answer with Sources.
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.llms import Ollama

from app.core.config import settings
from app.services.vector_store import (
    get_medical_vector_store,
    get_documents_vector_store,
    get_all_document_chunks,
)
from app.services.lab_extractor import extract_lab_results_from_document


# Prompt for when LLM is available
CITATION_PROMPT = """You are a helpful medical information assistant. Use ONLY the following context to answer the question.

- If the user asks about ONE specific lab (e.g. creatinine, glucose): focus only on that lab, explain what their value means, and how they can improve.
- If the user asks about ALL their results / full report / summary: provide a clear summary of each relevant lab mentioned in their document, with brief interpretation for each.

Every response MUST end with a "Source" section citing the medical database references from the context.

Context:
{context}

Question: {question}

Answer (include "Source" at the end):"""


def _get_llm():
    try:
        return Ollama(model="llama3.2", temperature=0.2)
    except Exception:
        return None


def _merge_stores():
    medical = get_medical_vector_store()
    docs_store = get_documents_vector_store()
    return medical, docs_store


def _load_medical_dict() -> List[Dict]:
    path = settings.data_dir / "medical_dictionary_sample.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _is_asking_about_all(question: str) -> bool:
    """Detect if user wants a summary of all their results, not a single lab."""
    q = question.lower().strip()
    all_keywords = [
        "all my", "all of my", "my results", "my labs", "my lab results",
        "my report", "my lab report", "entire", "full report", "full results",
        "summary", "summarize", "overall", "everything", "each of",
        "what do my", "explain my", "interpret my", "review my",
        "all the", "all these", "each result", "every result",
    ]
    return any(k in q for k in all_keywords)


# Aliases: user phrases -> canonical term(s). "cholesterol" high -> LDL; "cholesterol" low -> HDL
TERM_ALIASES = {
    "cholesterol": "LDL Cholesterol",
    "cholestrol": "LDL Cholesterol",
    "bad cholesterol": "LDL Cholesterol",
    "good cholesterol": "HDL Cholesterol",
    "blood sugar": "Glucose",
    "sugar": "Glucose",
    "kidney": "Creatinine",
    "kidney function": "eGFR",
    "gfr": "eGFR",
    "thyroid": "TSH",
    "a1c": "HbA1c",
    "diabetes test": "HbA1c",
    "vitamin d": "Vitamin D",
    "vit d": "Vitamin D",
    "anemia": "Hemoglobin",
    "iron": "Ferritin",
    "white blood": "WBC",
    "red blood": "RBC",
    "liver": "ALT",
    "liver function": "ALT",
    "triglycerides": "Triglycerides",
    "trigs": "Triglycerides",
    "total chol": "Total Cholesterol",
    "sodium": "Sodium",
    "potassium": "Potassium",
    "calcium": "Calcium",
    "b12": "Vitamin B12",
    "vitamin b12": "Vitamin B12",
    "platelets": "Platelets",
    "inflammation": "CRP",
    "crp": "CRP",
}


def _extract_term_from_question(question: str, terms: List[str]) -> Optional[str]:
    """Extract the primary term from question, using aliases and exact matches."""
    q = question.lower()
    for alias, canonical in TERM_ALIASES.items():
        if alias in q and canonical in terms:
            return canonical
    for t in terms:
        if t.lower() in q:
            return t
    return None


def _extract_direction_from_question(question: str) -> Optional[str]:
    """Extract high/low from question when user describes without a numeric value."""
    q = question.lower()
    if any(w in q for w in ["high", "elevated", "raised", "too high", "increase"]):
        return "high"
    if any(w in q for w in ["low", "decreased", "drop", "too low", "reduce", "deficiency"]):
        return "low"
    return None


def _extract_value_from_question(question: str) -> Optional[float]:
    # Match numbers like 0.49, 5.2, 140, etc.
    m = re.search(r"\b(\d+\.?\d*)\b", question)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _is_low_or_high(term_entry: Dict, value: float) -> str:
    """Return 'low', 'high', or 'normal' based on typical ranges."""
    term = term_entry.get("term", "").lower()
    normal = term_entry.get("normal_range", "").lower()

    # Simple heuristics for common labs
    if "creatinine" in term:
        if value < 0.5:
            return "low"
        if value > 1.2:
            return "high"
    elif "glucose" in term or "blood sugar" in term:
        if value < 70:
            return "low"
        if value >= 100:
            return "high"
    elif "ldl" in term or "cholesterol" in term:
        if value > 100:
            return "high"
    elif "hdl" in term:
        if value < 40:
            return "low"
    elif "hba1c" in term or "a1c" in term:
        if value >= 5.7:
            return "high"
    elif "egfr" in term or "gfr" in term:
        if value < 90:
            return "low"
    elif "bun" in term:
        if value > 20:
            return "high"
        if value < 7:
            return "low"
    elif "tsh" in term:
        if value < 0.4:
            return "low"
        if value > 4.0:
            return "high"
    elif "vitamin d" in term or "vit d" in term:
        if value < 30:
            return "low"

    return "normal"


def _clean_doc_snippet(text: str, max_len: int = 200) -> str:
    """Remove OCR artifacts and shorten."""
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len] + "..."
    return cleaned


def _build_summary_answer(
    question: str,
    docs_med: List[Any],
    docs_user: List[Any],
    sources: List[Dict[str, str]],
) -> str:
    """Build a summary of all lab results when user asks about their full report.
    Only includes labs we actually extracted from the document—never inferred."""
    entries = _load_medical_dict()
    entry_by_term = {e.get("term", ""): e for e in entries if e.get("term")}

    # Use ALL document chunks to comb through the entire PDF
    all_chunks = get_all_document_chunks()
    if not all_chunks:
        all_chunks = docs_user

    extracted = extract_lab_results_from_document(all_chunks)

    if not extracted:
        return (
            "I couldn't find lab results with clear values in your uploaded document. "
            "Make sure your PDF contains lab test names and their numeric results. "
            "You can also ask about a specific test (e.g., 'What does my creatinine mean?')."
        )

    found_terms = []
    for canonical, (value, status) in extracted.items():
        entry = entry_by_term.get(canonical)
        if entry:
            found_terms.append((entry, value, status))

    source_refs = list({e.get("source", "Medical database") for e, _, _ in found_terms})
    parts = [
        "Summary of your lab results (extracted from your document):\n",
    ]

    for entry, value, status in found_terms:
        term = entry["term"]
        definition = entry.get("definition", "")
        normal_range = entry.get("normal_range", "")

        section = f"{term}\n{definition}\nNormal range: {normal_range}"
        if value is not None:
            section += f"\nYour value: {value}"
        if status:
            section += f" ({status})"
            if status == "low" and entry.get("low_interpretation"):
                section += f"\n  → {entry['low_interpretation'][:200]}"
                if entry.get("recommendations_low"):
                    section += f" {entry['recommendations_low'][:150]}..."
            elif status == "high" and entry.get("high_interpretation"):
                section += f"\n  → {entry['high_interpretation'][:200]}"
                if entry.get("recommendations_high"):
                    section += f" {entry['recommendations_high'][:150]}..."
        parts.append(section + "\n")

    parts.append(f"\n---\nSource: {'; '.join(source_refs[:5])}")
    return "\n".join(parts)


def _build_focused_answer(
    question: str,
    docs_med: List[Any],
    docs_user: List[Any],
    sources: List[Dict[str, str]],
) -> str:
    """Build a focused, user-friendly answer without an LLM."""
    entries = _load_medical_dict()
    terms = [e.get("term", "") for e in entries if e.get("term")]

    term = _extract_term_from_question(question, terms)
    value = _extract_value_from_question(question)

    # If user didn't provide value, try to get it from their document
    if value is None and term:
        all_chunks = get_all_document_chunks() or docs_user
        extracted = extract_lab_results_from_document(all_chunks)
        for canonical, (v, _) in extracted.items():
            if canonical.lower() == term.lower():
                value = v
                break

    entry = None
    for e in entries:
        if e.get("term", "").lower() == (term or "").lower():
            entry = e
            break

    if not entry:
        # Fallback: use first relevant medical doc
        if docs_med:
            content = docs_med[0].page_content
            return (
                "Based on the medical database:\n\n"
                + content[:2000]
                + "\n\n---\nSource: " + "; ".join(s["source"] for s in sources[:3])
            )
        return "I couldn't find specific information about that in the medical database. Try asking about a specific lab value (e.g., creatinine, glucose, cholesterol)."

    definition = entry.get("definition", "")
    normal_range = entry.get("normal_range", "")
    source = entry.get("source", "Medical database")

    direction = _is_low_or_high(entry, value) if value is not None else _extract_direction_from_question(question)
    interpretation = ""
    recommendations = ""

    if direction == "low":
        interpretation = entry.get("low_interpretation", "")
        recommendations = entry.get("recommendations_low", "")
    elif direction == "high":
        interpretation = entry.get("high_interpretation", "")
        recommendations = entry.get("recommendations_high", "")
    elif "improve" in question.lower() or "lower" in question.lower() or "reduce" in question.lower():
        # User wants to improve/lower—often means high
        interpretation = entry.get("high_interpretation", "")
        recommendations = entry.get("recommendations_high", "")
    elif not direction and (entry.get("high_interpretation") or entry.get("low_interpretation")):
        # No direction: show both so user gets full picture
        lo = entry.get("low_interpretation", "")
        hi = entry.get("high_interpretation", "")
        interpretation = f"If low: {lo}\n\nIf high: {hi}" if lo and hi else (lo or hi)
        rec_lo = entry.get("recommendations_low", "")
        rec_hi = entry.get("recommendations_high", "")
        recommendations = f"If low: {rec_lo}\n\nIf high: {rec_hi}" if rec_lo and rec_hi else (rec_lo or rec_hi)

    parts = [
        f"What is {entry['term']}?\n{definition}",
        f"\nNormal range: {normal_range}",
    ]

    if value is not None:
        parts.append(f"\nYour value: {value}")
    if interpretation:
        parts.append(f"\n\nWhat this means for you: {interpretation}")
    if recommendations:
        parts.append(f"\n\nHow you can improve: {recommendations}")

    # Add brief relevant note from user's document if it mentions the term
    term_lower = (term or "").lower()
    for d in docs_user[:3]:
        content = d.page_content
        if term_lower in content.lower() and "normal range" in content.lower():
            snippet = _clean_doc_snippet(content, 150)
            if snippet and len(snippet) > 30:
                parts.append(f"\n\nFrom your lab report: {snippet}")
                break

    parts.append(f"\n\n---\nSource: {source}")
    return "\n".join(parts)


def get_sources_from_docs(docs: List[Any]) -> List[Dict[str, str]]:
    sources = []
    seen = set()
    for d in docs:
        meta = getattr(d, "metadata", None) or {}
        source = meta.get("source") or meta.get("term") or "Medical database"
        key = (source, meta.get("term", ""))
        if key not in seen:
            seen.add(key)
            sources.append({"source": source, "term": meta.get("term", "")})
    return sources


def query_rag(question: str, top_k: int = 6) -> Dict[str, Any]:
    medical_store, docs_store = _merge_stores()
    asking_about_all = _is_asking_about_all(question)
    docs_k = 12 if asking_about_all else top_k  # More chunks when summarizing full report
    retriever_med = medical_store.as_retriever(search_kwargs={"k": top_k})
    retriever_docs = docs_store.as_retriever(search_kwargs={"k": docs_k})

    docs_med = retriever_med.get_relevant_documents(question)
    docs_user = retriever_docs.get_relevant_documents(question)
    sources = get_sources_from_docs(docs_med + docs_user)

    llm = _get_llm()
    answer = None

    if llm:
        try:
            combined_context = "\n\n---\n\n".join(d.page_content for d in docs_med + docs_user)
            combined_context = combined_context[:4000]
            prompt = PromptTemplate(
                template=CITATION_PROMPT,
                input_variables=["context", "question"],
            )
            chain = LLMChain(llm=llm, prompt=prompt)
            result = chain({"context": combined_context, "question": question})
            answer = result.get("text", result.get("answer", ""))
        except Exception:
            pass

    if not answer:
        if asking_about_all:
            answer = _build_summary_answer(question, docs_med, docs_user, sources)
        else:
            answer = _build_focused_answer(question, docs_med, docs_user, sources)

    combined_context = "\n\n---\n\n".join(d.page_content for d in docs_med + docs_user)
    return {
        "answer": answer,
        "sources": sources,
        "technical_context_preview": combined_context[:1500] if combined_context else "",
    }
