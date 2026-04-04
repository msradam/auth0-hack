"""
Preprocess policy PDFs into structured JSON chunks for RAG.

Uses Docling to parse the real ICRC Handbook, IASC Guidance, GDPR, and
Sphere Handbook PDFs. Extracts text by section/chapter, stores as JSON
chunks with metadata (source, page, title) in Granite 4's native
<documents> format.

Run once:
    uv run python scripts/preprocess_policies.py

Output: amanat/knowledge/policy_chunks.json
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

OUTPUT = Path("amanat/knowledge/policy_chunks.json")
SOURCE_DIR = Path("amanat/knowledge/source_docs")

# Map files to source metadata
SOURCES = {
    "ICRC_Data_Protection_Handbook_2nd_Ed_2020.pdf": {
        "source": "ICRC Handbook",
        "full_title": "Handbook on Data Protection in Humanitarian Action",
        "edition": "2nd/3rd Edition",
        "year": 2020,
    },
    "IASC_Operational_Guidance_Data_Responsibility_2023.pdf": {
        "source": "IASC",
        "full_title": "Operational Guidance on Data Responsibility in Humanitarian Action",
        "edition": "2023",
        "year": 2023,
    },
    "GDPR_Full_Text.pdf": {
        "source": "GDPR",
        "full_title": "Regulation (EU) 2016/679 (General Data Protection Regulation)",
        "edition": "Official Journal",
        "year": 2016,
    },
    "Sphere_Handbook_2018.pdf": {
        "source": "Sphere",
        "full_title": "The Sphere Handbook: Humanitarian Charter and Minimum Standards",
        "edition": "4th Edition",
        "year": 2018,
    },
}

# Keywords for filtering relevant sections (skip irrelevant content like
# table of contents, acknowledgements, index pages)
RELEVANT_KEYWORDS = [
    "data protection", "personal data", "processing", "consent", "retention",
    "security", "transfer", "sharing", "biometric", "sensitive", "special category",
    "protection", "privacy", "confidential", "humanitarian", "beneficiary",
    "minimisation", "minimization", "purpose limitation", "lawfulness",
    "accountability", "transparency", "rights", "breach", "incident",
    "encryption", "pseudonymisation", "access control", "audit",
    "child", "gender", "GBV", "sexual", "medical", "health",
    "controller", "processor", "data subject", "legitimate interest",
    "vital interest", "public interest",
]

MAX_CHUNK_CHARS = 1500  # Keep chunks small for Granite Micro's context window
MIN_CHUNK_CHARS = 100   # Skip tiny fragments


def parse_pdf(pdf_path: Path) -> str:
    """Parse a PDF with Docling and return markdown text."""
    from docling.document_converter import DocumentConverter
    print(f"  Parsing {pdf_path.name}...")
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    text = result.document.export_to_markdown()
    print(f"  Extracted {len(text):,} chars")
    return text


def chunk_by_sections(text: str, source_meta: dict) -> list[dict]:
    """Split markdown text into chunks by headings."""
    # Split on markdown headings (## or ###)
    sections = re.split(r'\n(#{1,3}\s+.+)\n', text)

    chunks = []
    current_title = source_meta["full_title"]
    current_text = ""

    for part in sections:
        if re.match(r'^#{1,3}\s+', part):
            # This is a heading — save previous chunk and start new one
            if current_text.strip() and len(current_text.strip()) >= MIN_CHUNK_CHARS:
                chunks.append({
                    "title": current_title.strip(),
                    "text": current_text.strip()[:MAX_CHUNK_CHARS],
                    "source": source_meta["source"],
                    "full_source": source_meta["full_title"],
                    "year": source_meta["year"],
                })
            current_title = part.strip().lstrip('#').strip()
            current_text = ""
        else:
            current_text += part

    # Don't forget the last section
    if current_text.strip() and len(current_text.strip()) >= MIN_CHUNK_CHARS:
        chunks.append({
            "title": current_title.strip(),
            "text": current_text.strip()[:MAX_CHUNK_CHARS],
            "source": source_meta["source"],
            "full_source": source_meta["full_title"],
            "year": source_meta["year"],
        })

    return chunks


def filter_relevant(chunks: list[dict]) -> list[dict]:
    """Keep only chunks relevant to data protection / humanitarian governance."""
    relevant = []
    for chunk in chunks:
        combined = (chunk["title"] + " " + chunk["text"]).lower()
        if any(kw in combined for kw in RELEVANT_KEYWORDS):
            relevant.append(chunk)
    return relevant


def main():
    all_chunks = []
    doc_id = 1

    for filename, meta in SOURCES.items():
        pdf_path = SOURCE_DIR / filename
        if not pdf_path.exists():
            print(f"  SKIP: {filename} not found")
            continue

        text = parse_pdf(pdf_path)
        chunks = chunk_by_sections(text, meta)
        relevant = filter_relevant(chunks)

        print(f"  {len(chunks)} total sections → {len(relevant)} relevant chunks")

        for chunk in relevant:
            chunk["doc_id"] = doc_id
            doc_id += 1
            all_chunks.append(chunk)

    # Write output
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"\nWrote {len(all_chunks)} chunks to {OUTPUT}")
    print(f"Total text: {sum(len(c['text']) for c in all_chunks):,} chars")

    # Print summary by source
    by_source = {}
    for c in all_chunks:
        by_source.setdefault(c["source"], []).append(c)
    for source, chunks in sorted(by_source.items()):
        print(f"  {source}: {len(chunks)} chunks")


if __name__ == "__main__":
    main()
