# pdf_generator.py - Generate professional PDF invoices using ReportLab

import os
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, HRFlowable)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

BILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bills")


def generate_pdf_bill(invoice_number: str, customer: dict, cart_items: list,
                      subtotal: float, discount: float, gst: float,
                      final_total: float, special_items: list = None) -> str:
    """Generate PDF invoice and return file path."""

    if not REPORTLAB_AVAILABLE:
        return _generate_text_bill(invoice_number, customer, cart_items,
                                   subtotal, discount, gst, final_total)

    os.makedirs(BILLS_DIR, exist_ok=True)
    filename = f"Invoice_{invoice_number}.pdf"
    filepath = os.path.join(BILLS_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)

    styles = getSampleStyleSheet()
    story  = []

    # ── Header ──────────────────────────────────────────────────
    title_style = ParagraphStyle("Title", parent=styles["Normal"],
                                 fontSize=28, textColor=colors.HexColor("#C0392B"),
                                 alignment=TA_CENTER, fontName="Helvetica-Bold",
                                 spaceAfter=2)
    sub_style   = ParagraphStyle("Sub",   parent=styles["Normal"],
                                 fontSize=11, textColor=colors.HexColor("#7F8C8D"),
                                 alignment=TA_CENTER, spaceAfter=4)
    body_style  = ParagraphStyle("Body",  parent=styles["Normal"],
                                 fontSize=9,  textColor=colors.HexColor("#2C3E50"))
    right_style = ParagraphStyle("Right", parent=body_style,
                                 alignment=TA_RIGHT)
    bold_style  = ParagraphStyle("Bold",  parent=body_style,
                                 fontName="Helvetica-Bold")
    total_style = ParagraphStyle("Total", parent=bold_style,
                                 fontSize=13, textColor=colors.HexColor("#C0392B"),
                                 alignment=TA_RIGHT)

    story.append(Paragraph("🍽️  TWIN T Restaurant", title_style))
    story.append(Paragraph("Taste Beyond Expectations", sub_style))
    story.append(HRFlowable(width="100%", thickness=2,
                             color=colors.HexColor("#C0392B")))
    story.append(Spacer(1, 0.3*cm))

    # ── Invoice meta ────────────────────────────────────────────
    now = datetime.now().strftime("%d-%b-%Y  %I:%M %p")
    meta = [
        [Paragraph(f"<b>Invoice #:</b> {invoice_number}", body_style),
         Paragraph(f"<b>Date:</b> {now}", right_style)],
        [Paragraph(f"<b>Customer:</b> {customer.get('name','')}", body_style),
         Paragraph(f"<b>Phone:</b> {customer.get('phone','')}", right_style)],
    ]
    if customer.get("email"):
        meta.append([Paragraph(f"<b>Email:</b> {customer.get('email')}", body_style), Paragraph("", body_style)])
    if customer.get("instructions"):
        meta.append([Paragraph(f"<b>Note:</b> {customer.get('instructions')}", body_style), Paragraph("", body_style)])

    meta_table = Table(meta, colWidths=[10*cm, 8*cm])
    meta_table.setStyle(TableStyle([("BOTTOMPADDING", (0,0), (-1,-1), 3)]))
    story.append(meta_table)
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=1,
                             color=colors.HexColor("#BDC3C7")))
    story.append(Spacer(1, 0.3*cm))

    # ── Items table ─────────────────────────────────────────────
    hdr = [Paragraph(t, ParagraphStyle("H", parent=bold_style, alignment=a))
           for t, a in [("Item", TA_LEFT), ("Qty", TA_CENTER),
                        ("Unit Price", TA_RIGHT), ("Total", TA_RIGHT)]]
    rows = [hdr]
    for item in cart_items:
        name  = item.get("name", "")
        qty   = item.get("quantity", 1)
        price = item.get("price", 0)
        rows.append([
            Paragraph(name, body_style),
            Paragraph(str(qty), ParagraphStyle("C", parent=body_style, alignment=TA_CENTER)),
            Paragraph(f"\u20b9{price:.0f}", ParagraphStyle("R", parent=body_style, alignment=TA_RIGHT)),
            Paragraph(f"\u20b9{price*qty:.0f}", ParagraphStyle("R", parent=body_style, alignment=TA_RIGHT)),
        ])

    # Complimentary items
    if special_items:
        for si in special_items:
            rows.append([
                Paragraph(f"{si} (Complimentary 🎁)", ParagraphStyle("G", parent=body_style,
                           textColor=colors.HexColor("#27AE60"))),
                Paragraph("1", ParagraphStyle("C", parent=body_style, alignment=TA_CENTER)),
                Paragraph("₹0", ParagraphStyle("R", parent=body_style, alignment=TA_RIGHT)),
                Paragraph("₹0", ParagraphStyle("R", parent=body_style, alignment=TA_RIGHT)),
            ])

    items_table = Table(rows, colWidths=[9*cm, 2*cm, 3.5*cm, 3.5*cm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  colors.HexColor("#C0392B")),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.HexColor("#FDFEFE"), colors.HexColor("#FADBD8")]),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#D5D8DC")),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Totals ───────────────────────────────────────────────────
    def money_row(label, amount, bold=False, color=None):
        s = ParagraphStyle("M", parent=body_style,
                           fontName="Helvetica-Bold" if bold else "Helvetica",
                           textColor=color or colors.HexColor("#2C3E50"))
        sr = ParagraphStyle("MR", parent=s, alignment=TA_RIGHT)
        return [Paragraph(label, s), Paragraph(f"\u20b9{amount:.2f}", sr)]

    totals = [
        money_row("Subtotal", subtotal),
    ]
    if discount > 0:
        totals.append(money_row(f"Discount (10%)", -discount,
                                color=colors.HexColor("#27AE60")))
    totals.append(money_row("GST (5%)", gst))
    totals.append(money_row("FINAL TOTAL", final_total, bold=True,
                            color=colors.HexColor("#C0392B")))

    tot_table = Table(totals, colWidths=[14*cm, 4*cm])
    tot_table.setStyle(TableStyle([
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LINEABOVE",     (0,-1), (-1,-1), 1.5, colors.HexColor("#C0392B")),
        ("LINEBELOW",     (0,-1), (-1,-1), 1.5, colors.HexColor("#C0392B")),
    ]))
    story.append(tot_table)
    story.append(Spacer(1, 0.6*cm))

    # ── Footer ───────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#BDC3C7")))
    story.append(Spacer(1, 0.2*cm))
    footer_style = ParagraphStyle("Footer", parent=body_style, alignment=TA_CENTER,
                                  textColor=colors.HexColor("#7F8C8D"), fontSize=8)
    story.append(Paragraph("Thank you for dining with TWIN T Restaurant! 🍽️", footer_style))
    story.append(Paragraph("\"Taste Beyond Expectations\"", footer_style))
    story.append(Paragraph(f"Bills saved to: bills/{filename}", footer_style))

    doc.build(story)
    return filepath


