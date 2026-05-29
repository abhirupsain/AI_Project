"""
Draw & Solve  —  Handwritten Math CNN
=======================================
Loads the model and class_names.json produced by train_model.ipynb,
segments and classifies symbols drawn on a canvas, then evaluates
the resulting arithmetic expression.

Required files (produced by training notebook)
------------------------------------------------
  outputs/best_model.keras
  outputs/class_names.json

Install:
    pip install streamlit numpy opencv-python-headless tensorflow \
                streamlit-drawable-canvas

Run:
    streamlit run draw_new.py
"""

import ast
import json
import operator as op
import os

import cv2
import numpy as np
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from tensorflow.keras.models import load_model


# ── Constants ────────────────────────────────────────────────────────────────

OUTPUT_DIR   = "./outputs"   # must match train_model.ipynb OUTPUT_DIR
MERGE_GAP    = 20            # max horizontal px gap to merge multi-stroke symbols
MIN_BOX_AREA = 30            # blobs smaller than this (px²) are discarded as noise
CONFIDENCE   = 0.60          # predictions below this are flagged as uncertain

# Maps dataset folder names (= model class names) to display / expression chars.
# Only the 4 operators used during training are included; digits map to themselves.
FOLDER_TO_SYMBOL: dict[str, str] = {
    **{str(d): str(d) for d in range(10)},
    "add": "+",
    "sub": "-",
    "mul": "*",
    "div": "/",
}

# Characters valid in a safe arithmetic expression
_ARITH_CHARS = set("0123456789+-*/. ")


# ── Segmentation helpers ──────────────────────────────────────────────────────

def merge_nearby_boxes(boxes: list[tuple]) -> list[tuple]:
    """Merge horizontally adjacent bounding boxes (handles multi-stroke digits)."""
    if not boxes:
        return []
    merged = []
    x, y, w, h = boxes[0]
    for nx, ny, nw, nh in boxes[1:]:
        if nx <= x + w + MERGE_GAP:          # overlapping or close enough
            x2 = max(x + w, nx + nw)
            y  = min(y, ny)
            x  = min(x, nx)
            w  = x2 - x
            h  = max(y + h, ny + nh) - y
        else:
            merged.append((x, y, w, h))
            x, y, w, h = nx, ny, nw, nh
    merged.append((x, y, w, h))
    return merged


def _preprocess_roi(roi_gray: np.ndarray, target: int = 28) -> np.ndarray:
    """
    Pad, scale and centre a symbol ROI into a target×target canvas.
    Produces dark ink on black background, matching training convention.
    """
    pad    = max(4, min(roi_gray.shape) // 6)
    padded = cv2.copyMakeBorder(roi_gray, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    scale  = (target - 4) / max(padded.shape)
    nw     = max(1, int(padded.shape[1] * scale))
    nh     = max(1, int(padded.shape[0] * scale))
    small  = cv2.resize(padded, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((target, target), dtype=np.uint8)
    y0, x0 = (target - nh) // 2, (target - nw) // 2
    canvas[y0:y0 + nh, x0:x0 + nw] = small
    return canvas


# ── Prediction ────────────────────────────────────────────────────────────────

def segment_and_predict(
    gray: np.ndarray,
    model,
    class_names: list[str],
    img_size: int,
) -> tuple[list[str], np.ndarray]:
    """
    Detect and classify every symbol in *gray* (H×W uint8, white background).

    Returns
    -------
    symbols   : list of predicted symbol strings (e.g. ["3", "+", "4"])
    debug_img : BGR image with colour-coded bounding boxes and confidence labels
    """
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    debug_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=3)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return [], debug_img

    boxes = [cv2.boundingRect(c) for c in contours]
    boxes = [(x, y, w, h) for x, y, w, h in boxes if w * h >= MIN_BOX_AREA]
    boxes.sort(key=lambda b: b[0])
    boxes = merge_nearby_boxes(boxes)

    results: list[str] = []
    for x, y, w, h in boxes:
        # Use the original gray ROI (dark ink on white) — invert for model input
        roi_gray = 255 - gray[y:y + h, x:x + w]
        canvas   = _preprocess_roi(roi_gray, target=img_size)
        img      = canvas.reshape(1, img_size, img_size, 1) / 255.0

        probs      = model.predict(img, verbose=0)[0]
        confidence = float(np.max(probs))
        class_idx  = int(np.argmax(probs))

        if confidence < CONFIDENCE:
            color  = (0, 140, 255)   # orange — uncertain
            label  = f"? {confidence:.0%}"
            results.append("?")
        else:
            folder_name = class_names[class_idx]
            symbol      = FOLDER_TO_SYMBOL.get(folder_name, folder_name)
            color  = (34, 139, 34) if symbol.isdigit() else (200, 60, 0)
            label  = f"{symbol}  {confidence:.0%}"
            results.append(symbol)

        # Draw bounding box
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), color, 2)

        # Draw label pill — always readable regardless of background
        font, fscale, thick = cv2.FONT_HERSHEY_SIMPLEX, 0.60, 1
        (tw, th), bl = cv2.getTextSize(label, font, fscale, thick)
        tx = x
        ty = y - 6 if y - 6 > th else y + h + th + 4
        cv2.rectangle(debug_img, (tx - 1, ty - th - 2), (tx + tw + 2, ty + bl), (255, 255, 255), -1)
        cv2.putText(debug_img, label, (tx, ty), font, fscale, color, thick, cv2.LINE_AA)

    return results, debug_img


