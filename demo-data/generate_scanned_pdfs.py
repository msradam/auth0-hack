"""
Generate synthetic scanned-looking PDFs for Amanat demo.

Each PDF is image-only (no embedded text layer)  -  simulating documents
that were printed and scanned. Docling's OCR pipeline is required to
extract text for PII detection.

Run from the repo root:
    uv run python demo-data/generate_scanned_pdfs.py
"""

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUTPUT_DIR = Path(__file__).parent / "drive"
OUTPUT_DIR.mkdir(exist_ok=True)

# Page dimensions at 150 DPI — realistic scanned document size
PAGE_W, PAGE_H = 1240, 1754  # ~A4 at 150 dpi
MARGIN = 90
LINE_H = 38
FONT_SIZE = 28


def _get_font(size: int = FONT_SIZE) -> ImageFont.ImageFont:
    """Return a font, falling back to Pillow default if no system fonts."""
    candidates = [
        "/System/Library/Fonts/Courier.ttc",
        "/System/Library/Fonts/Monaco.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _render_page(lines: list[str], title: str | None = None) -> Image.Image:
    """Render a list of text lines onto a page image."""
    # Slightly off-white paper
    bg = (248, 245, 238)
    img = Image.new("RGB", (PAGE_W, PAGE_H), color=bg)
    draw = ImageDraw.Draw(img)

    font = _get_font(FONT_SIZE)
    title_font = _get_font(FONT_SIZE + 6)
    ink = (18, 18, 18)

    y = MARGIN
    if title:
        draw.text((MARGIN, y), title, font=title_font, fill=ink)
        y += LINE_H + 16
        # Underline
        draw.line([(MARGIN, y), (PAGE_W - MARGIN, y)], fill=(80, 80, 80), width=2)
        y += 20

    for line in lines:
        if y + LINE_H > PAGE_H - MARGIN:
            break  # Don't overflow
        draw.text((MARGIN, y), line, font=font, fill=ink)
        y += LINE_H

    return img


def _degrade(img: Image.Image, rotation: float = 0.0, noise: int = 8) -> Image.Image:
    """Add scan-like degradation: slight rotation, noise, mild blur."""
    if rotation:
        img = img.rotate(rotation, fillcolor=(248, 245, 238), expand=False)

    # Add random pixel noise
    import random
    pixels = img.load()
    for _ in range(PAGE_W * PAGE_H * noise // 1000):
        x = random.randint(0, PAGE_W - 1)
        y = random.randint(0, PAGE_H - 1)
        delta = random.randint(-20, 20)
        r, g, b = pixels[x, y]
        pixels[x, y] = (
            max(0, min(255, r + delta)),
            max(0, min(255, g + delta)),
            max(0, min(255, b + delta)),
        )

    # Very mild blur to simulate scanner softness
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
    return img


def _save_pdf(pages: list[Image.Image], path: Path):
    """Save a list of page images as a PDF (image-only, no text layer)."""
    if not pages:
        return
    first = pages[0].convert("RGB")
    rest = [p.convert("RGB") for p in pages[1:]]
    first.save(path, format="PDF", save_all=True, append_images=rest, resolution=150)
    print(f"  Wrote {path.name} ({len(pages)} page(s))")


# ── Document 1: Beneficiary Registration Form ─────────────────────────────────

def generate_registration_form():
    pages = []

    page1_lines = [
        "WAQWAQ RELIEF AUTHORITY",
        "BENEFICIARY REGISTRATION FORM  -  WRA-REG-2026",
        "",
        "SECTION A: PERSONAL INFORMATION",
        "-" * 55,
        "Full Name:        Rozel al-Bahar",
        "Date of Birth:    14 March 1989",
        "Place of Origin:  Sofala Village, Southern Coast",
        "Nationality:      Kanbalese",
        "Case ID:          WAQ-26C00891",
        "",
        "SECTION B: DISPLACEMENT STATUS",
        "-" * 55,
        "Date of Displacement:   01 May 2025",
        "Cause:                  Cataclysm  -  structural collapse",
        "Current Location:       Kanbaloh IDP Hub, Tent B-14",
        "Household Size:         4 (adult + 3 dependants)",
        "",
        "SECTION C: MEDICAL & VULNERABILITY",
        "-" * 55,
        "Medical Conditions:     PTSD (documented), chronic hypertension",
        "Disability Status:      None declared",
        "Pregnant / Lactating:   No",
        "Priority Needs:         Mental health support, shelter",
        "",
        "SECTION D: CONTACT",
        "-" * 55,
        "Phone:      471-55-555-1234",
        "Alternate:  471-55-555-9900",
        "Email:      r.albahar@sofala.wra-waqwaq.org",
        "",
        "SECTION E: CONSENT",
        "-" * 55,
        "I consent to WRA processing my personal data for",
        "humanitarian assistance coordination.",
        "",
        "Signature: ___________________________  Date: ___________",
        "",
        "Registered by: Penn Rashidi  (Staff ID: WRA-STAFF-042)",
        "Registration Date: 03 June 2025",
        "Site: Kanbaloh Hub",
    ]

    img = _render_page(page1_lines)
    pages.append(_degrade(img, rotation=0.4))
    _save_pdf(pages, OUTPUT_DIR / "Beneficiary_Registration_Scanned.pdf")


# ── Document 2: GBV Incident Report ───────────────────────────────────────────

def generate_gbv_report():
    pages = []

    page1_lines = [
        "WAQWAQ RELIEF AUTHORITY",
        "GBV INCIDENT REPORT  -  CONFIDENTIAL",
        "Report Ref: GBV-2026-0047",
        "",
        "STRICTLY CONFIDENTIAL  -  RESTRICTED ACCESS",
        "Do not share without explicit authorisation.",
        "-" * 55,
        "",
        "Date of Report:    12 August 2026",
        "Reported by:       Addison Khalil (Caseworker, WRA)",
        "Location of Inc.:  Vakwa Shelter, Sector 3",
        "Date of Incident:  09 August 2026",
        "",
        "SURVIVOR INFORMATION",
        "-" * 55,
        "Pseudonym / Ref:   Survivor-GBV-047",
        "Age:               24",
        "Ethnicity:         Vakwan",
        "Case ID:           WAQ-26C00923",
        "",
        "INCIDENT DETAILS",
        "-" * 55,
        "Type of Violence:  Intimate partner violence",
        "Injuries:          Minor physical trauma, psychological trauma",
        "Medical Referral:  Majala Village Clinic  -  Dr. Farah Tabib",
        "Safe House:        Vakwa Shelter, Unit 7 (restricted access)",
        "",
        "IMMEDIATE NEEDS",
        "-" * 55,
        "  [X] Medical care",
        "  [X] Psychosocial support",
        "  [X] Legal advice",
        "  [ ] Emergency shelter",
        "  [ ] Child protection referral",
        "",
        "REFERRAL CHAIN",
        "-" * 55,
        "  WRA Vakwa Shelter --> Majala Clinic",
        "  Contact: +471-55-555-8800",
        "",
        "This report must be stored in a locked system.",
        "Access limited to Protection Cluster leads only.",
        "",
        "Caseworker signature: _______________  Date: __________",
    ]

    img = _render_page(page1_lines)
    pages.append(_degrade(img, rotation=-0.3, noise=10))
    _save_pdf(pages, OUTPUT_DIR / "GBV_Incident_Report_Scanned.pdf")


# ── Document 3: Protection Assessment ─────────────────────────────────────────

def generate_protection_assessment():
    pages = []

    page1_lines = [
        "WRA PROTECTION CLUSTER",
        "INDIVIDUAL PROTECTION ASSESSMENT  -  IPA-2026-0112",
        "",
        "Assessment Date:  22 September 2026",
        "Assessor:         Fariq Haras  (WRA Protection Officer)",
        "Location:         Kanbaloh Hub, Room 4",
        "-" * 55,
        "",
        "SUBJECT DETAILS",
        "-" * 55,
        "Name:             Halim al-Mawj",
        "DOB:              07 July 1992",
        "Ethnicity:        Zenji",
        "Case ID:          WAQ-26C00889",
        "Current Address:  Zenji Harbor Temporary Site, Shelter 3",
        "",
        "RISK FACTORS IDENTIFIED",
        "-" * 55,
        "  [X] Separated from family during Cataclysm",
        "  [X] Visible ethnic minority (Zenji) in mixed camp",
        "  [X] History of detention (pre-Cataclysm)",
        "  [ ] UASC",
        "  [ ] Medical vulnerability",
        "",
        "PROTECTION CONCERNS",
        "-" * 55,
        "Subject reports verbal harassment by other displaced",
        "persons. Fear of targeted violence due to ethnic origin.",
        "GPS coords of last incident: 136.8842, -3.4921",
        "",
        "RECOMMENDED ACTIONS",
        "-" * 55,
        "1. Relocate to dedicated Zenji-only housing block.",
        "2. Psychosocial support referral.",
        "3. Document incidents for legal protection file.",
        "4. Monthly follow-up by Fariq Haras.",
        "",
        "Referral contact:  Symin Nuru  +471-55-555-3344",
        "Email:             s.nuru@wra-waqwaq.org",
        "",
        "Signature: ___________________________  Date: ___________",
        "Supervisor review: Amara Sahel   Date: ___________",
    ]

    img = _render_page(page1_lines)
    pages.append(_degrade(img, rotation=0.2, noise=6))
    _save_pdf(pages, OUTPUT_DIR / "Protection_Assessment_Scanned.pdf")


# ── Document 4: Biometric Enrollment Consent ──────────────────────────────────

def generate_biometric_consent():
    pages = []

    page1_lines = [
        "WRA AID DISTRIBUTION  -  BIOMETRIC ENROLMENT",
        "INFORMED CONSENT FORM",
        "Site: Kanbaloh Hub  |  Date: 10 Oct 2026",
        "-" * 55,
        "",
        "Beneficiary Name:    Naila Barid",
        "Case ID:             WAQ-26C00877",
        "Date of Birth:       19 February 2001",
        "Ethnicity:           Zenji",
        "",
        "WHAT WE ARE COLLECTING",
        "-" * 55,
        "WRA is enrolling beneficiaries in a biometric system",
        "for aid distribution. We will collect:",
        "",
        "  - Fingerprint scan (right index + middle finger)",
        "  - Iris scan (both eyes)",
        "  - Facial recognition photograph",
        "",
        "PURPOSE",
        "-" * 55,
        "Biometric data is used only to verify identity at",
        "aid distribution points. It will not be shared with",
        "government authorities or third parties without",
        "explicit consent.",
        "",
        "RETENTION",
        "-" * 55,
        "Data retained for 6 months after last assistance.",
        "You may request deletion at any time.",
        "",
        "CONSENT DECLARATION",
        "-" * 55,
        "I have read and understood the above. I consent to",
        "biometric enrolment for WRA aid distribution.",
        "",
        "Signature: ___________________________  Date: ___________",
        "",
        "Enrolled by: Penn Rashidi  (Staff ID: WRA-STAFF-042)",
        "Enrolment ID: BIO-2026-0412",
        "Phone on file: 471-55-555-2211",
    ]

    img = _render_page(page1_lines)
    pages.append(_degrade(img, rotation=-0.5, noise=9))
    _save_pdf(pages, OUTPUT_DIR / "Biometric_Consent_Scanned.pdf")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating scanned-look PDFs for Amanat demo...")
    generate_registration_form()
    generate_gbv_report()
    generate_protection_assessment()
    generate_biometric_consent()
    print(f"\nDone. Files written to {OUTPUT_DIR}/")
    print("\nThese PDFs have no embedded text layer.")
    print("Docling OCR is required to extract content for PII detection.")
