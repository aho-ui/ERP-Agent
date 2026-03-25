import io
import openpyxl


def generate_xlsx_bytes(columns: list, rows: list) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(columns)
    for row in rows:
        ws.append([("" if c is None else c) for c in row])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
