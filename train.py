"""
train.py  —  Unified CNN for Handwritten Math Symbols
======================================================
Dataset : sagyamthapa / Handwritten Math Symbols (Kaggle)
          https://www.kaggle.com/datasets/sagyamthapa/handwritten-math-symbols

Expected dataset layout (flat class folders under one root):
    dataset/
      0/   1/  ...  9/
      add/ sub/ mul/ div/ dec/ eq/
      x/   y/   z/

19 classes: digits 0–9 · operators +  −  ×  ÷  ·  = · variables x y z

Outputs (written to --out-dir, default ".")
-------------------------------------------
  math_model.h5             trained Keras model
  class_names.json          ordered list of class folder names (for inference)
  training_history.json     per-epoch loss / accuracy
  class_info.json           per-class folder name, symbol, sample count
  confusion_matrix.png      counts + row-normalised CM side-by-side
  training_curves.png       loss & accuracy curves

Usage
-----
  python train.py                          # data in ./dataset/
  python train.py --data /path/to/dataset
  python train.py --data dataset --epochs 30 --out-dir results/
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import tensorflow as tf
from tensorflow.keras import callbacks, layers, models
from sklearn.metrics import confusion_matrix

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

IMG_SIZE   = 28          # height = width in pixels (must match draw_new.py)
BATCH_SIZE = 64
EPOCHS     = 25
SEED       = 42
VAL_SPLIT  = 0.15        # fraction of data held out for validation
PATIENCE   = 6           # early-stopping patience (epochs)

# Maps dataset folder names → the math symbol used in expressions.
# Covers both possible naming conventions (e.g. "add" and "+").
FOLDER_TO_SYMBOL: dict[str, str] = {
    # Digits – identical
    **{str(d): str(d) for d in range(10)},
    # Operators spelled out
    "add":   "+",  "plus":   "+",
    "sub":   "-",  "minus":  "-",
    "mul":   "*",  "times":  "*",  "mult": "*",
    "div":   "/",  "divide": "/",
    "dec":   ".",  "dot":    ".",
    "eq":    "=",  "equals": "=",
    # Operators as raw characters
    "+": "+", "-": "-", "*": "*", "/": "/", ".": ".", "=": "=",
    # Variables
    "x": "x", "y": "y", "z": "z",
}

# ── MODEL ARCHITECTURE ────────────────────────────────────────────────────────

def build_model(num_classes: int) -> models.Sequential:
    """
    Three-block CNN for handwritten symbol classification.

    Architecture
    ------------
    Input  28 × 28 × 1
    Block 1  Conv(32) → BN → Conv(32) → BN → MaxPool → Dropout(0.25)
    Block 2  Conv(64) → BN → Conv(64) → BN → MaxPool → Dropout(0.25)
    Block 3  Conv(128) → BN → MaxPool → Dropout(0.25)
    Head     Flatten → Dense(256) → BN → Dropout(0.5) → Dense(num_classes)
    """
    inp = (IMG_SIZE, IMG_SIZE, 1)

    def conv_block(filters, first=False):
        blk = [
            layers.Conv2D(filters, 3, padding="same", activation="relu",
                          **({"input_shape": inp} if first else {})),
            layers.BatchNormalization(),
            layers.Conv2D(filters, 3, padding="same", activation="relu"),
            layers.BatchNormalization(),
            layers.MaxPooling2D(2),
            layers.Dropout(0.25),
        ]
        return blk

    m = models.Sequential(
        conv_block(32, first=True)
        + conv_block(64)
        + [
            layers.Conv2D(128, 3, padding="same", activation="relu"),
            layers.BatchNormalization(),
            layers.MaxPooling2D(2),
            layers.Dropout(0.25),
            layers.Flatten(),
            layers.Dense(256, activation="relu"),
            layers.BatchNormalization(),
            layers.Dropout(0.5),
            layers.Dense(num_classes, activation="softmax"),
        ],
        name="math_cnn",
    )
    return m


# ── DATA LOADING ──────────────────────────────────────────────────────────────

def load_datasets(data_dir: str):
    """
    Load train / validation splits from a folder-per-class directory.
    Images are converted to grayscale and rescaled to [0, 1].
    A small augmentation pipeline is applied during training.
    """
    common = dict(
        directory=data_dir,
        image_size=(IMG_SIZE, IMG_SIZE),
        color_mode="grayscale",
        batch_size=BATCH_SIZE,
        label_mode="int",
        seed=SEED,
        validation_split=VAL_SPLIT,
    )
    train_ds = tf.keras.utils.image_dataset_from_directory(subset="training",   **common)
    val_ds   = tf.keras.utils.image_dataset_from_directory(subset="validation", **common)
    class_names: list[str] = train_ds.class_names

    # Normalise pixel values to [0, 1]
    rescale = layers.Rescaling(1.0 / 255)

    # Light augmentation (training only) to improve robustness to drawing variation
    augment = tf.keras.Sequential([
        # fill_value=1.0 → white background after Rescaling(1/255), matching training images
        layers.RandomRotation(0.08, fill_mode="constant", fill_value=1.0),
        layers.RandomZoom(0.10,     fill_mode="constant", fill_value=1.0),
        layers.RandomTranslation(0.08, 0.08, fill_mode="constant", fill_value=1.0),
    ], name="augmentation")

    train_ds = (
        train_ds
        .map(lambda x, y: (augment(rescale(x), training=True), y),
             num_parallel_calls=tf.data.AUTOTUNE)
        .cache()
        .shuffle(10_000, seed=SEED)
        .prefetch(tf.data.AUTOTUNE)
    )
    val_ds = (
        val_ds
        .map(lambda x, y: (rescale(x), y), num_parallel_calls=tf.data.AUTOTUNE)
        .cache()
        .prefetch(tf.data.AUTOTUNE)
    )
    return train_ds, val_ds, class_names


def count_per_class(data_dir: str, class_names: list[str]) -> dict[str, int]:
    """Count image files per class folder."""
    IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff"}
    counts: dict[str, int] = {}
    for cn in class_names:
        p = Path(data_dir) / cn
        if p.is_dir():
            counts[cn] = sum(1 for f in p.iterdir() if f.suffix.lower() in IMAGE_EXTS)
        else:
            counts[cn] = 0
    return counts


# ── PLOTTING ──────────────────────────────────────────────────────────────────

def plot_training_curves(history_dict: dict, out_path: str) -> None:
    """Save a two-panel figure: loss curves (left) and accuracy curves (right)."""
    epochs = range(1, len(history_dict["loss"]) + 1)
    best_ep = int(np.argmax(history_dict["val_accuracy"])) + 1

    fig, (ax_loss, ax_acc) = plt.subplots(1, 2, figsize=(12, 4))

    # Loss panel
    ax_loss.plot(epochs, history_dict["loss"],     label="Train",      linewidth=2)
    ax_loss.plot(epochs, history_dict["val_loss"], label="Validation", linewidth=2, linestyle="--")
    ax_loss.axvline(best_ep, color="grey", linestyle=":", linewidth=1, label=f"Best epoch ({best_ep})")
    ax_loss.set_xlabel("Epoch"); ax_loss.set_ylabel("Loss")
    ax_loss.set_title("Loss"); ax_loss.legend(); ax_loss.grid(True, alpha=0.3)

    # Accuracy panel
    ax_acc.plot(epochs, history_dict["accuracy"],     label="Train",      linewidth=2)
    ax_acc.plot(epochs, history_dict["val_accuracy"], label="Validation", linewidth=2, linestyle="--")
    ax_acc.axvline(best_ep, color="grey", linestyle=":", linewidth=1, label=f"Best epoch ({best_ep})")
    ax_acc.set_xlabel("Epoch"); ax_acc.set_ylabel("Accuracy")
    ax_acc.set_title("Accuracy"); ax_acc.legend(); ax_acc.grid(True, alpha=0.3)
    ax_acc.set_ylim(bottom=max(0, min(history_dict["accuracy"]) - 0.05), top=1.01)

    fig.suptitle("Training History — Handwritten Math Symbol CNN", fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[train] Saved training curves → {out_path}")


def plot_confusion_matrix(
    y_true: list[int],
    y_pred: list[int],
    class_names: list[str],
    symbols: list[str],
    out_path: str,
) -> None:
    """
    Save a two-panel confusion matrix figure (raw counts + row-normalised).
    Tick labels show 'folder_name (symbol)' when they differ.
    """
    cm      = confusion_matrix(y_true, y_pred)
    cm_norm = cm.astype(float) / (cm.sum(axis=1, keepdims=True) + 1e-9)

    # Build human-readable tick labels
    tick_labels = [
        f"{cn}\n({sym})" if cn != sym else cn
        for cn, sym in zip(class_names, symbols)
    ]

    n = len(class_names)
    cell = max(0.55, 10 / n)  # scale cell size to number of classes
    figw = n * cell * 2 + 2
    figh = n * cell + 1

    fig, axes = plt.subplots(1, 2, figsize=(figw, figh))

    for ax, mat, title, fmt, vmax in [
        (axes[0], cm,      "Confusion Matrix – Counts",       "d",    None),
        (axes[1], cm_norm, "Confusion Matrix – Row-normalised", ".2f", 1.0),
    ]:
        sns.heatmap(
            mat, ax=ax,
            annot=True, fmt=fmt,
            cmap="Blues",
            vmin=0, vmax=vmax,
            xticklabels=tick_labels,
            yticklabels=tick_labels,
            linewidths=0.3, linecolor="lightgrey",
            cbar_kws={"shrink": 0.8},
        )
        ax.set_xlabel("Predicted label", fontsize=10)
        ax.set_ylabel("True label",      fontsize=10)
        ax.set_title(title, fontsize=11, pad=8)
        ax.tick_params(axis="both", labelsize=max(6, 9 - n // 5))

    fig.suptitle(
        f"Validation Confusion Matrix  ({n} classes, {len(y_true)} samples)",
        fontsize=12, y=1.01,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[train] Saved confusion matrix → {out_path}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Train unified math-symbol CNN")
    parser.add_argument("--data",    default="dataset",
                        help="Root directory with one sub-folder per class")
    parser.add_argument("--epochs",  type=int, default=EPOCHS)
    parser.add_argument("--batch",   type=int, default=BATCH_SIZE)
    parser.add_argument("--out-dir", default=".",
                        help="Directory for all output files (model, plots, JSON)")
    args = parser.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ── Load data ──────────────────────────────────────────────────────────
    print("[train] Loading dataset …")
    train_ds, val_ds, class_names = load_datasets(args.data)
    num_classes = len(class_names)
    symbols = [FOLDER_TO_SYMBOL.get(cn, cn) for cn in class_names]
    print(f"[train] {num_classes} classes found: {class_names}")

    # ── Count samples per class ────────────────────────────────────────────
    print("[train] Counting samples per class …")
    raw_counts = count_per_class(args.data, class_names)
    total      = sum(raw_counts.values())

    class_info = {
        "num_classes": num_classes,
        "img_size":    IMG_SIZE,
        "total_images": total,
        "val_split":   VAL_SPLIT,
        "classes": [
            {
                "index":        i,
                "folder":       cn,
                "symbol":       sym,
                "total_images": raw_counts[cn],
                "est_train":    int(raw_counts[cn] * (1 - VAL_SPLIT)),
                "est_val":      raw_counts[cn] - int(raw_counts[cn] * (1 - VAL_SPLIT)),
            }
            for i, (cn, sym) in enumerate(zip(class_names, symbols))
        ],
    }
    with open(out / "class_info.json", "w") as f:
        json.dump(class_info, f, indent=2)
    print(f"[train] Saved class info → {out / 'class_info.json'}")

    # ── Save class names for inference ────────────────────────────────────
    with open(out / "class_names.json", "w") as f:
        json.dump(class_names, f)
    print(f"[train] Saved class names → {out / 'class_names.json'}")

    # ── Build & compile model ──────────────────────────────────────────────
    model = build_model(num_classes)
    model.compile(
        optimizer=tf.keras.optimizers.legacy.Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.summary()

    # ── Train ──────────────────────────────────────────────────────────────
    cbs = [
        callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=PATIENCE,
            min_delta=1e-4,
            restore_best_weights=True,
            verbose=1,
        ),
        callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=3,
            min_lr=1e-6,
            verbose=1,
        ),
        callbacks.ModelCheckpoint(
            str(out / "math_model_best.h5"),
            monitor="val_accuracy",
            save_best_only=True,
            verbose=0,
        ),
    ]

    print(f"\n[train] Starting training for up to {args.epochs} epochs …\n")
    hist = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        callbacks=cbs,
        verbose=1,
    )

    # ── Save model & history ───────────────────────────────────────────────
    model_path = out / "math_model.h5"
    model.save(str(model_path))
    print(f"[train] Saved model → {model_path}")

    history_dict = {k: [float(v) for v in vs] for k, vs in hist.history.items()}
    history_dict["best_epoch"] = int(np.argmax(history_dict["val_accuracy"])) + 1
    history_dict["best_val_accuracy"] = float(max(history_dict["val_accuracy"]))
    with open(out / "training_history.json", "w") as f:
        json.dump(history_dict, f, indent=2)
    print(f"[train] Saved history → {out / 'training_history.json'}")

    # ── Confusion matrix ───────────────────────────────────────────────────
    print("[train] Computing confusion matrix on validation set …")
    y_true: list[int] = []
    y_pred: list[int] = []
    for imgs, labels in val_ds:
        preds = model.predict(imgs, verbose=0)
        y_pred.extend(np.argmax(preds, axis=1).tolist())
        y_true.extend(labels.numpy().tolist())

    plot_confusion_matrix(
        y_true, y_pred, class_names, symbols,
        str(out / "confusion_matrix.png"),
    )

    # ── Training curves ────────────────────────────────────────────────────
    plot_training_curves(history_dict, str(out / "training_curves.png"))

    # ── Summary ────────────────────────────────────────────────────────────
    val_acc = history_dict["best_val_accuracy"]
    print(f"\n{'═' * 52}")
    print(f"  Best validation accuracy : {val_acc:.4f}  ({val_acc*100:.2f} %)")
    print(f"  Best epoch               : {history_dict['best_epoch']}")
    print(f"  Classes                  : {num_classes}")
    print(f"  Total samples            : {total}")
    print(f"{'═' * 52}\n")
    print(f"  Outputs written to: {out.resolve()}")
    print(f"    math_model.h5           ← load in draw_new.py")
    print(f"    class_names.json        ← also needed by draw_new.py")
    print(f"    class_info.json         ← per-class counts for report")
    print(f"    training_history.json   ← epoch metrics for report")
    print(f"    confusion_matrix.png    ← figure for report")
    print(f"    training_curves.png     ← figure for report")


if __name__ == "__main__":
    main()