# ── Expression evaluation ────────────────────────────────────────────────────

_OPS = {
    ast.Add:  op.add,
    ast.Sub:  op.sub,
    ast.Mult: op.mul,
    ast.Div:  op.truediv,
}


def safe_eval(expr: str) -> float | int:
    """Evaluate a pure-arithmetic expression string safely (no exec/eval)."""
    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -_eval(node.operand)
        raise ValueError("Unsupported expression node")
    return _eval(ast.parse(expr, mode="eval").body)


def evaluate_expression(symbols: list[str]) -> dict:
    equation = "".join(symbols)

    if "?" in equation:
        return {"equation": equation,
                "result": "⚠ Uncertain symbol(s) — please redraw", "ok": False}

    if not all(c in _ARITH_CHARS for c in equation):
        return {"equation": equation, "result": "Unsupported characters", "ok": False}

    try:
        value   = safe_eval(equation)
        display = int(value) if isinstance(value, float) and value.is_integer() else value
        return {"equation": equation, "result": str(display), "ok": True}
    except ZeroDivisionError:
        return {"equation": equation, "result": "Division by zero!", "ok": False}
    except Exception as exc:
        return {"equation": equation, "result": f"Error: {exc}", "ok": False}


# ── Model loading ─────────────────────────────────────────────────────────────

@st.cache_resource
def load_math_model():
    model_path       = os.path.join(OUTPUT_DIR, "best_model.keras")
    class_names_path = os.path.join(OUTPUT_DIR, "class_names.json")

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model not found at '{model_path}'.\n"
            "Run train_model.ipynb first to produce outputs/best_model.keras."
        )
    if not os.path.exists(class_names_path):
        raise FileNotFoundError(
            f"class_names.json not found at '{class_names_path}'.\n"
            "Run train_model.ipynb first."
        )

    mdl = load_model(model_path, compile=False)
    img_size: int = mdl.input_shape[1]
    with open(class_names_path, encoding="utf-8") as f:
        class_names: list[str] = json.load(f)

    return mdl, class_names, img_size


# ── Streamlit UI ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Draw & Solve", page_icon="🧮", layout="wide")
st.title("🧮 Draw & Solve")
st.caption(
    "Draw a maths expression — digits **0–9** and operators **+ − × ÷** "
    "— the expression is recognised and solved in real time."
)

with st.expander("ℹ️ Tips for best results"):
    st.markdown(
        "- Leave **clear gaps** between each symbol.\n"
        "- `+` — draw a full cross; strokes roughly equal length.\n"
        "- `−` — draw a **wide** horizontal line (wider than it is tall).\n"
        "- `×` — two diagonal strokes crossing in the middle.\n"
        "- `÷` — horizontal bar with a dot above and a dot below.\n"
        "- If a digit like `4` or `5` is split, try increasing stroke width.\n"
    )

try:
    with st.spinner("Loading model …"):
        math_model, class_names, img_size = load_math_model()
    symbols_list = [FOLDER_TO_SYMBOL.get(cn, cn) for cn in class_names]
    st.sidebar.markdown(
        f"**Model:** `outputs/best_model.keras`  \n"
        f"**Classes ({len(class_names)}):** {' '.join(symbols_list)}"
    )
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

canvas_result = st_canvas(
    fill_color="rgba(0,0,0,0)",
    stroke_width=14,
    stroke_color="#000000",
    background_color="#ffffff",
    height=400,
    width=1800,
    drawing_mode="freedraw",
    key="canvas",
)

st.markdown("---")
result_area = st.empty()

if canvas_result.image_data is not None:
    raw  = canvas_result.image_data
    gray = cv2.cvtColor(raw.astype("uint8"), cv2.COLOR_RGBA2GRAY)

    if gray.min() < 200:   # something has been drawn
        symbols, debug_img = segment_and_predict(gray, math_model, class_names, img_size)
        st.image(
            debug_img,
            caption="Detected symbols  (green = digit · teal = operator · orange = uncertain)",
        )

        if symbols:
            eval_result = evaluate_expression(symbols)
            equation    = eval_result["equation"]

            with result_area.container():
                # Per-symbol coloured chips
                st.markdown("**Detected symbols**")
                chip_html = ""
                for s in symbols:
                    if s == "?":
                        bg, fg = "#ff9800", "#fff"
                    elif s.isdigit():
                        bg, fg = "#2e7d32", "#fff"
                    else:
                        bg, fg = "#1565c0", "#fff"
                    chip_html += (
                        f"<span style='background:{bg};color:{fg};"
                        f"padding:4px 10px;margin:2px;border-radius:6px;"
                        f"font-size:1.3rem;font-family:monospace;"
                        f"display:inline-block'>{s}</span>"
                    )
                st.markdown(chip_html, unsafe_allow_html=True)
                st.markdown("")

                c1, c2 = st.columns(2)

                with c1:
                    st.markdown("**Expression**")
                    st.markdown(
                        f"<span style='font-size:2.2rem;font-family:monospace'>"
                        f"{equation}</span>",
                        unsafe_allow_html=True,
                    )

                with c2:
                    st.markdown("**Result**")
                    if eval_result["ok"]:
                        st.markdown(
                            f"<span style='font-size:2.5rem;color:#2ecc71;"
                            f"font-weight:bold'>{eval_result['result']}</span>",
                            unsafe_allow_html=True,
                        )
                    elif "?" in equation:
                        st.warning("Some symbols unclear — try drawing them larger or with a thicker stroke.")
                    else:
                        st.error(eval_result["result"])