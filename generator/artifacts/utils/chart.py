import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np


def _save_fig(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _style_ax(ax):
    ax.set_facecolor("#0d0d0d")
    ax.tick_params(colors="#f5f4f0", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#2c2c2c")
    ax.yaxis.label.set_color("#f5f4f0")
    ax.xaxis.label.set_color("#f5f4f0")
    ax.grid(axis="y", color="#1f1f1f", linewidth=0.5)


def bar_chart() -> bytes:
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    revenue   = [41200, 53800, 47600, 62100, 58900, 71400, 68200, 74500, 69300, 82100, 91500, 104200]
    target    = [45000, 50000, 55000, 60000, 60000, 65000, 70000, 75000, 75000, 80000, 90000, 100000]
    prev_year = [32100, 41500, 38700, 49800, 46200, 55300, 51900, 58400, 54700, 63200, 72400, 84600]

    x = np.arange(len(months))
    w = 0.28

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor("#0d0d0d")
    _style_ax(ax)

    ax.bar(x - w, prev_year, w, label="Prev Year", color="#2c2c2c")
    ax.bar(x,     revenue,   w, label="Revenue",   color="#f5f4f0")
    ax.bar(x + w, target,    w, label="Target",    color="#6b6760")

    ax.set_xticks(x)
    ax.set_xticklabels(months)
    ax.set_title("Annual Revenue vs Target vs Previous Year", color="#f5f4f0", fontsize=13, pad=12)
    ax.set_ylabel("USD")
    ax.legend(facecolor="#1a1a1a", labelcolor="#f5f4f0", fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v/1000:.0f}k"))

    return _save_fig(fig)


def line_chart() -> bytes:
    quarters = ["Q1 '24", "Q2 '24", "Q3 '24", "Q4 '24", "Q1 '25", "Q2 '25", "Q3 '25", "Q4 '25"]
    sales     = [128000, 154000, 141000, 187000, 162000, 198000, 211000, 243000]
    purchases = [94000,  112000, 103000, 138000, 119000, 147000, 158000, 182000]
    invoices  = [121000, 148000, 135000, 179000, 155000, 191000, 204000, 237000]
    payments  = [108000, 139000, 127000, 164000, 143000, 178000, 196000, 229000]

    fig, ax = plt.subplots(figsize=(13, 5))
    fig.patch.set_facecolor("#0d0d0d")
    _style_ax(ax)

    for data, label, color, ls in [
        (sales,     "Sales Orders",  "#f5f4f0", "-"),
        (invoices,  "Invoices",      "#c8c4bb", "--"),
        (purchases, "Purchases",     "#6b6760", "-"),
        (payments,  "Payments",      "#e8e5df", ":"),
    ]:
        ax.plot(quarters, data, marker="o", markersize=5, label=label, color=color, linestyle=ls, linewidth=1.8)

    ax.set_title("Quarterly ERP Financial Overview (2024–2025)", color="#f5f4f0", fontsize=13, pad=12)
    ax.set_ylabel("USD")
    ax.legend(facecolor="#1a1a1a", labelcolor="#f5f4f0", fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v/1000:.0f}k"))
    ax.fill_between(quarters, payments, sales, alpha=0.04, color="#f5f4f0")

    return _save_fig(fig)


def pie_chart() -> bytes:
    fig = plt.figure(figsize=(14, 6))
    fig.patch.set_facecolor("#0d0d0d")
    gs = gridspec.GridSpec(1, 2, figure=fig)

    # Left: revenue by category
    ax1 = fig.add_subplot(gs[0])
    ax1.set_facecolor("#0d0d0d")
    cat_labels = ["Electronics", "Furniture", "Office Supplies", "Software", "Services", "Hardware"]
    cat_values = [87400, 34200, 18600, 62100, 29800, 41500]
    cat_colors = ["#4a90d9", "#7ec8a4", "#e8a838", "#d9534f", "#9b59b6", "#5bc0de"]
    wedges, texts, autotexts = ax1.pie(
        cat_values, labels=cat_labels, colors=cat_colors,
        autopct="%1.1f%%", startangle=140, pctdistance=0.82,
        wedgeprops={"linewidth": 0.6, "edgecolor": "#0d0d0d"},
    )
    for t in texts + autotexts:
        t.set_color("#f5f4f0")
        t.set_fontsize(8)
    ax1.set_title("Revenue by Product Category", color="#f5f4f0", fontsize=11, pad=10)

    # Right: order status distribution
    ax2 = fig.add_subplot(gs[1])
    ax2.set_facecolor("#0d0d0d")
    status_labels = ["Confirmed", "Draft", "Cancelled", "Pending Review"]
    status_values = [312, 87, 24, 51]
    status_colors = ["#7ec8a4", "#e8a838", "#d9534f", "#4a90d9"]
    wedges2, texts2, autotexts2 = ax2.pie(
        status_values, labels=status_labels, colors=status_colors,
        autopct="%1.1f%%", startangle=90, pctdistance=0.78,
        wedgeprops={"linewidth": 0.6, "edgecolor": "#0d0d0d"},
    )
    for t in texts2 + autotexts2:
        t.set_color("#f5f4f0")
        t.set_fontsize(8)
    ax2.set_title("Sales Order Status Distribution", color="#f5f4f0", fontsize=11, pad=10)

    fig.suptitle("Business Analytics Overview", color="#f5f4f0", fontsize=13, y=1.02)
    return _save_fig(fig)
