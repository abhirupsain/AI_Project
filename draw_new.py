"""
Draw & Solve  —  Unified Math-Symbol CNN
=========================================
• Single CNN trained on the sagyamthapa Handwritten Math Symbols dataset
  (19 classes: digits 0–9, operators + − × ÷ . =, variables x y z)
• All symbols — digits AND operators — are classified by the same model.
• Frontend (canvas, layout, evaluation) is unchanged from the previous version.

Required files (same directory as this script, produced by train.py)
---------------------------------------------------------------------
  math_model.keras   —  trained Keras model
  class_names.json   —  ordered list of class folder names

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


# ══════════════════════════════════════════════════════════════════════════════
#  PROXIMITY MERGING
#  Merge bounding boxes whose horizontal gap ≤ MERGE_GAP px so that
#  multi-stroke digits (4, 5, 7 …) aren't split into separate symbols.
# ══════════════════════════════════════════════════════════════════════════════

MERGE_GAP    = 18   # px — max horizontal gap to merge multi-stroke symbols
MIN_BOX_AREA = 80   # px² — smaller blobs are discarded as noise
CONFIDENCE   = 0.60 # minimum prediction confidence; below → "?"

# Maps dataset folder names (= model class names) → display / expression char.
# Covers the two common naming conventions used by the Kaggle dataset.
FOLDER_TO_SYMBOL: dict[str, str] = {
    **{str(d): str(d) for d in range(10)},
    "add": "+", "plus":   "+", "+": "+",
    "sub": "-", "minus":  "-", "-": "-",
    "mul": "*", "times":  "*", "mult": "*", "×": "*",
    "div": "/", "divide": "/",              "÷": "/",
    "dec": ".", "dot":    ".",              ".": ".",
    "eq":  "=", "equals": "=",             "=": "=",
    "x": "x",  "y": "y",  "z": "z",
}

# Characters valid in a pure arithmetic expression (for safe_eval)
_ARITH_CHARS = set("0123456789+-*/. ")


def merge_nearby_boxes(boxes: list[tuple]) -> list[tuple]:
    if not boxes:
        return []
    merged = []
    x, y, w, h = boxes[0]
    for nx, ny, nw, nh in boxes[1:]:
        # Next box starts within MERGE_GAP of current box's right edge?
        if nx <= x + w + MERGE_GAP:
            new_x2 = max(x + w, nx + nw)
            new_y2 = max(y + h, ny + nh)
            y = min(y, ny)
            x = min(x, nx)
            w = new_x2 - x
            h = new_y2 - y
        else:
            merged.append((x, y, w, h))
            x, y, w, h = nx, ny, nw, nh
    merged.append((x, y, w, h))
    return merged


# ══════════════════════════════════════════════════════════════════════════════
#  PREPROCESSING
#  Add a small border (mimicking the training images' whitespace), then
#  scale and centre in a target×target canvas — same idea as the original
#  _center_in_28, now generalised to any target size read from the model.
# ══════════════════════════════════════════════════════════════════════════════

def _preprocess_roi(roi_gray: np.ndarray, target: int = 28) -> np.ndarray:
    """
    Resize a greyscale ROI (dark ink on white background) to target×target,
    centred on a white canvas with a small border — matching the style of the
    sagyamthapa training images so that background≈1.0 and ink≈0.0 after /255.
    """
    pad    = max(4, min(roi_gray.shape) // 6)
    padded = cv2.copyMakeBorder(roi_gray, pad, pad, pad, pad,
                                cv2.BORDER_CONSTANT, value=255)   # white border
    scale = (target - 2) / max(padded.shape)
    nw    = max(1, int(padded.shape[1] * scale))
    nh    = max(1, int(padded.shape[0] * scale))
    small  = cv2.resize(padded, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.full((target, target), 255, dtype=np.uint8)        # white canvas
    y0, x0 = (target - nh) // 2, (target - nw) // 2
    canvas[y0:y0 + nh, x0:x0 + nw] = small
    return canvas


# ══════════════════════════════════════════════════════════════════════════════
#  SEGMENTATION + PREDICTION
# ══════════════════════════════════════════════════════════════════════════════

def segment_and_predict(
    gray: np.ndarray,
    model,
    class_names: list[str],
    img_size: int,
) -> tuple[list[str], np.ndarray]:
    """
    Detect symbols in *gray* (H×W uint8, white background) and classify each
    one with the unified *model*.

    Returns
    -------
    symbols   : list of predicted symbol strings (e.g. ["3", "+", "4"])
    debug_img : BGR image with colour-coded bounding boxes
    """
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    debug_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return [], debug_img

    boxes = [cv2.boundingRect(c) for c in contours]
    boxes = [(x, y, w, h) for x, y, w, h in boxes if w * h >= MIN_BOX_AREA]
    boxes.sort(key=lambda b: b[0])
    boxes = merge_nearby_boxes(boxes)

    results: list[str] = []
    for x, y, w, h in boxes:
        # ── Use ORIGINAL gray ROI (dark ink on white bg) so the model sees
        #    the same pixel distribution it was trained on.
        #    thresh is only used above for contour / dilation.
        roi_gray = gray[y:y + h, x:x + w]
        canvas   = _preprocess_roi(roi_gray, target=img_size)
        img      = canvas.reshape(1, img_size, img_size, 1) / 255.0

        probs      = model.predict(img, verbose=0)[0]
        confidence = float(np.max(probs))
        class_idx  = int(np.argmax(probs))

        if confidence < CONFIDENCE:
            color = (0, 140, 255)   # orange — uncertain
            label = f"? {confidence:.0%}"
            results.append("?")
        else:
            folder_name = class_names[class_idx]
            symbol      = FOLDER_TO_SYMBOL.get(folder_name, folder_name)
            color = (34, 139, 34) if symbol.isdigit() else (200, 60, 0)
            label = f"{symbol}  {confidence:.0%}"
            results.append(symbol)

        # Draw bounding box
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), color, 2)

        # Draw label with a white background pill so it's always readable
        font, fscale, thick = cv2.FONT_HERSHEY_SIMPLEX, 0.60, 1
        (tw, th), bl = cv2.getTextSize(label, font, fscale, thick)
        tx = x
        ty = y - 6 if y - 6 > th else y + h + th + 4   # above box, or below if no room
        cv2.rectangle(debug_img, (tx - 1, ty - th - 2), (tx + tw + 2, ty + bl), (255, 255, 255), -1)
        cv2.putText(debug_img, label, (tx, ty), font, fscale, color, thick, cv2.LINE_AA)

    return results, debug_img


# ══════════════════════════════════════════════════════════════════════════════
#  EXPRESSION EVALUATION
# ══════════════════════════════════════════════════════════════════════════════

_OPS = {
    ast.Add:  op.add,
    ast.Sub:  op.sub,
    ast.Mult: op.mul,
    ast.Div:  op.truediv,
}


def safe_eval(expr: str) -> float | int:
    """Evaluate a pure-arithmetic expression string (no variables, no =)."""
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
    """
    Turn the predicted symbol list into a displayable result.

    Returns a dict:
      equation  str  — the joined expression
      result    str  — numeric answer, equality check, or error message
      ok        bool — True when evaluation produced a clean numeric result
    """
    equation = "".join(symbols)

    if "?" in equation:
        return {"equation": equation,
                "result": "⚠ Uncertain symbol(s) — please redraw", "ok": False}

    has_variable = any(s in equation for s in "xyz")
    has_equals   = "=" in equation

    if has_variable:
        return {"equation": equation,
                "result": "(contains variables — display only)", "ok": False}

    if has_equals:
        parts = equation.split("=", 1)
        lhs, rhs = parts[0].strip(), parts[1].strip()
        if not lhs or not rhs:
            return {"equation": equation, "result": "Incomplete equation", "ok": False}
        if not all(c in _ARITH_CHARS for c in lhs + rhs):
            return {"equation": equation, "result": "Unsupported characters", "ok": False}
        try:
            lv, rv = safe_eval(lhs), safe_eval(rhs)
            lv_d = int(lv) if isinstance(lv, float) and lv.is_integer() else round(lv, 6)
            rv_d = int(rv) if isinstance(rv, float) and rv.is_integer() else round(rv, 6)
            check = "✓  True" if abs(lv - rv) < 1e-9 else "✗  False"
            return {"equation": equation,
                    "result": f"{lv_d} = {rv_d}   →   {check}", "ok": True}
        except Exception as e:
            return {"equation": equation, "result": f"Error: {e}", "ok": False}

    if not all(c in _ARITH_CHARS for c in equation):
        return {"equation": equation, "result": "Unsupported characters", "ok": False}

    try:
        value   = safe_eval(equation)
        display = int(value) if isinstance(value, float) and value.is_integer() else value
        return {"equation": equation, "result": str(display), "ok": True}
    except ZeroDivisionError:
        return {"equation": equation, "result": "Division by zero!", "ok": False}
    except Exception as e:
        return {"equation": equation, "result": f"Error: {e}", "ok": False}


# ══════════════════════════════════════════════════════════════════════════════
#  MODEL LOADING
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def load_math_model():
    base             = os.path.dirname(__file__)
    model_path       = os.path.join(base, "math_model.h5")
    class_names_path = os.path.join(base, "class_names.json")

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model not found at '{model_path}'. "
            "Run  python train.py  first to produce math_model.keras "
            "and class_names.json."
        )
    if not os.path.exists(class_names_path):
        raise FileNotFoundError(
            f"class_names.json not found at '{class_names_path}'. "
            "Make sure train.py wrote it to the same directory."
        )

    mdl = load_model(model_path, compile=False)  # inference only — no optimizer needed
    img_size: int = mdl.input_shape[1]          # e.g. 28
    with open(class_names_path) as f:
        class_names: list[str] = json.load(f)

    return mdl, class_names, img_size


# ══════════════════════════════════════════════════════════════════════════════
#  STREAMLIT UI
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="Draw & Solve", page_icon="🧮", layout="wide")
st.title("🧮 Draw & Solve")
st.caption(
    "Draw a maths expression — digits **0–9** and operators **+ − × ÷** "
    "— then the expression is recognised and solved in real time."
)

with st.expander("ℹ️ Tips for best results"):
    st.markdown(
        "- Leave **clear gaps** between each symbol.\n"
        "- `+` → draw a full cross; keep the strokes roughly equal length.\n"
        "- `−` → draw a **wide** horizontal line (wider than it is tall).\n"
        "- `×` → two diagonal strokes crossing in the middle.\n"
        "- `÷` → horizontal bar with a dot above and a dot below.\n"
        "- `=` → two horizontal bars, one above the other.\n"
        "- `.` → a small round dot (decimal point).\n"
        "- If a digit like `4` or `5` is split, try increasing stroke width.\n"
        "- Expressions with `=` show a truth check (e.g. `3+4=7 → True`).\n"
        "- Expressions with variables `x y z` are displayed but not evaluated."
    )

try:
    with st.spinner("Loading model..."):
        math_model, class_names, img_size = load_math_model()
    symbols_list = [FOLDER_TO_SYMBOL.get(cn, cn) for cn in class_names]
    st.sidebar.markdown(
        f"**Model:** `math_model.h5`  \n"
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

    if gray.min() < 200:
        symbols, debug_img = segment_and_predict(
            gray, math_model, class_names, img_size
        )
        st.image(debug_img, caption="Detected Symbols (green = digit · blue = operator · orange = uncertain)")

        if symbols:
            eval_result = evaluate_expression(symbols)
            equation    = eval_result["equation"]

            with result_area.container():
                # ── Per-symbol chip row ──────────────────────────────────────
                st.markdown("**Detected symbols**")
                chip_html = ""
                for s in symbols:
                    if s == "?":
                        bg, fg = "#ff9800", "#fff"
                    elif s.isdigit() or s == ".":
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

                # ── Expression + result ──────────────────────────────────────
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
                        st.warning("Some symbols unclear — try drawing them larger or with thicker strokes.")
                    elif "variable" in eval_result["result"]:
                        st.info(eval_result["result"])
                    else:
                        st.error(eval_result["result"])
