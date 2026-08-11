"""Render a real, accurate data/category chart with matplotlib (brand-styled).

Unlike tools/make_infographics.py (generative AI images), this renders text
and layout deterministically -- use it whenever labels, categories, or
numbers need to be guaranteed accurate rather than "AI-drawn."

Usage:
    python tools/make_chart.py --data PATH [--brand PATH] [--out PATH]

Data JSON shape -- any of:
  Category grid (no magnitude, just a labeled set):
    {"title": "...", "items": ["Customer service", "Healthcare", ...]}
  Horizontal bar (has magnitude, categories compared independently):
    {"title": "...", "categories": ["A", "B"], "values": [10, 25], "unit": "%"}
  Pie (has magnitude AND values are true parts of one whole -- must sum to
  ~100, otherwise it misrepresents completeness; use a bar chart instead
  if the categories don't exhaustively cover the whole):
    {"title": "...", "type": "pie", "categories": ["A", "B"], "values": [70, 30], "unit": "%"}
"""
import argparse
import colorsys
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

DEFAULT_BRAND_PATH = Path("assets/brand/brand.json")


def tint_ramp(hex_color: str, n: int) -> list[str]:
    """n shades of one hue, darkest to lightest -- a sequential ramp for
    magnitude, per the single-hue-for-magnitude rule (never a rainbow)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    shades = []
    for i in range(n):
        lightness = l + (0.85 - l) * (i / max(n - 1, 1))
        r2, g2, b2 = colorsys.hls_to_rgb(h, lightness, s)
        shades.append(f"#{int(r2*255):02x}{int(g2*255):02x}{int(b2*255):02x}")
    return shades


def render_category_grid(data: dict, brand: dict, out_path: Path) -> None:
    items = data["items"]
    cols = 2
    rows = -(-len(items) // cols)  # ceil

    fig, ax = plt.subplots(figsize=(10, 1.1 * rows + 0.8), dpi=200)
    fig.patch.set_facecolor(brand["background_color"])
    ax.set_facecolor(brand["background_color"])
    ax.set_xlim(0, cols)
    ax.set_ylim(0, rows)
    ax.invert_yaxis()
    ax.axis("off")

    if data.get("title"):
        ax.text(
            0, -0.55, data["title"],
            fontsize=15, fontweight="bold", color=brand["text_color"],
            ha="left", va="center",
        )

    chip_pad = 0.08
    for i, label in enumerate(items):
        col, row = i % cols, i // cols
        x0, y0 = col + chip_pad, row + chip_pad
        w, h = 1 - 2 * chip_pad, 1 - 2 * chip_pad
        chip = FancyBboxPatch(
            (x0, y0), w, h,
            boxstyle="round,pad=0,rounding_size=0.08",
            linewidth=1.2,
            edgecolor=brand["divider_color"],
            facecolor=brand.get("wrapper_background", "#000000"),
        )
        ax.add_patch(chip)
        # accent marker
        ax.add_patch(plt.Circle((x0 + 0.16, y0 + h / 2), 0.045, color=brand["accent_color"]))
        ax.text(
            x0 + 0.32, y0 + h / 2, label,
            fontsize=11.5, color=brand["text_color"], va="center", ha="left",
        )

    plt.tight_layout(pad=0.6)
    fig.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)


def render_bar_chart(data: dict, brand: dict, out_path: Path) -> None:
    categories = data["categories"]
    values = data["values"]
    unit = data.get("unit", "")

    fig, ax = plt.subplots(figsize=(10, 0.6 * len(categories) + 1.5), dpi=200)
    fig.patch.set_facecolor(brand["background_color"])
    ax.set_facecolor(brand["background_color"])

    y_pos = range(len(categories))
    bars = ax.barh(list(y_pos), values, color=brand["accent_color"], height=0.55)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
            f"{value}{unit}", va="center", fontsize=10.5, color=brand["text_color"],
        )

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(categories, color=brand["text_color"], fontsize=11)
    ax.invert_yaxis()
    ax.tick_params(axis="x", colors=brand["muted_color"], labelsize=9)
    for spine in ("top", "right", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(brand["divider_color"])
    ax.set_xticks([])

    if data.get("title"):
        ax.set_title(data["title"], color=brand["text_color"], fontsize=14, fontweight="bold", loc="left", pad=14)

    plt.tight_layout()
    fig.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)


def render_pie_chart(data: dict, brand: dict, out_path: Path) -> None:
    categories = data["categories"]
    values = data["values"]
    unit = data.get("unit", "")
    total = sum(values)

    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=200)
    fig.patch.set_facecolor(brand["background_color"])
    ax.set_facecolor(brand["background_color"])
    ax.set_xlim(-1.7, 1.7)
    ax.set_ylim(-1.5, 1.5)

    colors = tint_ramp(brand["accent_color"], len(values))
    wedges, _ = ax.pie(
        values,
        colors=colors,
        startangle=90,
        counterclock=False,
        wedgeprops={"edgecolor": brand["background_color"], "linewidth": 2},
    )
    ax.set_aspect("equal")

    # Direct labels (<=4 slices) with a leader line, outside the pie.
    for wedge, category, value in zip(wedges, categories, values):
        angle = (wedge.theta2 + wedge.theta1) / 2
        import math
        x, y = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        ha = "left" if x >= 0 else "right"
        ax.annotate(
            f"{category}\n{value}{unit}",
            xy=(x * 0.9, y * 0.9), xytext=(x * 1.35, y * 1.15),
            ha=ha, va="center", fontsize=11, color=brand["text_color"],
            arrowprops={"arrowstyle": "-", "color": brand["muted_color"], "lw": 1},
        )

    if data.get("title"):
        ax.set_title(data["title"], color=brand["text_color"], fontsize=14, fontweight="bold", pad=18)
    if abs(total - 100) > 1 and unit == "%":
        ax.text(
            0, -1.42, f"Note: categories sum to {total}%, not shown as 100%",
            ha="center", fontsize=8.5, color=brand["muted_color"],
        )

    ax.axis("off")
    fig.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a brand-styled chart/infographic with matplotlib")
    parser.add_argument("--data", required=True, help="Path to chart data JSON")
    parser.add_argument("--brand", default=str(DEFAULT_BRAND_PATH), help="Path to brand.json")
    parser.add_argument("--out", required=True, help="Output PNG path")
    args = parser.parse_args()

    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    brand = json.loads(Path(args.brand).read_text(encoding="utf-8"))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if data.get("type") == "pie":
        render_pie_chart(data, brand, out_path)
    elif "values" in data:
        render_bar_chart(data, brand, out_path)
    else:
        render_category_grid(data, brand, out_path)

    print(str(out_path))


if __name__ == "__main__":
    main()
