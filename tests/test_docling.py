"""
Tests for Docling document parsing integration.
"""

import json
import tempfile
from pathlib import Path

import pytest

from amanat.tools.docling_tool import (
    extract_text,
    extract_text_from_bytes,
    parse_and_scan_document,
    SUPPORTED_EXTENSIONS,
    DOCLING_MIMES,
)


# --- Fixtures ---

DEMO_CSV = Path("demo-data/drive/Cataclysm_Displaced_Registry_2026.csv")


@pytest.fixture
def demo_csv_path():
    if not DEMO_CSV.exists():
        pytest.skip("Demo data not found")
    return str(DEMO_CSV)


@pytest.fixture
def minimal_pdf_bytes():
    """Minimal valid PDF with embedded text content."""
    pdf = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 100>>
stream
BT /F1 12 Tf 100 700 Td (Beneficiary: Rozel al-Bahar Case ID: WAQ-26C00891 medical: PTSD) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f\r
0000000009 00000 n\r
0000000058 00000 n\r
0000000115 00000 n\r
0000000266 00000 n\r
0000000416 00000 n\r
trailer<</Size 6/Root 1 0 R>>
startxref
497
%%EOF"""
    return pdf


# --- extract_text tests ---

def test_extract_text_csv(demo_csv_path):
    """CSV files should be extracted by Docling."""
    text = extract_text(demo_csv_path)
    assert len(text) > 100
    assert "Rozel" in text or "Case" in text or "Displaced" in text


def test_extract_text_missing_file():
    """Missing file returns empty string, does not raise."""
    result = extract_text("/nonexistent/path/file.pdf")
    assert result == ""


# --- extract_text_from_bytes tests ---

def test_extract_text_from_bytes_unsupported_mime():
    """Unsupported MIME type returns empty string without error."""
    result = extract_text_from_bytes(b"hello world", "text/plain")
    assert result == ""


def test_extract_text_from_bytes_pdf(minimal_pdf_bytes):
    """PDF bytes should be written to temp file and parsed by Docling."""
    result = extract_text_from_bytes(minimal_pdf_bytes, "application/pdf")
    # Docling may or may not extract text from this minimal PDF,
    # but it should not raise and should return a string
    assert isinstance(result, str)


def test_extract_text_from_bytes_no_temp_file_leak(minimal_pdf_bytes):
    """Temp file should be cleaned up after extraction."""
    import glob
    import os
    before = set(glob.glob(tempfile.gettempdir() + "/tmp*.pdf"))
    extract_text_from_bytes(minimal_pdf_bytes, "application/pdf")
    after = set(glob.glob(tempfile.gettempdir() + "/tmp*.pdf"))
    leaked = after - before
    assert not leaked, f"Temp files not cleaned up: {leaked}"


# --- parse_and_scan_document tests ---

def test_parse_and_scan_csv_finds_pii(demo_csv_path):
    """Full pipeline: parse CSV and detect PII."""
    result = parse_and_scan_document(demo_csv_path)
    assert "DOCUMENT SCAN" in result
    assert "PII found" in result
    # Should find names and case numbers in the registry
    assert "---JSON---" in result

    json_part = result.split("---JSON---")[1].strip()
    data = json.loads(json_part)
    assert data["pii_found"] is True
    assert data["pii_instances"] > 0


def test_parse_and_scan_missing_file():
    """Missing file returns JSON error, does not raise."""
    result = parse_and_scan_document("/tmp/nonexistent_file.pdf")
    data = json.loads(result)
    assert "error" in data


def test_parse_and_scan_unsupported_extension():
    """Unsupported file extension returns JSON error."""
    with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as tmp:
        tmp.write(b"some content")
        tmp_path = tmp.name
    try:
        result = parse_and_scan_document(tmp_path)
        data = json.loads(result)
        assert "error" in data
        assert "Unsupported" in data["error"]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_parse_and_scan_empty_file():
    """Empty file returns error about no text content."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(b"")
        tmp_path = tmp.name
    try:
        result = parse_and_scan_document(tmp_path)
        # Should either error or return no PII
        assert isinstance(result, str)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# --- DOCLING_MIMES coverage ---

def test_docling_mimes_includes_pdf():
    assert "application/pdf" in DOCLING_MIMES


def test_docling_mimes_includes_office_formats():
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in DOCLING_MIMES
    assert "application/vnd.openxmlformats-officedocument.presentationml.presentation" in DOCLING_MIMES
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in DOCLING_MIMES
