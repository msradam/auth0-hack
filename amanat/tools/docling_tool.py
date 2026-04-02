"""
Docling-powered document parsing for Amanat.

Converts uploaded PDFs, DOCX, PPTX, and images into structured text,
then runs PII detection on the extracted content. This enables Amanat
to scan real humanitarian documents — situation reports, intake forms,
registration sheets — not just synthetic demo data.

Uses IBM's Docling library with the standard pipeline (CPU-compatible).
For scanned documents or image-heavy PDFs, the VLM pipeline with
granite-docling-258M provides superior table recognition.
"""

import json
import tempfile
from pathlib import Path

from amanat.tools.scanner import detect_pii_in_text


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".md", ".csv"}


def parse_and_scan_document(
    file_path: str,
    use_vlm: bool = False,
) -> str:
    """
    Parse a document with Docling and scan for PII.

    Args:
        file_path: Path to the document to parse.
        use_vlm: If True, use the VLM pipeline (granite-docling-258M)
                 for better table/image extraction. Requires more memory.

    Returns:
        Text report + JSON blob (---JSON--- separator) with findings.
    """
    path = Path(file_path)

    if not path.exists():
        return json.dumps({"error": f"File not found: {file_path}"})

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return json.dumps({
            "error": f"Unsupported file type: {suffix}. "
                     f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        })

    try:
        from docling.document_converter import DocumentConverter
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions,
            EasyOcrOptions,
        )
    except ImportError:
        return json.dumps({"error": "Docling not installed. Run: uv add docling"})

    try:
        if use_vlm:
            # VLM pipeline — granite-docling-258M for enhanced table/OCR
            from docling.pipeline.vlm_pipeline import VlmPipeline
            from docling.datamodel.pipeline_options import (
                VlmPipelineOptions,
                granite_picture_description,
            )
            options = VlmPipelineOptions()
            options.vlm_options = granite_picture_description
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: options,
                    InputFormat.IMAGE: options,
                }
            )
        else:
            # Standard pipeline — fast, CPU-compatible
            converter = DocumentConverter()

        result = converter.convert(str(path))
        doc = result.document

        # Export to markdown for human-readable text
        text_content = doc.export_to_markdown()

        # Also get page count if available
        page_count = len(doc.pages) if hasattr(doc, "pages") else "unknown"

    except Exception as e:
        return json.dumps({"error": f"Docling conversion failed: {e}"})

    if not text_content.strip():
        return json.dumps({
            "error": "Document converted but produced no text content. "
                     "The file may be empty or image-only without OCR support."
        })

    # Run PII detection on extracted text
    pii_findings = detect_pii_in_text(text_content)

    total_pii = sum(p["count"] for p in pii_findings)
    has_critical = any(p["severity"] == "critical" for p in pii_findings)
    categories = list(set(p["category"] for p in pii_findings))

    # Text report
    lines = [
        f"DOCUMENT SCAN: {path.name}",
        f"Pages: {page_count} | Extracted: {len(text_content):,} characters",
        f"PII found: {total_pii} instances across {len(pii_findings)} types",
        "",
    ]

    if pii_findings:
        lines.append("PII DETECTED:")
        for finding in pii_findings:
            severity_label = "🔴" if finding["severity"] == "critical" else "🟡"
            lines.append(
                f"  {severity_label} {finding['type']} ({finding['category']}) "
                f"— {finding['count']} instance(s)"
            )
            if finding.get("samples"):
                samples_preview = [str(s)[:40] for s in finding["samples"][:2]]
                lines.append(f"     Samples: {', '.join(samples_preview)}")
        lines.append("")
    else:
        lines.append("No PII detected in extracted text.")

    if has_critical:
        lines.append(
            "⚠ CRITICAL: This document contains special category data "
            "(medical, biometric, or ethnic/religious information). "
            "Handle with restricted access and explicit consent documentation."
        )

    lines.append("")
    lines.append("EXTRACTED TEXT PREVIEW (first 500 chars):")
    lines.append("─" * 40)
    lines.append(text_content[:500])
    lines.append("─" * 40)

    data = {
        "file": path.name,
        "pages": page_count,
        "text_length": len(text_content),
        "pii_found": len(pii_findings) > 0,
        "pii_types": len(pii_findings),
        "pii_instances": total_pii,
        "has_critical": has_critical,
        "categories": categories,
        "pii_findings": pii_findings,
        "text_preview": text_content[:1000],
    }

    lines.append("\n---JSON---")
    lines.append(json.dumps(data))
    return "\n".join(lines)
