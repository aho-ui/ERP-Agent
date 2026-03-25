import io
import os
from PIL import Image, ImageDraw, ImageFont

# import matplotlib
# matplotlib.use("Agg")
# import matplotlib.pyplot as plt

_BASE = os.path.dirname(__file__)
_FONT_HEADER = os.path.join(_BASE, "fonts", "IBMPlexMono-Bold.ttf")
_FONT_BODY = os.path.join(_BASE, "fonts", "IBMPlexSans-Regular.ttf")


def render_table_image(columns: list, rows: list, title: str = "") -> bytes:
    PAD_X = 16
    HEADER_H = 36
    ROW_H = 30

    font_header = ImageFont.truetype(_FONT_HEADER, 11)
    font_body = ImageFont.truetype(_FONT_BODY, 12)

    col_widths = []
    for i, col in enumerate(columns):
        w = font_header.getlength(col.upper())
        for row in rows:
            val = str(row[i]) if i < len(row) and row[i] is not None else ""
            w = max(w, font_body.getlength(val))
        col_widths.append(int(w) + PAD_X * 2)

    total_w = sum(col_widths)
    total_h = HEADER_H + ROW_H * len(rows)

    img = Image.new("RGB", (total_w, total_h), "#0d0d0d")
    draw = ImageDraw.Draw(img)

    x = 0
    for i, col in enumerate(columns):
        cw = col_widths[i]
        draw.rectangle([x, 0, x + cw - 1, HEADER_H - 1], fill="#0a0a0a")
        draw.text((x + cw // 2, HEADER_H // 2), col.upper(), font=font_header, fill="#f5f4f0", anchor="mm")
        x += cw

    for r, row in enumerate(rows):
        y = HEADER_H + r * ROW_H
        bg = "#1a1a1a" if r % 2 == 0 else "#0d0d0d"
        x = 0
        for i in range(len(columns)):
            cw = col_widths[i]
            val = str(row[i]) if i < len(row) and row[i] is not None else ""
            draw.rectangle([x, y, x + cw - 1, y + ROW_H - 1], fill=bg)
            draw.text((x + cw // 2, y + ROW_H // 2), val, font=font_body, fill="#f5f4f0", anchor="mm")
            x += cw

    for r in range(len(rows) + 2):
        y = 0 if r == 0 else (HEADER_H if r == 1 else HEADER_H + (r - 1) * ROW_H)
        draw.line([(0, y), (total_w - 1, y)], fill="#2c2c2c", width=1)
    draw.line([(0, total_h - 1), (total_w - 1, total_h - 1)], fill="#2c2c2c", width=1)

    x = 0
    for cw in col_widths:
        draw.line([(x, 0), (x, total_h - 1)], fill="#2c2c2c", width=1)
        x += cw
    draw.line([(total_w - 1, 0), (total_w - 1, total_h - 1)], fill="#2c2c2c", width=1)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()

# def render_table_image_matplotlib(columns: list, rows: list, title: str = "") -> bytes:
#     col_count = max(len(columns), 1)
#     row_count = len(rows)
#     cell_w = 1.6
#     cell_h = 0.35
#     fig_w = col_count * cell_w
#     fig_h = (row_count + 1) * cell_h
#
#     fig, ax = plt.subplots(figsize=(fig_w, fig_h))
#     ax.set_position([0, 0, 1, 1])
#     ax.axis("off")
#
#     table = ax.table(
#         cellText=rows,
#         colLabels=[c.upper() for c in columns],
#         cellLoc="center",
#         loc="center",
#         bbox=[0, 0, 1, 1],
#     )
#     table.auto_set_font_size(False)
#     table.set_fontsize(9)
#
#     fig.patch.set_facecolor("#0d0d0d")
#     ax.set_facecolor("#0d0d0d")
#
#     for (row, col), cell in table.get_celld().items():
#         cell.set_linewidth(0.4)
#         cell.set_edgecolor("#2c2c2c")
#         if row == 0:
#             cell.set_facecolor("#f5f4f0")
#             cell.get_text().set_color("#0d0d0d")
#             cell.get_text().set_fontfamily("DejaVu Sans Mono")
#             cell.get_text().set_fontweight("bold")
#         elif row % 2 == 0:
#             cell.set_facecolor("#1a1a1a")
#             cell.get_text().set_color("#f5f4f0")
#             cell.get_text().set_fontfamily("DejaVu Sans")
#         else:
#             cell.set_facecolor("#0d0d0d")
#             cell.get_text().set_color("#f5f4f0")
#             cell.get_text().set_fontfamily("DejaVu Sans")
#
#     buf = io.BytesIO()
#     plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=130, facecolor="#0d0d0d")
#     plt.close(fig)
#     buf.seek(0)
#     return buf.read()
