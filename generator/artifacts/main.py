import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from generator.artifacts.utils.chart import bar_chart, line_chart, pie_chart
from generator.artifacts.utils.table import invoice_table, sales_table
from generator.artifacts.utils.pdf import purchase_order

OUTPUT = os.path.join(os.path.dirname(__file__), "output")


def run():
    os.makedirs(OUTPUT, exist_ok=True)

    for name, fn in [("bar_chart", bar_chart), ("line_chart", line_chart), ("pie_chart", pie_chart)]:
        with open(os.path.join(OUTPUT, f"{name}.png"), "wb") as f:
            f.write(fn())
        print(f"chart: {name}.png")

    for name, fn in [("sales_table", sales_table), ("invoice_table", invoice_table)]:
        with open(os.path.join(OUTPUT, f"{name}.png"), "wb") as f:
            f.write(fn())
        print(f"table: {name}.png")

    with open(os.path.join(OUTPUT, "purchase_order.pdf"), "wb") as f:
        f.write(purchase_order())
    print("pdf: purchase_order.pdf")


if __name__ == "__main__":
    run()