def _generate_text_bill(invoice_number, customer, cart_items,
                        subtotal, discount, gst, final_total) -> str:
    """Fallback plain-text bill when ReportLab is not installed."""
    os.makedirs(BILLS_DIR, exist_ok=True)
    filename = f"Invoice_{invoice_number}.txt"
    filepath = os.path.join(BILLS_DIR, filename)
    now = datetime.now().strftime("%d-%b-%Y %I:%M %p")
    lines = [
        "=" * 50,
        "       TWIN T RESTAURANT",
        "    Taste Beyond Expectations",
        "=" * 50,
        f"Invoice #: {invoice_number}",
        f"Date     : {now}",
        f"Customer : {customer.get('name','')}",
        f"Phone    : {customer.get('phone','')}",
        "-" * 50,
        f"{'Item':<28} {'Qty':>4} {'Price':>8} {'Total':>8}",
        "-" * 50,
    ]
    for item in cart_items:
        n = item.get("name","")[:27]
        q = item.get("quantity",1)
        p = item.get("price",0)
        lines.append(f"{n:<28} {q:>4} {p:>8.0f} {p*q:>8.0f}")
    lines += [
        "-" * 50,
        f"{'Subtotal':<38} {subtotal:>8.2f}",
    ]
    if discount:
        lines.append(f"{'Discount':<38} -{discount:>7.2f}")
    lines += [
        f"{'GST (5%)':<38} {gst:>8.2f}",
        "=" * 50,
        f"{'FINAL TOTAL':<38} {final_total:>8.2f}",
        "=" * 50,
        "Thank you for dining with TWIN T Restaurant!",
    ]
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return filepath
