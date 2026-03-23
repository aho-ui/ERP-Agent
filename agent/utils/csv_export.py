import io
import csv


def generate_csv_bytes(columns: list, rows: list) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    writer.writerows([("" if c is None else str(c)) for c in row] for row in rows)
    return buf.getvalue().encode("utf-8")


# def generate_csv_base64(columns: list, rows: list) -> str:
#     import base64
#     data = generate_csv_bytes(columns, rows)
#     return "data:text/csv;base64," + base64.b64encode(data).decode()
