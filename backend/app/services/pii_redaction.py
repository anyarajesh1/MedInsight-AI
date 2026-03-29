"""
Privacy-first: redact PII (names, phone numbers) from text before processing.
Used on extracted document text before sending to RAG.
"""
import re
from typing import Optional

# Optional: use presidio for better name/entity detection
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False


# Phone number patterns (US and generic international)
PHONE_PATTERNS = [
    r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",  # 123-456-7890
    r"\b\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b",  # (123) 456-7890
    r"\b\d{10,11}\b",  # 10–11 digit run
]

PHONE_REGEX = re.compile("|".join(f"({p})" for p in PHONE_PATTERNS))


def redact_phones(text: str) -> str:
    """Replace phone numbers with [REDACTED-PHONE]."""
    return PHONE_REGEX.sub("[REDACTED-PHONE]", text)


def redact_with_presidio(text: str, language: str = "en") -> str:
    """Use Presidio to detect and redact PII (names, etc.)."""
    if not PRESIDIO_AVAILABLE:
        return text
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()
    results = analyzer.analyze(text=text, language=language)
    # Redact: PERSON, PHONE_NUMBER, etc.
    operator = OperatorConfig("replace", {"new_value": "[REDACTED]"})
    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators={"PERSON": operator, "PHONE_NUMBER": operator},
    )
    return anonymized.text


def redact_names_regex(text: str) -> str:
    """
    Fallback: simple pattern to reduce obvious 'Name: John Smith' style content.
    Not as accurate as NER; use presidio when available.
    """
    # Common lab report patterns: "Patient: X", "Name: X", "DOB:"
    patterns = [
        (re.compile(r"(Patient|Name|Patient Name)\s*:\s*[A-Za-z\s\-']+", re.I), r"\1: [REDACTED]"),
        (re.compile(r"(DOB|Date of Birth)\s*:\s*[\d/\-\.]+", re.I), r"\1: [REDACTED]"),
        (re.compile(r"(MRN|Medical Record #)\s*:\s*\S+", re.I), r"\1: [REDACTED]"),
    ]
    out = text
    for pattern, repl in patterns:
        out = pattern.sub(repl, out)
    return out


def redact_pii(text: str, use_presidio: bool = True) -> str:
    """
    Redact PII from text before processing.
    - Phone numbers: always redacted via regex.
    - Names/entities: via Presidio if available, else regex fallbacks.
    """
    if not text or not text.strip():
        return text
    out = redact_phones(text)
    if use_presidio and PRESIDIO_AVAILABLE:
        out = redact_with_presidio(out)
    else:
        out = redact_names_regex(out)
    return out
