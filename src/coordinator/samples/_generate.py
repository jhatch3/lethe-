"""One-off script to generate the canned sample PDFs.

Run from src/coordinator/:
    .venv/Scripts/python samples/_generate.py
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


SAMPLES_DIR = Path(__file__).parent

BILLS = {
    "general-hospital-er.pdf": {
        "title": "GENERAL HOSPITAL · EMERGENCY DEPARTMENT",
        "header": [
            ("Patient", "J. Doe"),
            ("DOB", "1985-07-04"),
            ("MRN", "0099281"),
            ("Provider", "General Hospital  ·  NPI 1234567890"),
            ("DOS", "2026-04-14"),
            ("Claim", "CLM-7F3A2B"),
        ],
        "lines": [
            ("1", "CPT 99214",   "Office visit, established patient",        "1", "$185.00"),
            ("2", "CPT 99214",   "Office visit, established patient",        "1", "$185.00"),
            ("3", "CPT 96372",   "Therapeutic injection",                    "1", "$118.40"),
            ("4", "HCPCS J3490", "Unclassified drug",                        "1",  "$62.20"),
            ("5", "REV 0450",    "Emergency room services - level 5",        "1", "$121.60"),
        ],
        "total": "$672.20",
    },
    "imaging-center-ct.pdf": {
        "title": "PACIFIC IMAGING CENTER",
        "header": [
            ("Patient", "A. Smith"),
            ("DOB", "1972-03-19"),
            ("MRN", "0044812"),
            ("Provider", "Pacific Imaging  ·  NPI 9988776655"),
            ("DOS", "2026-04-09"),
            ("Claim", "CLM-IM-31A8"),
        ],
        "lines": [
            ("1", "CPT 70450",   "CT head/brain without contrast",  "1", "$640.00"),
            ("2", "CPT 70450",   "CT head/brain without contrast",  "1", "$640.00"),
            ("3", "HCPCS Q9967", "LOCM contrast 100ml",             "1", "$185.50"),
        ],
        "total": "$1465.50",
    },
    "ortho-clinic-mri.pdf": {
        "title": "CASCADE ORTHOPEDIC CLINIC",
        "header": [
            ("Patient", "M. Lee"),
            ("DOB", "1990-11-02"),
            ("MRN", "0077155"),
            ("Provider", "Cascade Ortho  ·  NPI 5544332211"),
            ("DOS", "2026-04-11"),
            ("Claim", "CLM-OR-94C2"),
        ],
        "lines": [
            ("1", "CPT 73721",   "MRI lower extremity joint without contrast", "1", "$1180.00"),
            ("2", "CPT 99213",   "Office visit, established patient",          "1",  "$112.00"),
            ("3", "CPT 20610",   "Arthrocentesis, major joint",                "1",   "$98.50"),
            ("4", "HCPCS J7325", "Hyaluronan injection",                       "1",  "$312.00"),
        ],
        "total": "$1702.50",
    },
}


def render(out: Path, bill: dict) -> None:
    c = canvas.Canvas(str(out), pagesize=letter)
    width, height = letter
    y = height - 0.75 * inch

    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.75 * inch, y, bill["title"])
    y -= 0.35 * inch

    c.setFont("Helvetica", 9)
    for label, val in bill["header"]:
        c.drawString(0.75 * inch, y, f"{label}:  {val}")
        y -= 14
    y -= 16

    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.75 * inch, y, "#")
    c.drawString(0.95 * inch, y, "Code")
    c.drawString(2.10 * inch, y, "Description")
    c.drawString(5.50 * inch, y, "Units")
    c.drawString(6.40 * inch, y, "Charge")
    c.line(0.75 * inch, y - 4, 7.50 * inch, y - 4)
    y -= 18

    c.setFont("Helvetica", 9)
    for ln, code, desc, units, charge in bill["lines"]:
        c.drawString(0.75 * inch, y, ln)
        c.drawString(0.95 * inch, y, code)
        c.drawString(2.10 * inch, y, desc)
        c.drawString(5.50 * inch, y, units)
        c.drawString(6.40 * inch, y, charge)
        y -= 14

    y -= 12
    c.line(0.75 * inch, y, 7.50 * inch, y)
    y -= 16
    c.setFont("Helvetica-Bold", 10)
    c.drawString(5.00 * inch, y, "Total Billed:")
    c.drawString(6.40 * inch, y, bill["total"])

    c.setFont("Helvetica-Oblique", 7)
    c.drawString(0.75 * inch, 0.5 * inch,
                 "Lethe phase-1 sample bill - synthetic data, no real patient.")

    c.save()


if __name__ == "__main__":
    for fname, bill in BILLS.items():
        out = SAMPLES_DIR / fname
        render(out, bill)
        print(f"wrote {out.name} ({out.stat().st_size} bytes)")