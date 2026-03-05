import base64
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_chart_base64(spec: dict) -> str:
    chart_type = spec.get("type", "bar")
    title = spec.get("title", "")
    data = spec.get("data", [])

    fig, ax = plt.subplots(figsize=(8, 4))

    if chart_type == "pie":
        labels = [d.get("name", "") for d in data]
        values = [d.get("value", 0) for d in data]
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.set_title(title)

    else:
        x_key = spec.get("x_key", "")
        series = spec.get("series", [])
        x_labels = [str(d.get(x_key, "")) for d in data]
        x = range(len(x_labels))

        for i, s in enumerate(series):
            key = s.get("key", "")
            label = s.get("label", key)
            values = [d.get(key, 0) for d in data]
            if chart_type == "line":
                ax.plot(list(x), values, marker="o", label=label)
            else:
                width = 0.8 / max(len(series), 1)
                offset = (i - len(series) / 2 + 0.5) * width
                ax.bar([xi + offset for xi in x], values, width=width, label=label)

        ax.set_xticks(list(x))
        ax.set_xticklabels(x_labels, rotation=30, ha="right", fontsize=8)
        ax.set_title(title)
        if series:
            ax.legend()

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode()
