#!/usr/bin/env python3
"""Generate presentation figures: per-class accuracy + failure case montage."""

import os, json, random
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import cv2
import tensorflow as tf

IMG_SIZE    = 28
OUTPUT_DIR  = "outputs"
DATASET_DIR = "dataset"
EXCLUDED    = {"dec", "eq", "x", "y", "z"}

FOLDER_TO_SYMBOL = {
    "0":"0","1":"1","2":"2","3":"3","4":"4",
    "5":"5","6":"6","7":"7","8":"8","9":"9",
    "add":"+","sub":"−","mul":"×","div":"÷",
}

# ── Load class names ──────────────────────────────────────────────────────────
with open(os.path.join(OUTPUT_DIR, "class_names.json")) as f:
    class_names = json.load(f)

symbols = [FOLDER_TO_SYMBOL.get(c, c) for c in class_names]

# ── Load model ────────────────────────────────────────────────────────────────
print("Loading model …")
class _CompatInputLayer(tf.keras.layers.InputLayer):
    def __init__(self, *args, **kwargs):
        kwargs.pop("optional", None)   # added in newer Keras; not in 2.14
        super().__init__(*args, **kwargs)

model = tf.keras.models.load_model(
    os.path.join(OUTPUT_DIR, "best_model.keras"),
    custom_objects={"InputLayer": _CompatInputLayer},
    compile=False,
)

# ── Load dataset (capped at 1 048 per class to match training balance) ────────
print("Loading dataset …")
X, y = [], []
random.seed(42)

for folder in sorted(os.listdir(DATASET_DIR)):
    if folder in EXCLUDED or folder not in FOLDER_TO_SYMBOL:
        continue
    if folder not in class_names:
        continue
    idx = class_names.index(folder)
    imgs = sorted(
        list((Path(DATASET_DIR) / folder).glob("*.jpg")) +
        list((Path(DATASET_DIR) / folder).glob("*.png"))
    )
    if len(imgs) > 1048:
        imgs = random.sample(imgs, 1048)
    for p in imgs:
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        img = cv2.resize(img, (IMG_SIZE, IMG_SIZE)).astype(np.float32) / 255.0
        X.append(img)
        y.append(idx)

X = np.array(X)[..., np.newaxis]
y = np.array(y)
print(f"  {len(X)} images, {len(class_names)} classes")

# ── Predict ───────────────────────────────────────────────────────────────────
print("Predicting …")
preds       = model.predict(X, batch_size=256, verbose=1)
pred_cls    = np.argmax(preds, axis=1)

# ── Figure 1: Per-class accuracy bar chart ───────────────────────────────────
per_acc = []
for i in range(len(class_names)):
    mask = y == i
    per_acc.append((pred_cls[mask] == i).mean() * 100 if mask.sum() else 0.0)

fig, ax = plt.subplots(figsize=(11, 4.5))
colors = ["#1565c0"] * 10 + ["#e65100"] * 4
bars = ax.bar(symbols, per_acc, color=colors, edgecolor="white", linewidth=0.5, width=0.7)
ax.set_ylim([min(per_acc) - 2, 100.8])
ax.set_ylabel("Accuracy (%)", fontsize=12)
ax.set_title("Per-Class Test Accuracy", fontsize=14, fontweight="bold")

mean_acc = np.mean(per_acc)
ax.axhline(mean_acc, color="#333", linestyle="--", linewidth=1.4, alpha=0.7)

for bar, acc in zip(bars, per_acc):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
            f"{acc:.1f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

legend_elems = [
    Patch(facecolor="#1565c0", label="Digits"),
    Patch(facecolor="#e65100", label="Operators"),
    Line2D([0], [0], color="#333", linestyle="--", label=f"Mean {mean_acc:.2f}%"),
]
ax.legend(handles=legend_elems, fontsize=11)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.tight_layout()
out = os.path.join(OUTPUT_DIR, "per_class_accuracy.png")
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved {out}")
print("  Per-class accuracies:")
for s, a in zip(symbols, per_acc):
    print(f"    {s}: {a:.2f}%")

# ── Figure 2: Top misclassification pairs (failure case montage) ──────────────
wrong_idx = np.where(pred_cls != y)[0]
print(f"\n{len(wrong_idx)} errors ({len(wrong_idx)/len(X)*100:.2f}%)")

pairs = defaultdict(list)
for i in wrong_idx:
    pairs[(int(y[i]), int(pred_cls[i]))].append(i)

top_pairs = sorted(pairs.items(), key=lambda kv: -len(kv[1]))
# Show up to 3 example images per pair, up to 6 pairs
N_PAIRS = min(6, len(top_pairs))
N_EACH  = 3

fig = plt.figure(figsize=(N_EACH * 2.4, N_PAIRS * 2.4))
gs  = gridspec.GridSpec(N_PAIRS, N_EACH + 1, figure=fig,
                        wspace=0.15, hspace=0.5,
                        width_ratios=[0.5] + [1] * N_EACH)

for row, ((tc, pc), indices) in enumerate(top_pairs[:N_PAIRS]):
    # Label column
    ax_lbl = fig.add_subplot(gs[row, 0])
    ax_lbl.axis("off")
    ax_lbl.text(0.5, 0.5,
                f"True: {symbols[tc]}\n→ Pred: {symbols[pc]}\n(n={len(indices)})",
                ha="center", va="center", fontsize=11,
                color="#c62828", fontweight="bold",
                transform=ax_lbl.transAxes)
    # Example images
    for col, sample_i in enumerate(indices[:N_EACH]):
        ax = fig.add_subplot(gs[row, col + 1])
        ax.imshow(X[sample_i, :, :, 0], cmap="gray", vmin=0, vmax=1)
        conf = preds[sample_i, pc] * 100
        ax.set_title(f"{conf:.0f}%", fontsize=9, color="#555")
        ax.axis("off")

fig.suptitle("Most Common Misclassifications", fontsize=14, fontweight="bold", y=1.01)
out = os.path.join(OUTPUT_DIR, "failure_cases.png")
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved {out}")

print("\nDone.")
