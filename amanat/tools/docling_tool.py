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

DOCLING_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword",
    "application/vnd.ms-powerpoint",
    "application/vnd.ms-excel",
}

MIME_TO_EXT = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/msword": ".doc",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.ms-excel": ".xls",
}


def extract_text(file_path: str, use_vlm: bool = False) -> str:
    """
    Extract text from a document using Docling. Returns raw markdown text.
    Does not run PII detection — use this when you need just the text.

    Returns empty string if extraction fails or produces no content.
    """
    path = Path(file_path)
    if not path.exists():
        return ""

    try:
        from docling.document_converter import DocumentConverter
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        if use_vlm:
            from docling.document_converter import PdfFormatOption
            from docling.pipeline.vlm_pipeline import VlmPipeline
            from docling.datamodel.pipeline_options import (
                VlmPipelineOptions,
                VlmConvertOptions,
            )
            from docling.datamodel.vlm_engine_options import MlxVlmEngineOptions
            vlm_opts = VlmConvertOptions.from_preset(
                "granite_docling",
                engine_options=MlxVlmEngineOptions(),
            )
            pipeline_opts = VlmPipelineOptions()
            pipeline_opts.vlm_options = vlm_opts
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_cls=VlmPipeline,
                        pipeline_options=pipeline_opts,
                    ),
                    InputFormat.IMAGE: PdfFormatOption(
                        pipeline_cls=VlmPipeline,
                        pipeline_options=pipeline_opts,
                    ),
                }
            )
        else:
            converter = DocumentConverter()

        result = converter.convert(str(path))
        return result.document.export_to_markdown()
    except Exception:
        return ""


def extract_text_from_bytes(content: bytes, mime_type: str) -> str:
    """
    Extract text from raw bytes of a document. Writes to a temp file,
    runs Docling, returns markdown text. Used by OneDrive scanner when
    a PDF or Office file is downloaded and needs text extraction.

    Returns empty string if the mime type is unsupported or extraction fails.
    """
    if mime_type not in DOCLING_MIMES:
        return ""

    suffix = MIME_TO_EXT.get(mime_type, ".pdf")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        return extract_text(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


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
            # granite-docling-258M via MLX on Apple Silicon
            from docling.document_converter import PdfFormatOption
            from docling.pipeline.vlm_pipeline import VlmPipeline
            from docling.datamodel.pipeline_options import (
                VlmPipelineOptions,
                VlmConvertOptions,
            )
            from docling.datamodel.vlm_engine_options import MlxVlmEngineOptions
            vlm_opts = VlmConvertOptions.from_preset(
                "granite_docling",
                engine_options=MlxVlmEngineOptions(),
            )
            pipeline_opts = VlmPipelineOptions()
            pipeline_opts.vlm_options = vlm_opts
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_cls=VlmPipeline,
                        pipeline_options=pipeline_opts,
                    ),
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
