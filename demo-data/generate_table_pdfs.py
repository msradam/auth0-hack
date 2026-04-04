"""
Generate dense-table PDFs for testing granite-docling-258M VLM extraction.

These simulate the kind of structured data exports that field teams
actually use: intake registers, distribution logs, site population tables.

Run from repo root:
    uv run python demo-data/generate_table_pdfs.py
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUTPUT_DIR = Path(__file__).parent / "drive"
OUTPUT_DIR.mkdir(exist_ok=True)

PAGE_W, PAGE_H = 1654, 2339  # A4 at 200 dpi — more pixels for table detail
MARGIN = 80
FONT_SIZE = 22
SMALL = 18


def _font(size=FONT_SIZE):
    for path in [
        "/System/Library/Fonts/Courier.ttc",
        "/System/Library/Fonts/Monaco.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _degrade(img, rotation=0.3, noise=7):
    if rotation:
        img = img.rotate(rotation, fillcolor=(247, 244, 237), expand=False)
    import random
    px = img.load()
    w, h = img.size
    for _ in range(w * h * noise // 1000):
        x, y = random.randint(0, w - 1), random.randint(0, h - 1)
        d = random.randint(-15, 15)
        r, g, b = px[x, y]
        px[x, y] = (max(0, min(255, r+d)), max(0, min(255, g+d)), max(0, min(255, b+d)))
    return img.filter(ImageFilter.GaussianBlur(radius=0.5))


def _save_pdf(pages, path):
    first = pages[0].convert("RGB")
    rest = [p.convert("RGB") for p in pages[1:]]
    first.save(path, format="PDF", save_all=True, append_images=rest, resolution=200)
    print(f"  Wrote {path.name} ({len(pages)} page(s))")


def _draw_table(draw, headers, rows, x0, y0, col_widths, row_h, font, header_font, ink=(20, 20, 20)):
    """Draw a bordered table with headers and data rows."""
    total_w = sum(col_widths)

    # Header row
    draw.rectangle([x0, y0, x0 + total_w, y0 + row_h], fill=(200, 210, 220))
    x = x0
    for i, (h, w) in enumerate(zip(headers, col_widths)):
        draw.text((x + 6, y0 + 5), h, font=header_font, fill=ink)
        x += w
    draw.rectangle([x0, y0, x0 + total_w, y0 + row_h], outline=ink, width=1)

    # Data rows
    y = y0 + row_h
    for ri, row in enumerate(rows):
        bg = (252, 250, 246) if ri % 2 == 0 else (243, 241, 237)
        draw.rectangle([x0, y, x0 + total_w, y + row_h], fill=bg)
        x = x0
        for cell, w in zip(row, col_widths):
            draw.text((x + 6, y + 5), str(cell), font=font, fill=ink)
            x += w
        draw.rectangle([x0, y, x0 + total_w, y + row_h], outline=(150, 150, 150), width=1)
        y += row_h

    # Outer border
    draw.rectangle([x0, y0, x0 + total_w, y], outline=ink, width=2)
    return y


# ── Document 1: Site Population Register ─────────────────────────────────────

def generate_site_register():
    img = Image.new("RGB", (PAGE_W, PAGE_H), (247, 244, 237))
    draw = ImageDraw.Draw(img)
    f = _font(FONT_SIZE)
    fh = _font(FONT_SIZE + 2)
    fs = _font(SMALL)
    ink = (20, 20, 20)

    y = MARGIN
    draw.text((MARGIN, y), "WAQWAQ RELIEF AUTHORITY", font=fh, fill=ink)
    y += 34
    draw.text((MARGIN, y), "KANBALOH IDP HUB - SITE POPULATION REGISTER", font=fh, fill=ink)
    y += 28
    draw.text((MARGIN, y), "Reporting Period: 01 Oct 2026 - 31 Oct 2026  |  Site ID: WRA-SITE-001", font=fs, fill=ink)
    y += 28
    draw.text((MARGIN, y), "Compiled by: Symin Nuru  |  Approved by: Amara Sahel", font=fs, fill=ink)
    y += 36
    draw.line([(MARGIN, y), (PAGE_W - MARGIN, y)], fill=ink, width=2)
    y += 20

    draw.text((MARGIN, y), "TABLE 1: REGISTERED HOUSEHOLD SUMMARY", font=fh, fill=ink)
    y += 32

    headers1 = ["Case ID", "Head of HH", "Ethnicity", "HH Size", "Arrival Date", "Shelter", "Med Flag"]
    col_w1 = [160, 220, 120, 90, 160, 110, 110]
    rows1 = [
        ["WAQ-26C00891", "Rozel al-Bahar",  "Kanbalese", "4", "01 Jun 2026", "B-14", "PTSD"],
        ["WAQ-26C00892", "Addis Harun",  "Kanbalese", "2", "03 Jun 2026", "B-15", "-"],
        ["WAQ-26C00893", "Yasmin al-Mawj",   "Zenji",   "3", "05 Jun 2026", "C-02", "-"],
        ["WAQ-26C00894", "Tariq Samawi",   "Ambari",   "5", "07 Jun 2026", "A-09", "chronic"],
        ["WAQ-26C00895", "Idris Baraka", "Ambari",   "6", "09 Jun 2026", "A-10", "-"],
        ["WAQ-26C00896", "Dalila Ramli",  "Vakwan", "1", "11 Jun 2026", "D-01", "trauma"],
        ["WAQ-26C00897", "Amara Sahel", "Vakwan", "3", "12 Jun 2026", "D-02", "-"],
        ["WAQ-26C00898", "Halim al-Mawj",  "Zenji",   "4", "14 Jun 2026", "C-03", "-"],
        ["WAQ-26C00899", "Jabir Sakhr", "Sofali",  "2", "16 Jun 2026", "E-01", "TB"],
        ["WAQ-26C00900", "Sami Samawi",  "Ambari",   "3", "18 Jun 2026", "A-11", "-"],
        ["WAQ-26C00901", "Zahra Nashid",  "Zenji",   "4", "20 Jun 2026", "C-04", "-"],
        ["WAQ-26C00902", "Naila Barid",   "Zenji",   "2", "22 Jun 2026", "C-05", "PTSD"],
    ]
    y = _draw_table(draw, headers1, rows1, MARGIN, y, col_w1, 34, fs, f)
    y += 30

    draw.text((MARGIN, y), "TABLE 2: VULNERABILITY BREAKDOWN BY ETHNICITY", font=fh, fill=ink)
    y += 32

    headers2 = ["Ethnicity", "HHs", "Individuals", "Children <5", "Elderly 60+", "Disabled", "Med Needs"]
    col_w2 = [150, 80, 130, 130, 130, 110, 120]
    rows2 = [
        ["Kanbalese", "24", "67",  "12", "8",  "3", "9"],
        ["Zenji",   "18", "52",  "6",  "4",  "1", "7"],
        ["Ambari",   "15", "61",  "14", "5",  "2", "4"],
        ["Vakwan", "11", "38",  "9",  "3",  "0", "6"],
        ["Sofali",  "8",  "29",  "4",  "6",  "1", "3"],
        ["TOTAL",  "76", "247", "45", "26", "7", "29"],
    ]
    y = _draw_table(draw, headers2, rows2, MARGIN, y, col_w2, 34, fs, f)
    y += 30

    draw.text((MARGIN, y), "TABLE 3: AID DISTRIBUTION LOG - OCTOBER 2026", font=fh, fill=ink)
    y += 32

    headers3 = ["Date", "Case ID", "Beneficiary", "Item", "Qty", "Collector", "Staff ID"]
    col_w3 = [130, 160, 210, 200, 60, 190, 160]
    rows3 = [
        ["02 Oct", "WAQ-26C00891", "Rozel al-Bahar",  "Food parcel 30d", "1", "Rozel al-Bahar",  "WRA-STAFF-042"],
        ["02 Oct", "WAQ-26C00892", "Addis Harun",  "Food parcel 30d", "1", "Addis Harun",  "WRA-STAFF-042"],
        ["02 Oct", "WAQ-26C00893", "Yasmin al-Mawj",   "Food parcel 30d", "1", "Yasmin al-Mawj",   "WRA-STAFF-042"],
        ["03 Oct", "WAQ-26C00894", "Tariq Samawi",   "NFI kit",         "1", "Tariq Samawi",   "WRA-STAFF-043"],
        ["03 Oct", "WAQ-26C00896", "Dalila Ramli",  "Hygiene kit",     "2", "Dalila Ramli",  "WRA-STAFF-043"],
        ["05 Oct", "WAQ-26C00899", "Jabir Sakhr", "Medical referral","1", "Penn Rashidi",  "WRA-STAFF-042"],
        ["07 Oct", "WAQ-26C00900", "Sami Samawi",  "Food parcel 30d", "1", "Sami Samawi",  "WRA-STAFF-044"],
        ["10 Oct", "WAQ-26C00902", "Naila Barid",   "PSS session",     "1", "Addison Khalil", "WRA-STAFF-045"],
    ]
    y = _draw_table(draw, headers3, rows3, MARGIN, y, col_w3, 34, fs, f)
    y += 30

    draw.text((MARGIN, y), "Contact: s.nuru@wra-waqwaq.org  |  Tel: 471-55-555-3344", font=fs, fill=ink)

    _save_pdf([_degrade(img, rotation=0.3)], OUTPUT_DIR / "Site_Population_Register_Scanned.pdf")


# ── Document 2: Biometric Verification Log ────────────────────────────────────

def generate_biometric_log():
    img = Image.new("RGB", (PAGE_W, PAGE_H), (247, 244, 237))
    draw = ImageDraw.Draw(img)
    f = _font(FONT_SIZE)
    fh = _font(FONT_SIZE + 2)
    fs = _font(SMALL)
    ink = (20, 20, 20)

    y = MARGIN
    draw.text((MARGIN, y), "WRA AID DISTRIBUTION - BIOMETRIC VERIFICATION LOG", font=fh, fill=ink)
    y += 34
    draw.text((MARGIN, y), "Site: Kanbaloh Hub  |  Date: 15 October 2026", font=fs, fill=ink)
    y += 28
    draw.text((MARGIN, y), "Operator: Penn Rashidi (WRA-STAFF-042)  |  Device: BIO-UNIT-07", font=fs, fill=ink)
    y += 28
    draw.text((MARGIN, y), "STRICTLY CONTROLLED - biometric data, special category under GDPR Art.9", font=fs, fill=(160, 30, 30))
    y += 36
    draw.line([(MARGIN, y), (PAGE_W - MARGIN, y)], fill=ink, width=2)
    y += 20

    draw.text((MARGIN, y), "VERIFICATION LOG", font=fh, fill=ink)
    y += 32

    headers = ["Time",  "Case ID",       "Name",            "Ethnicity", "Finger", "Iris", "Match", "Aid Item"]
    col_w   = [100,     160,             200,                120,         90,       70,     90,      240]
    rows = [
        ["09:02", "WAQ-26C00891", "Rozel al-Bahar",  "Kanbalese", "R.Index", "L",  "PASS", "Food parcel 30d"],
        ["09:11", "WAQ-26C00893", "Yasmin al-Mawj",   "Zenji",   "R.Index", "L",  "PASS", "Food parcel 30d"],
        ["09:19", "WAQ-26C00894", "Tariq Samawi",   "Ambari",   "R.Index", "L",  "PASS", "Food parcel 30d"],
        ["09:28", "WAQ-26C00895", "Idris Baraka", "Ambari",   "R.Mid",   "R",  "PASS", "Food parcel 30d"],
        ["09:35", "WAQ-26C00896", "Dalila Ramli",  "Vakwan", "R.Index", "L",  "FAIL", "Retry required"],
        ["09:44", "WAQ-26C00896", "Dalila Ramli",  "Vakwan", "R.Mid",   "L",  "PASS", "Food parcel 30d"],
        ["09:52", "WAQ-26C00898", "Halim al-Mawj",  "Zenji",   "R.Index", "L",  "PASS", "NFI kit"],
        ["10:03", "WAQ-26C00899", "Jabir Sakhr", "Sofali",  "R.Index", "R",  "PASS", "Food parcel 30d"],
        ["10:11", "WAQ-26C00900", "Sami Samawi",  "Ambari",   "R.Index", "L",  "PASS", "Food parcel 30d"],
        ["10:19", "WAQ-26C00901", "Zahra Nashid",  "Zenji",   "R.Mid",   "L",  "PASS", "Hygiene kit"],
        ["10:27", "WAQ-26C00902", "Naila Barid",   "Zenji",   "R.Index", "L",  "PASS", "Food parcel 30d"],
        ["10:35", "WAQ-26C00897", "Amara Sahel", "Vakwan", "R.Index", "L",  "PASS", "Food parcel 30d"],
    ]
    y = _draw_table(draw, headers, rows, MARGIN, y, col_w, 34, fs, f)
    y += 30

    draw.text((MARGIN, y), "SUMMARY", font=fh, fill=ink)
    y += 32

    sum_headers = ["Metric", "Value"]
    sum_col_w = [400, 200]
    sum_rows = [
        ["Total verifications attempted",    "13"],
        ["Successful matches (PASS)",         "12"],
        ["Failed matches (FAIL - retry)",      "1"],
        ["Beneficiaries served",              "12"],
        ["Fingerprint scan used",             "13"],
        ["Iris scan used",                    "13"],
        ["Facial recognition used",            "0"],
        ["Enrolment IDs referenced",  "BIO-2026-0412 to BIO-2026-0423"],
    ]
    y = _draw_table(draw, sum_headers, sum_rows, MARGIN, y, sum_col_w, 34, fs, f)
    y += 30

    draw.text((MARGIN, y), "Operator signature: ___________________________   Supervisor: Penn Rashidi", font=fs, fill=ink)
    y += 28
    draw.text((MARGIN, y), "Contact for queries: p.rashidi@wra-waqwaq.org  |  Tel: 471-55-555-1001", font=fs, fill=ink)

    _save_pdf([_degrade(img, rotation=-0.25, noise=8)], OUTPUT_DIR / "Biometric_Verification_Log_Scanned.pdf")


if __name__ == "__main__":
    print("Generating dense-table scanned PDFs for Granite VLM test...")
    generate_site_register()
    generate_biometric_log()
    print(f"\nDone. Files in {OUTPUT_DIR}/")
    print("Test with: uv run python demo-data/test_granite_vlm.py")
