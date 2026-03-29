"""
Extract actual lab test results from document text.
Only returns labs where we found a clear (test_name, value, status) in the document.
"""
import re
from typing import List, Dict, Optional, Tuple

# Lab name variations -> (canonical_name, value_min, value_max for sanity check)
LAB_PATTERNS = [
    (["creatinine", "creatinine, serum"], "Creatinine", 0.1, 3.0),
    (["bun", "blood urea nitrogen", "urea nitrogen"], "BUN", 1, 100),
    (["egfr", "gfr", "glomerular filtration"], "eGFR", 5, 200),
    (["glucose", "blood glucose", "fasting glucose"], "Glucose", 20, 500),
    (["hdl", "hdl cholesterol", "hdl-c"], "HDL Cholesterol", 10, 150),
    (["ldl", "ldl cholesterol", "ldl-c"], "LDL Cholesterol", 20, 300),
    (["total cholesterol", "total chol"], "Total Cholesterol", 50, 400),
    (["triglycerides", "trigs"], "Triglycerides", 20, 600),
    (["hba1c", "hemoglobin a1c", "a1c", "glycated hemoglobin"], "HbA1c", 4.0, 15.0),
    (["tsh", "thyroid stimulating"], "TSH", 0.01, 100),
    (["hemoglobin", "hgb", "hb "], "Hemoglobin", 5, 25),
    (["alt", "alanine aminotransferase", "sgpt"], "ALT", 1, 500),
    (["ast", "aspartate aminotransferase", "sgot"], "AST", 1, 500),
    (["vitamin d", "vit d", "25-hydroxyvitamin", "25-oh vitamin d"], "Vitamin D", 1, 150),
    (["vitamin b12", "b12", "cobalamin"], "Vitamin B12", 50, 2000),
    (["potassium", "k+", "k +"], "Potassium", 2.0, 8.0),
    (["sodium", "na+", "na +"], "Sodium", 120, 160),
    (["calcium", "ca"], "Calcium", 6, 14),
    (["wbc", "white blood cell", "leukocyte"], "WBC", 0.5, 50),
    (["rbc", "red blood cell", "erythrocyte"], "RBC", 2, 8),
    (["platelet", "plt"], "Platelets", 10, 1000),
    (["ferritin"], "Ferritin", 1, 1000),
    (["crp", "c-reactive protein"], "CRP", 0.1, 200),
]


def _clean_text(text: str) -> str:
    """Remove OCR artifacts."""
    return re.sub(r"<[^>]+>", " ", text)


def _find_next_lab_position(text: str, start: int, current_patterns: List[str]) -> int:
    """Find the start of the next lab section (next lab name) after position start."""
    rest = text[start:start + 500]
    for names, _, _, _ in LAB_PATTERNS:
        for n in names:
            if n in rest.lower():
                idx = rest.lower().find(n)
                if idx > 30:  # Avoid same lab
                    return start + idx
    return start + len(rest)


def _extract_value_and_status(window: str, vmin: float, vmax: float) -> Tuple[Optional[float], Optional[str]]:
    """
    Extract the lab value and Low/High/Normal from a text window.
    Prefer the value closest to the status flag; exclude reference-range numbers.
    """
    wl = window.lower()
    status = None
    if " low" in wl or "low\n" in wl or "low " in wl or re.search(r"low(?:egfr|$|\s)", wl):
        status = "low"
    elif " high" in wl or "high\n" in wl or "high " in wl:
        status = "high"
    elif "normal" in wl or "within normal" in wl or "wnl" in wl:
        status = "normal"

    # Numbers to exclude: reference ranges, thresholds like "> 60", "7 - 20"
    ref_nums = set()
    for pat in [
        r"(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)",
        r"[>=]\s*(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*to\s*(\d+\.?\d*)",
        r"normal\s*range[:\s]*(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)",
    ]:
        for mo in re.finditer(pat, wl, re.I):
            for g in mo.groups():
                try:
                    ref_nums.add(float(g))
                except ValueError:
                    pass

    candidates: List[Tuple[float, int]] = []
    for m in re.finditer(r"\d+\.?\d*", window):
        try:
            v = float(m.group(0))
            if vmin <= v <= vmax and v not in ref_nums:
                candidates.append((v, m.start()))
        except ValueError:
            pass

    if not candidates:
        return None, status

    if status:
        status_pos = -1
        for pat in [" low", " high", " normal", "low", "high", "normal"]:
            idx = wl.find(pat)
            if idx >= 0 and (status_pos < 0 or idx < status_pos):
                status_pos = idx
        if status_pos >= 0:
            best = min(candidates, key=lambda x: abs(x[1] - status_pos))
            return best[0], status

    return candidates[0][0], status


def extract_lab_results_from_document(doc_chunks: List) -> Dict[str, Tuple[float, Optional[str]]]:
    """
    Extract lab results from document chunks. Returns only labs with an actual value found.
    Returns: {canonical_name: (value, status)}
    """
    full_text = "\n\n".join(
        getattr(c, "page_content", str(c)) if hasattr(c, "page_content") else str(c)
        for c in doc_chunks
    )
    full_text = _clean_text(full_text)
    results: Dict[str, Tuple[float, Optional[str]]] = {}

    for names, canonical, vmin, vmax in LAB_PATTERNS:
        if canonical in results:
            continue
        for name in names:
            idx = 0
            while True:
                pos = full_text.lower().find(name, idx)
                if pos < 0:
                    break
                # Window: from this lab name to the next lab name (or 250 chars)
                next_lab = _find_next_lab_position(full_text, pos + len(name), names)
                end = min(pos + 250, next_lab)
                window = full_text[pos:end]

                value, status = _extract_value_and_status(window, vmin, vmax)
                if value is not None:
                    results[canonical] = (value, status)
                    break
                idx = pos + 1
            if canonical in results:
                break

    return results
