"""
render.py — Convert bill JSON files into CMS-1500-styled PDF bills.

Reads JSON files (one bill each, or a list of bills in a single file) from
the input directory and writes PDFs to the output directory using the
filename convention clean_NNN.pdf / dis_NNN.pdf. Also writes manifest.csv.

Usage:
    python render.py --input bills_json/ --output bills_pdf/

The JSON schema is described in bill-generator-prompt.md.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)


def _addr(a: dict) -> str:
    return f"{a['street']}, {a['city']}, {a['state']} {a['zip']}"


def _money(x: float) -> str:
    return f"${x:,.2f}"


def render_bill(bill: dict, out_path: Path) -> None:
    """Render one bill JSON dict to a PDF at out_path."""
    doc = SimpleDocTemplate(
        str(out_path), pagesize=LETTER,
        leftMargin=0.5 * inch, rightMargin=0.5 * inch,
        topMargin=0.4 * inch, bottomMargin=0.4 * inch,
        title="Statement of Services",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=14, spaceAfter=2, alignment=0)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=10, spaceAfter=2, textColor=colors.HexColor("#444444"))
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=8.5, leading=11)
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=7.5, leading=9, textColor=colors.HexColor("#555555"))
    label = ParagraphStyle("Label", parent=styles["BodyText"], fontSize=7, leading=9, textColor=colors.HexColor("#777777"), spaceAfter=0)

    story: list[Any] = []
    p = bill["provider"]
    pt = bill["patient"]
    ins = bill["insurance"]
    enc = bill["encounter"]

    # ── Header band ───────────────────────────────────────────────────────
    header = Table(
        [[
            Paragraph(f"<b>{p['name']}</b>", h1),
            Paragraph(f"<b>STATEMENT OF SERVICES</b><br/><font size=8 color='#666666'>Form {bill['metadata']['bill_type']}</font>",
                      ParagraphStyle("R", parent=styles["BodyText"], fontSize=11, alignment=2, leading=13)),
        ]],
        colWidths=[4.5 * inch, 3.0 * inch],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.2, colors.HexColor("#333333")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(header)

    # Provider block
    story.append(Spacer(1, 4))
    prov_text = (
        f"{_addr(p['address'])}<br/>"
        f"Tel: {p['phone']} &nbsp;&nbsp; NPI: {p['npi']} &nbsp;&nbsp; Tax ID: {p['tax_id']}<br/>"
        f"Taxonomy: {p['specialty_taxonomy']} ({bill['metadata']['specialty'].replace('_', ' ').title()})"
    )
    story.append(Paragraph(prov_text, small))
    story.append(Spacer(1, 10))

    # ── Patient & Insurance & Encounter side-by-side ──────────────────────
    pat_block = (
        f"<b>{pt['name']}</b><br/>"
        f"DOB: {pt['dob']} &nbsp;|&nbsp; Sex: {pt['sex']}<br/>"
        f"{_addr(pt['address'])}<br/>"
        f"Acct #: {pt['account_number']}"
    )
    ins_block = (
        f"<b>{ins['payer_name']}</b><br/>"
        f"Plan: {ins['plan_type']}<br/>"
        f"Subscriber ID: {ins['subscriber_id']}<br/>"
        f"Group #: {ins['group_number']}"
    )
    fac_text = enc.get("facility") or "—"
    enc_block = (
        f"<b>Date of Service:</b> {enc['date_of_service']}<br/>"
        f"<b>Billing Date:</b> {enc['billing_date']}<br/>"
        f"<b>POS:</b> {enc['place_of_service_code']} ({enc['place_of_service_description']})<br/>"
        f"<b>Facility:</b> {fac_text}"
    )

    info = Table(
        [[
            [Paragraph("PATIENT", label), Paragraph(pat_block, body)],
            [Paragraph("INSURANCE", label), Paragraph(ins_block, body)],
            [Paragraph("ENCOUNTER", label), Paragraph(enc_block, body)],
        ]],
        colWidths=[2.5 * inch, 2.5 * inch, 2.5 * inch],
    )
    info.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fafafa")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(info)
    story.append(Spacer(1, 12))

    # ── Diagnosis codes ───────────────────────────────────────────────────
    dx_rows = [["Ptr", "ICD-10", "Description"]]
    for d in bill["diagnoses"]:
        dx_rows.append([d["pointer"], d["icd10"], Paragraph(d["description"], body)])
    dx_table = Table(dx_rows, colWidths=[0.4 * inch, 0.9 * inch, 6.2 * inch])
    dx_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(Paragraph("DIAGNOSIS CODES", h2))
    story.append(dx_table)
    story.append(Spacer(1, 10))

    # ── Service lines ─────────────────────────────────────────────────────
    sl_rows = [["#", "DOS", "POS", "CPT/HCPCS", "Mod", "Dx", "Description", "Units", "Charge", "Line Total"]]
    for s in bill["service_lines"]:
        mods = ", ".join(s["modifiers"]) if s["modifiers"] else "—"
        ptrs = "".join(s["diagnosis_pointers"])
        sl_rows.append([
            str(s["line_number"]),
            s["date_of_service"],
            s["place_of_service"],
            s["cpt_hcpcs"],
            mods,
            ptrs,
            Paragraph(s["description"], body),
            str(s["units"]),
            _money(s["unit_charge"]),
            _money(s["line_charge"]),
        ])
    sl_table = Table(
        sl_rows,
        colWidths=[0.3*inch, 0.7*inch, 0.4*inch, 0.7*inch, 0.45*inch, 0.4*inch,
                   2.7*inch, 0.45*inch, 0.7*inch, 0.75*inch],
    )
    sl_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (7, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 1), (5, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(Paragraph("SERVICES PROVIDED", h2))
    story.append(sl_table)
    story.append(Spacer(1, 12))

    # ── Totals ────────────────────────────────────────────────────────────
    t = bill["totals"]
    totals_rows = [
        ["Total Charges", _money(t["total_charges"])],
        ["Insurance Payment", "(" + _money(t["insurance_payment"]) + ")"],
        ["Patient Responsibility", _money(t["patient_responsibility"])],
        ["AMOUNT DUE", _money(t["amount_due"])],
    ]
    totals_table = Table(totals_rows, colWidths=[2.0 * inch, 1.3 * inch])
    totals_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor("#333333")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f4f4f4")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    # Right-align the totals table by wrapping in a container
    totals_wrap = Table([[totals_table]], colWidths=[7.5 * inch])
    totals_wrap.setStyle(TableStyle([("ALIGN", (0, 0), (0, 0), "RIGHT")]))
    story.append(totals_wrap)

    # ── Footer ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 18))
    footer = (
        "<i>This is a synthetic medical bill generated for software testing. "
        "All names, NPIs, account numbers, and identifiers are fictional. "
        "No real patient or provider data is represented.</i>"
    )
    story.append(Paragraph(footer, small))

    doc.build(story)


def collect_bills(inp: Path) -> list[dict]:
    """Read bills from a directory of .json files OR a single .json list/object."""
    bills: list[dict] = []
    if inp.is_file():
        data = json.loads(inp.read_text())
        bills = data if isinstance(data, list) else [data]
    else:
        for f in sorted(inp.glob("*.json")):
            data = json.loads(f.read_text())
            if isinstance(data, list):
                bills.extend(data)
            else:
                bills.append(data)
    return bills


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="JSON file or directory of JSON files")
    ap.add_argument("--output", required=True, help="Output directory for PDFs")
    ap.add_argument("--manifest", default=None, help="Manifest CSV path (default: <output>/manifest.csv)")
    args = ap.parse_args()

    inp = Path(args.input)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest) if args.manifest else (out / "manifest.csv")

    bills = collect_bills(inp)
    print(f"Loaded {len(bills)} bill(s) from {inp}")

    clean_n = 0
    dis_n = 0
    rows: list[dict] = []

    for b in bills:
        is_clean = bool(b["metadata"]["is_clean"])
        if is_clean:
            clean_n += 1
            fname = f"clean_{clean_n:03d}.pdf"
        else:
            dis_n += 1
            fname = f"dis_{dis_n:03d}.pdf"
        out_path = out / fname
        render_bill(b, out_path)
        print(f"  → {fname}")

        errs = ";".join(e["error_type"] for e in b["metadata"].get("planted_errors", []))
        savings = sum(float(e.get("expected_savings_usd") or 0) for e in b["metadata"].get("planted_errors", []))
        rows.append({
            "filename": fname,
            "is_clean": is_clean,
            "specialty": b["metadata"]["specialty"],
            "bill_type": b["metadata"]["bill_type"],
            "planted_errors": errs,
            "expected_total_savings_usd": f"{savings:.2f}",
        })

    with manifest_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\nWrote {clean_n} clean + {dis_n} dispute PDFs ({clean_n + dis_n} total)")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
