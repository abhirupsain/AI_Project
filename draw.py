"""
Draw Equation Solver  —  CNN edition
=====================================
• Digits    → small CNN trained on full MNIST  (~99 % accuracy, fast inference)
• Operators → geometry classifier (aspect ratio, cross score, corner ink, diagonals)
• Segments  → proximity merging so multi-stroke digits (4, 5, 7 …) stay together
 
Install:
    pip install streamlit numpy opencv-python-headless tensorflow \
                streamlit-drawable-canvas
Run:
    streamlit run equation_solver.py
"""
import os
import cv2
import numpy as np
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from tensorflow.keras.models import load_model
import ast
import operator as op


# ══════════════════════════════════════════════════════════════════════
#  PROXIMITY MERGING
#  Merge bounding boxes whose horizontal gap ≤ MERGE_GAP px so that
#  multi-stroke digits (4, 5, 7 …) aren't split into separate symbols.
# ══════════════════════════════════════════════════════════════════════
 
MERGE_GAP = 18


# safe operators
OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
}

def safe_eval(expr):
    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            return OPS[type(node.op)](_eval(node.left), _eval(node.right))
        else:
            raise ValueError("Invalid expression")

    return _eval(ast.parse(expr, mode='eval').body)

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

def _cross_score(roi: np.ndarray) -> tuple[float, float]:
    """Ratio of centre-strip ink density to whole-image ink density."""
    h, w = roi.shape
    total = roi.sum()
    if total == 0:
        return 0.0, 0.0
    bw = max(2, min(h, w) // 6)
    cy, cx = h // 2, w // 2
    h_strip = roi[max(0, cy - bw): cy + bw + 1, :]
    v_strip = roi[:, max(0, cx - bw): cx + bw + 1]
    mean_d  = total / (h * w)
    hd = h_strip.sum() / (h_strip.shape[0] * w + 1e-9)
    vd = v_strip.sum() / (h * v_strip.shape[1] + 1e-9)
    return hd / (mean_d + 1e-9), vd / (mean_d + 1e-9)


def _corner_ink_ratio(roi: np.ndarray) -> float:
    """
    Fraction of total ink that sits in the four corner quadrants.
    LOW  → corners are empty  → likely a  +  (arms, no diagonals)
    HIGH → corners have ink   → likely a  ×  (diagonal strokes)
    """
    h, w = roi.shape
    total = roi.sum()
    if total == 0:
        return 0.0
    qh, qw = max(1, h // 4), max(1, w // 4)
    corner_ink = (
        roi[:qh,    :qw   ].sum() +
        roi[:qh,    w-qw: ].sum() +
        roi[h-qh:,  :qw   ].sum() +
        roi[h-qh:,  w-qw: ].sum()
    )
    return corner_ink / (total + 1e-9)


def _diagonal_score(roi: np.ndarray) -> float:
    """Fraction of ink near either main diagonal."""
    h, w = roi.shape
    total = roi.sum()
    if total == 0:
        return 0.0
    tol = max(2, min(h, w) // 7)
    mask = np.zeros_like(roi, dtype=bool)
    for i in range(h):
        c1 = int(round(i * w / h))
        c2 = int(round((h - 1 - i) * w / h))
        for c in [c1, c2]:
            lo, hi = max(0, c - tol), min(w, c + tol + 1)
            mask[i, lo:hi] = True
    return roi[mask].sum() / (total + 1e-9)


def _has_gap_structure(roi: np.ndarray) -> bool:
    """Three distinct horizontal ink bands → divide sign (dot/bar/dot)."""
    proj = roi.sum(axis=1)
    binary = (proj > proj.max() * 0.1).astype(int)
    return int(np.diff(binary).clip(0).sum()) >= 3


def classify_operator(roi: np.ndarray, w: int, h: int) -> str | None:
    aspect = w / max(h, 1)

    if aspect > 2.8:
        return "-"

    if 0.5 < aspect < 2.0:
        h_score, v_score = _cross_score(roi)
        corner           = _corner_ink_ratio(roi)
        diag             = _diagonal_score(roi)
        if h_score > 1.3 and v_score > 1.3 and corner < 0.12:
            return "+"

        if diag > 0.55 and corner > 0.12:
            return "*"

    if _has_gap_structure(roi):
        return "/"

    return None


# ══════════════════════════════════════════════════════════════════════
#  PREPROCESSING
# ══════════════════════════════════════════════════════════════════════

def _center_in_28(roi_bin: np.ndarray) -> np.ndarray:
    h, w = roi_bin.shape
    scale = 20.0 / max(h, w)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    small = cv2.resize(roi_bin, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((28, 28), dtype=np.uint8)
    y0, x0 = (28 - nh) // 2, (28 - nw) // 2
    canvas[y0:y0+nh, x0:x0+nw] = small
    return canvas


# ══════════════════════════════════════════════════════════════════════
#  SEGMENTATION + PREDICTION
# ══════════════════════════════════════════════════════════════════════

def segment_and_predict(gray: np.ndarray, digit_model):
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    debug_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return [], debug_img

    boxes = [cv2.boundingRect(c) for c in contours]
    boxes = [(x, y, w, h) for x, y, w, h in boxes if w*h > 120]
    boxes.sort(key=lambda b: b[0])

    boxes = merge_nearby_boxes(boxes)

    results = []
    for x, y, w, h in boxes:
        roi = thresh[y:y+h, x:x+w]
        op = classify_operator(roi, w, h)

        if op is not None:
            cv2.rectangle(debug_img, (x,y), (x+w,y+h), (255,0,0), 2)
            results.append(op)
            continue
        else:
            cv2.rectangle(debug_img, (x,y), (x+w,y+h), (0,255,0), 2)

        canvas = _center_in_28(roi)
        img = canvas.reshape(1, 28, 28, 1) / 255.0
        pred = digit_model.predict(img, verbose=0)[0]
        confidence = np.max(pred)
        digit = np.argmax(pred)

        if confidence < 0.6:
            results.append("?")
        else:
            results.append(str(digit))

    return results, debug_img


# ══════════════════════════════════════════════════════════════════════
#  STREAMLIT UI
# ══════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="Draw & Solve", page_icon="🧮", layout="wide")
st.title("🧮 Draw & Solve")
st.caption("Draw a maths expression — digits **0–9** and operators **+ − × ÷** "
           "— then click **Solve**.")

with st.expander("ℹ️ Tips for best results"):
    st.markdown(
        "- Leave **clear gaps** between each symbol.\n"
        "- `+` → draw a full cross; keep the strokes roughly equal length.\n"
        "- `−` → draw a **wide** horizontal line (wider than it is tall).\n"
        "- `×` → two diagonal strokes crossing in the middle.\n"
        "- `÷` → horizontal bar with a dot above and a dot below.\n"
        "- If a digit like `4` or `5` is split, try increasing stroke width."
    )

@st.cache_resource
def load_digit_model():
    path = os.path.join(os.path.dirname(__file__), "model.keras")
    return load_model(path)

try:
    with st.spinner("Loading model..."):
        digit_model = load_digit_model()
except Exception:
    st.error("Model not found. Please train and save model first.")
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
        symbols, debug_img = segment_and_predict(gray, digit_model)
        st.image(debug_img)

        if symbols:
            equation = "".join(symbols)
            if "?" in equation:
                st.warning("Uncertain digits detected. Please redraw clearly.")
                st.stop()
            with result_area.container():
                c1, c2 = st.columns(2)

                with c1:
                    st.markdown("**Detected expression**")
                    st.markdown(
                        f"<span style='font-size:2.2rem;font-family:monospace'>"
                        f"{equation}</span>",
                        unsafe_allow_html=True,
                    )

                with c2:
                    st.markdown("**Result**")
                    allowed = set("0123456789+-*/ ")
                    try:
                        if all(c in allowed for c in equation):
                            result = safe_eval(equation)   
                            display = (int(result)
                                       if isinstance(result, float)
                                       and result.is_integer()
                                       else result)
                            st.markdown(
                                f"<span style='font-size:2.5rem;color:#2ecc71;"
                                f"font-weight:bold'>{display}</span>",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.warning("Unexpected characters in expression.")
                    except ZeroDivisionError:
                        st.error("Division by zero!")
                    except Exception:
                        st.markdown(
                            "<span style='font-size:2rem;color:#aaa'>…</span>",
                            unsafe_allow_html=True,
                        )