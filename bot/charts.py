"""Generate price‐history chart images with matplotlib."""

from __future__ import annotations

import io
import datetime as dt

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def generate_price_chart(
    prices: list[list[float]],
    title: str = "Price (USD)",
    days: int = 7,
) -> bytes:
    dates = [dt.datetime.utcfromtimestamp(p[0] / 1000) for p in prices]
    values = [p[1] for p in prices]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, values, color="#00d4aa", linewidth=1.5)
    ax.fill_between(dates, values, alpha=0.15, color="#00d4aa")

    ax.set_title(title, fontsize=14, color="white")
    ax.set_facecolor("#1a1a2e")
    fig.patch.set_facecolor("#16213e")
    ax.tick_params(colors="white")
    ax.spines["bottom"].set_color("#444")
    ax.spines["left"].set_color("#444")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.label.set_color("white")
    ax.xaxis.label.set_color("white")

    if days <= 1:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    elif days <= 30:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()

    ax.set_ylabel("USD", fontsize=10, color="white")
    ax.grid(True, alpha=0.15)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
