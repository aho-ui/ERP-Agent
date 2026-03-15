import base64
import io
import csv


def generate_csv_base64(columns: list, rows: list) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    writer.writerows([("" if c is None else str(c)) for c in row] for row in rows)
    data = buf.getvalue().encode("utf-8")
    return "data:text/csv;base64," + base64.b64encode(data).decode()
