import io
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_BASE  = os.path.dirname(os.path.dirname(__file__))
_FONTS = os.path.join(_BASE, "fonts")

pdfmetrics.registerFont(TTFont("IBMPlexSans",      os.path.join(_FONTS, "IBMPlexSans-Regular.ttf")))
pdfmetrics.registerFont(TTFont("IBMPlexMono-Bold", os.path.join(_FONTS, "IBMPlexMono-Bold.ttf")))

C_BG    = colors.HexColor("#f5f4f0")
C_BLACK = colors.HexColor("#0d0d0d")
C_MUTED = colors.HexColor("#6b6760")
C_RULE  = colors.HexColor("#c8c4bb")
C_TAG   = colors.HexColor("#e8e5df")

_EYEBROW     = ParagraphStyle("eyebrow",   fontName="IBMPlexMono-Bold", fontSize=7.5, textColor=C_MUTED,  leading=10)
_LABEL       = ParagraphStyle("label",     fontName="IBMPlexMono-Bold", fontSize=7.5, textColor=C_MUTED,  leading=10)
_BODY        = ParagraphStyle("body",      fontName="IBMPlexSans",      fontSize=11,  textColor=C_BLACK,  leading=16)
_MUTED_P     = ParagraphStyle("muted",     fontName="IBMPlexSans",      fontSize=9,   textColor=C_MUTED,  leading=13)
_RIGHT_MONO  = ParagraphStyle("rmono",     fontName="IBMPlexMono-Bold", fontSize=11,  textColor=C_BLACK,  leading=16, alignment=2)
_RIGHT_MUTED = ParagraphStyle("rmuted",    fontName="IBMPlexSans",      fontSize=9,   textColor=C_MUTED,  leading=13, alignment=2)
_TH          = ParagraphStyle("th",        fontName="IBMPlexMono-Bold", fontSize=7.5, textColor=C_BG,     leading=10)
_TD          = ParagraphStyle("td",        fontName="IBMPlexSans",      fontSize=11,  textColor=C_BLACK,  leading=14)
_TD_NUM      = ParagraphStyle("tdnum",     fontName="IBMPlexSans",      fontSize=11,  textColor=C_BLACK,  leading=14, alignment=2)
_TOT_LABEL   = ParagraphStyle("tot-label", fontName="IBMPlexMono-Bold", fontSize=7.5, textColor=C_MUTED,  leading=10, alignment=2)
_TOT_VALUE   = ParagraphStyle("tot-value", fontName="IBMPlexSans",      fontSize=11,  textColor=C_BLACK,  leading=14, alignment=2)


def generate_po_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    W   = A4[0] - 40 * mm

    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm,  bottomMargin=20*mm)

    def _bg(canvas, _doc):
        canvas.saveState()
        canvas.setFillColor(C_BG)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        canvas.restoreState()

    elems = []

    # ── Header ──────────────────────────────────────────────────────────────
    po_number = data.get("po_number", "")
    date      = data.get("date", "")

    header = Table(
        [[Paragraph("PURCHASE ORDER", _EYEBROW), Paragraph(po_number, _RIGHT_MONO)],
         [Paragraph("",              _MUTED_P),  Paragraph(date,      _RIGHT_MUTED)]],
        colWidths=[W * 0.6, W * 0.4],
    )
    header.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    elems.append(header)
    elems.append(Spacer(1, 10))
    elems.append(HRFlowable(width="100%", thickness=2, color=C_BLACK, spaceAfter=10))

    # ── Vendor ──────────────────────────────────────────────────────────────
    vendor = data.get("vendor", {})
    elems.append(Paragraph("VENDOR", _LABEL))
    elems.append(Spacer(1, 4))
    elems.append(Paragraph(vendor.get("name", ""), _BODY))
    if vendor.get("address"):
        elems.append(Paragraph(vendor["address"], _MUTED_P))
    elems.append(Spacer(1, 10))
    elems.append(HRFlowable(width="100%", thickness=1, color=C_RULE, spaceAfter=8))

    # ── Line items ──────────────────────────────────────────────────────────
    lines      = data.get("lines", [])
    col_widths = [W * 0.45, W * 0.15, W * 0.20, W * 0.20]

    table_data = [[
        Paragraph("PRODUCT",    _TH),
        Paragraph("QTY",        _TH),
        Paragraph("UNIT PRICE", _TH),
        Paragraph("TOTAL",      _TH),
    ]]
    for line in lines:
        table_data.append([
            Paragraph(str(line.get("product", "")),              _TD),
            Paragraph(str(line.get("qty", "")),                  _TD_NUM),
            Paragraph(f'{float(line.get("unit_price", 0)):.2f}', _TD_NUM),
            Paragraph(f'{float(line.get("total", 0)):.2f}',      _TD_NUM),
        ])

    row_count  = len(table_data)
    style_cmds = [
        ("BACKGROUND",    (0, 0),  (-1, 0),  C_BLACK),
        ("BACKGROUND",    (0, 1),  (-1, -1), C_BG),
        ("TOPPADDING",    (0, 0),  (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0),  (-1, -1), 6),
        ("LEFTPADDING",   (0, 0),  (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0),  (-1, -1), 8),
        ("LINEBELOW",     (0, 1),  (-1, -1), 0.5, C_RULE),
        ("VALIGN",        (0, 0),  (-1, -1), "MIDDLE"),
    ]
    for i in range(2, row_count, 2):
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), C_TAG))

    items_table = Table(table_data, colWidths=col_widths)
    items_table.setStyle(TableStyle(style_cmds))
    elems.append(items_table)
    elems.append(Spacer(1, 12))

    # ── Totals ──────────────────────────────────────────────────────────────
    totals_w    = W * 0.35
    totals_data = []
    for label, key in [("SUBTOTAL", "subtotal"), ("TAX", "tax"), ("TOTAL", "total")]:
        val = data.get(key)
        if val is not None:
            totals_data.append([Paragraph(label, _TOT_LABEL), Paragraph(f"{float(val):.2f}", _TOT_VALUE)])

    if totals_data:
        totals_table = Table(totals_data, colWidths=[totals_w * 0.5, totals_w * 0.5])
        totals_table.setStyle(TableStyle([
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("LINEABOVE",     (0, -1), (-1, -1), 1.5, C_BLACK),
        ]))
        outer = Table([[Paragraph("", _BODY), totals_table]], colWidths=[W - totals_w, totals_w])
        outer.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ]))
        elems.append(outer)

    # ── Notes ───────────────────────────────────────────────────────────────
    notes = data.get("notes", "")
    if notes:
        elems.append(Spacer(1, 12))
        elems.append(HRFlowable(width="100%", thickness=1, color=C_RULE, spaceAfter=8))
        elems.append(Paragraph("NOTES", _LABEL))
        elems.append(Spacer(1, 4))
        elems.append(Paragraph(notes, _MUTED_P))

    doc.build(elems, onFirstPage=_bg, onLaterPages=_bg)
    buf.seek(0)
    return buf.read()
