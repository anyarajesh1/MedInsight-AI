#!/usr/bin/env python3
"""
Test lab result extraction with sample document text.
Run: .venv/bin/python -m scripts.test_lab_extraction
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.lab_extractor import extract_lab_results_from_document


# Sample text similar to user's lab report (Creatinine 0.49 Low, etc.)
SAMPLE_DOC = """
Creatinine
Normal range: 0.50 - 0.96 mg/dL
0.49 Low

eGFR
Normal value: > OR = 60 mL/min/1.73m2
94

Glucose
Normal range: 65 - 99 mg/dL
85 Normal

HbA1c 5.2 % Normal
LDL 95
HDL 52
TSH 2.1
"""


class FakeDoc:
    def __init__(self, content):
        self.page_content = content


# Doc with BUN header but NO BUN value - should NOT extract BUN
SAMPLE_NO_BUN_VALUE = """
BUN (Blood Urea Nitrogen)
Normal range: 7 - 20 mg/dL

Creatinine
Normal range: 0.50 - 0.96 mg/dL
0.49 Low
"""


def main():
    chunks = [FakeDoc(SAMPLE_DOC)]
    results = extract_lab_results_from_document(chunks)
    print("Extracted lab results (sample 1):")
    for name, (value, status) in results.items():
        print(f"  {name}: {value} ({status})")

    assert "Creatinine" in results, "Should find Creatinine"
    cr = results["Creatinine"]
    assert cr[0] == 0.49, f"Creatinine value should be 0.49, got {cr[0]}"
    assert cr[1] == "low", f"Creatinine status should be low, got {cr[1]}"
    print("\n✓ Creatinine extraction OK")

    # BUN has no value - should NOT appear
    chunks2 = [FakeDoc(SAMPLE_NO_BUN_VALUE)]
    results2 = extract_lab_results_from_document(chunks2)
    print("\nExtracted (sample 2 - no BUN value):")
    for name, (value, status) in results2.items():
        print(f"  {name}: {value} ({status})")
    assert "BUN" not in results2, "Should NOT extract BUN when only ref range, no result"
    assert "Creatinine" in results2, "Should find Creatinine"
    print("✓ BUN correctly excluded when no value")

    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
