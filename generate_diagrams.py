"""
generate_diagrams.py
Generates two architecture diagrams saved to outputs/:
  - software_architecture.png   (system / software pipeline)
  - nn_architecture.png         (CNN layer diagram)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

OUT = "outputs"


# ─────────────────────────────────────────────────────────────────────────────
# Palette
# ─────────────────────────────────────────────────────────────────────────────
NAVY   = "#1a237e"
BLUE   = "#1565c0"
SKY    = "#42a5f5"
GREEN  = "#2e7d32"
ORANGE = "#e65100"
PURPLE = "#6a1b9a"
GREY   = "#546e7a"
LIGHT  = "#f5f7fa"
WHITE  = "#ffffff"


def rounded_box(ax, x, y, w, h, color, text, fontsize=9, textcolor=WHITE,
                radius=0.04, alpha=1.0, zorder=2):
    box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                         boxstyle=f"round,pad=0,rounding_size={radius}",
                         facecolor=color, edgecolor=WHITE,
                         linewidth=1.2, zorder=zorder, alpha=alpha)
    ax.add_patch(box)
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            color=textcolor, fontweight="bold", zorder=zorder+1,
            multialignment="center")


def arrow(ax, x0, y0, x1, y1, color=GREY, lw=1.5, zorder=1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", color=color,
                                lw=lw, mutation_scale=12),
                zorder=zorder)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Software / system architecture
# ─────────────────────────────────────────────────────────────────────────────

def draw_software_architecture():
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.set_xlim(0, 14); ax.set_ylim(0, 5)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE)

    # ── Layer labels ─────────────────────────────────────────────────────────
    layer_info = [
        # (x_centre, label, sublabel, color)
        (1.4,  "User\nInput",       "Mouse / touch\ndrawing",         NAVY),
        (3.5,  "Streamlit\nCanvas", "RGBA image\n1800×400 px",        BLUE),
        (5.6,  "OpenCV\nSegmentor", "Greyscale → thresh\n→ contours", GREEN),
        (7.7,  "CNN\nClassifier",   "28×28 ROI\n→ softmax(14)",       PURPLE),
        (9.8,  "Expression\nBuilder","Symbol list\n→ string",         ORANGE),
        (11.9, "AST\nEvaluator",    "Safe arithmetic\neval",          NAVY),
    ]

    BOX_W = 1.7;  BOX_H = 1.1;  Y_BOX = 3.3
    for x, lbl, sub, col in layer_info:
        rounded_box(ax, x, Y_BOX, BOX_W, BOX_H, col, lbl, fontsize=9)
        ax.text(x, Y_BOX - 0.85, sub, ha="center", va="top", fontsize=7.5,
                color=GREY, multialignment="center")

    # Arrows between boxes
    for i in range(len(layer_info) - 1):
        x0 = layer_info[i][0]   + BOX_W / 2
        x1 = layer_info[i+1][0] - BOX_W / 2
        arrow(ax, x0, Y_BOX, x1, Y_BOX, color=GREY)

    # ── Output / feedback row ─────────────────────────────────────────────────
    outputs = [
        (5.6,  "Bounding boxes\n+ debug overlay", GREEN),
        (7.7,  "Symbol chips\n(colour-coded)",     PURPLE),
        (11.9, "Numeric result\nor error msg",      NAVY),
    ]
    Y_OUT = 1.5
    for x, txt, col in outputs:
        rounded_box(ax, x, Y_OUT, 1.7, 0.75, col, txt,
                    fontsize=7.5, alpha=0.25, textcolor="#222222")
        arrow(ax, x, Y_BOX - BOX_H/2, x, Y_OUT + 0.375, color=col, lw=1.2)

    # ── Streamlit UI band ────────────────────────────────────────────────────
    band = FancyBboxPatch((0.45, 0.5), 13.1, 4.1,
                          boxstyle="round,pad=0,rounding_size=0.1",
                          facecolor=LIGHT, edgecolor=BLUE, linewidth=1.0,
                          alpha=0.25, zorder=0)
    ax.add_patch(band)
    ax.text(0.7, 4.55, "Streamlit web app  (draw.py)", fontsize=8,
            color=BLUE, fontweight="bold")

    # ── Model files note ──────────────────────────────────────────────────────
    ax.text(7.7, 0.25,
            "Model: outputs/best_model.keras · Classes: outputs/class_names.json",
            ha="center", va="bottom", fontsize=7.5, color=GREY, style="italic")

    ax.set_title("Software Architecture — Draw & Solve", fontsize=12,
                 fontweight="bold", color=NAVY, pad=6)
    fig.tight_layout(pad=0.3)
    path = f"{OUT}/software_architecture.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path}")


# ─────────────────────────────────────────────────────────────────────────────
# 2. CNN layer diagram
# ─────────────────────────────────────────────────────────────────────────────

def draw_nn_architecture():
    fig, ax = plt.subplots(figsize=(16, 5.5))
    ax.set_xlim(0, 16); ax.set_ylim(0, 5.5)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE)

    # Each entry: (x_centre, label_lines, sublabel, width, color)
    layers = [
        # Input
        (0.8,  ["Input", "28×28×1"],        "",               1.2, SKY),
        # Block 1
        (2.5,  ["Conv2D 32", "3×3 + BN"],   "×2",             1.4, BLUE),
        (3.9,  ["MaxPool", "2×2"],           "→ 14×14×32",    1.1, BLUE),
        (4.85, ["Drop", "0.25"],             "",              0.85, "#90caf9"),
        # Block 2
        (6.3,  ["Conv2D 64", "3×3 + BN"],   "×2",             1.4, PURPLE),
        (7.7,  ["MaxPool", "2×2"],           "→ 7×7×64",      1.1, PURPLE),
        (8.65, ["Drop", "0.25"],             "",              0.85, "#ce93d8"),
        # Block 3
        (10.1, ["Conv2D 128", "3×3 + BN"],  "×1",             1.4, GREEN),
        (11.4, ["Drop", "0.25"],             "",              0.85, "#a5d6a7"),
        # Global pool + Dense
        (12.55,["Global Avg", "Pool → 128"], "",               1.3, GREEN),
        (14.0, ["Dense 256", "+ BN"],        "Drop 0.5",       1.3, ORANGE),
        # Output
        (15.4, ["Softmax", "14"],            "Output",         1.0, NAVY),
    ]

    BOX_H = 1.1;  Y = 3.0

    for x, lines, sub, w, col in layers:
        lbl = "\n".join(lines)
        rounded_box(ax, x, Y, w, BOX_H, col, lbl, fontsize=8)
        if sub:
            ax.text(x, Y - BOX_H/2 - 0.15, sub, ha="center", va="top",
                    fontsize=7, color=GREY)

    # Arrows
    prev_x = None
    prev_w = None
    for x, _, _, w, _ in layers:
        if prev_x is not None:
            arrow(ax, prev_x + prev_w/2, Y, x - w/2, Y, color=GREY, lw=1.2)
        prev_x, prev_w = x, w

    # Block brackets
    def bracket(ax, x0, x1, label, color):
        y_b = Y - BOX_H/2 - 0.55
        ax.annotate("", xy=(x1, y_b), xytext=(x0, y_b),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.0))
        ax.text((x0+x1)/2, y_b - 0.18, label, ha="center", va="top",
                fontsize=7.5, color=color, fontweight="bold")

    bracket(ax, 1.85, 5.3,   "Conv Block 1  (32 filters)", BLUE)
    bracket(ax, 5.65, 9.1,   "Conv Block 2  (64 filters)", PURPLE)
    bracket(ax, 9.45, 12.9,  "Conv Block 3  (128 filters)", GREEN)
    bracket(ax, 13.15, 16.45,"Dense Head", ORANGE)

    # Param count row
    params = [
        (0.8,   "—"),
        (3.2,   "9.9K"),
        (7.0,   "55.7K"),
        (10.8,  "74.4K"),
        (14.3,  "299.8K"),
        (15.95, "3.6K"),
    ]
    for x, p in params:
        ax.text(x, Y + BOX_H/2 + 0.12, p, ha="center", va="bottom",
                fontsize=7, color=GREY)
    ax.text(0.0, Y + BOX_H/2 + 0.12, "Params:", ha="left", va="bottom",
            fontsize=7, color=GREY, style="italic")

    ax.set_title(
        "CNN Architecture — 441K total parameters  "
        "(BN = Batch Normalisation · Drop = Dropout)",
        fontsize=11, fontweight="bold", color=NAVY, pad=6)
    fig.tight_layout(pad=0.3)
    path = f"{OUT}/nn_architecture.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path}")


if __name__ == "__main__":
    draw_software_architecture()
    draw_nn_architecture()
    print("Done.")
