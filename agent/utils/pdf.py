import io
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

_BASE = os.path.dirname(__file__)
pdfmetrics.registerFont(TTFont("IBMPlexSans", os.path.join(_BASE, "fonts", "IBMPlexSans-Regular.ttf")))
pdfmetrics.registerFont(TTFont("IBMPlexMono-Bold", os.path.join(_BASE, "fonts", "IBMPlexMono-Bold.ttf")))

_BG = "#0d0d0d"
_HEADER_BG = "#0a0a0a"
_ROW_EVEN = "#1a1a1a"
_ROW_ODD = "#0d0d0d"
_TEXT = "#f5f4f0"
_GRID = "#2c2c2c"


def generate_pdf_bytes(columns: list, rows: list, title: str = "") -> bytes:
    buf = io.BytesIO()
    page = landscape(A4) if len(columns) > 6 else A4

    doc = SimpleDocTemplate(buf, pagesize=page, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)

    header_style = ParagraphStyle("header", fontName="IBMPlexMono-Bold", fontSize=8, textColor=colors.HexColor(_TEXT))
    cell_style = ParagraphStyle("cell", fontName="IBMPlexSans", fontSize=8, textColor=colors.HexColor(_TEXT), leading=11)

    header_row = [Paragraph(str(c).upper(), header_style) for c in columns]
    data_rows = [[Paragraph("" if c is None else str(c), cell_style) for c in row] for row in rows]
    table_data = [header_row] + data_rows

    col_count = len(columns)
    available = page[0] - 72
    col_width = available / col_count

    t = Table(table_data, colWidths=[col_width] * col_count, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_HEADER_BG)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(_TEXT)),
        ("FONTNAME", (0, 0), (-1, 0), "IBMPlexMono-Bold"),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor(_TEXT)),
        ("FONTNAME", (0, 1), (-1, -1), "IBMPlexSans"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor(_ROW_EVEN), colors.HexColor(_ROW_ODD)]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(_GRID)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))

    def _bg(canvas, doc):
        canvas.setFillColor(colors.HexColor(_BG))
        canvas.rect(0, 0, page[0], page[1], fill=1, stroke=0)

    doc.build([t], onFirstPage=_bg, onLaterPages=_bg)
    buf.seek(0)
    return buf.read()


# def generate_pdf_base64(columns: list, rows: list, title: str = "") -> str:
#     import base64
#     data = generate_pdf_bytes(columns, rows, title=title)
#     return "data:application/pdf;base64," + base64.b64encode(data).decode()
