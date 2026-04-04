"""
Test granite-docling-258M VLM extraction on dense-table PDFs.
First run downloads ibm-granite/granite-docling-258M-mlx (~500MB).

Run from repo root:
    uv run python demo-data/test_granite_vlm.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from amanat.tools.docling_tool import extract_text, parse_and_scan_document

files = [
    "demo-data/drive/Site_Population_Register_Scanned.pdf",
    "demo-data/drive/Biometric_Verification_Log_Scanned.pdf",
]

for f in files:
    print(f"\n{'='*60}")
    print(f"FILE: {Path(f).name}")
    print(f"{'='*60}")

    t0 = time.time()
    text = extract_text(f, use_vlm=True)
    elapsed = time.time() - t0

    print(f"Extracted {len(text)} chars in {elapsed:.1f}s")
    print("\n--- TEXT SAMPLE (first 800 chars) ---")
    print(text[:800])

    print("\n--- PII SCAN ---")
    result = parse_and_scan_document(f, use_vlm=True)
    data = json.loads(result.split("---JSON---")[1].strip())
    print(f"PII instances: {data['pii_instances']} across {data['pii_types']} types")
    print(f"Has critical:  {data['has_critical']}")
    print(f"Categories:    {', '.join(data['categories'])}")
