"""
Draw & Solve  —  Handwritten Math CNN
=======================================
Loads the model and class_names.json produced by train_model.ipynb,
segments and classifies symbols drawn on a canvas, then evaluates
the resulting arithmetic expression.
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

OUTPUT_DIR   = "./outputs"   
MERGE_GAP    = 20            
MIN_BOX_AREA = 30            
CONFIDENCE   = 0.60          

FOLDER_TO_SYMBOL: dict[str, str] = {
    **{str(d): str(d) for d in range(10)},
    "add": "+",
    "sub": "-",
    "mul": "*",
    "div": "/",
}

_ARITH_CHARS = set("0123456789+-*/. ")


# ── Segmentation helpers ──────────────────────────────────────────────────────

def merge_nearby_boxes(boxes: list[tuple]) -> list[tuple]:
    """Merge horizontally adjacent bounding boxes (handles multi-stroke digits)."""
    if not boxes:
        return []
    merged = []
    x, y, w, h = boxes[0]
    for nx, ny, nw, nh in boxes[1:]:
        if nx <= x + w + MERGE_GAP:          
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


def _scale_nearest(img: np.ndarray, target_size=150) -> np.ndarray:
    """Helper to scale tiny images crisply for PowerPoint visuals."""
    h, w = img.shape[:2]
    scale = target_size / max(h, w)
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_NEAREST)


def _preprocess_roi(roi_gray: np.ndarray, target: int = 28) -> tuple[np.ndarray, dict]:
    """
    Pad, scale and centre a symbol ROI into a target×target canvas.
    Returns the canvas AND a dictionary of intermediate steps for visualization.
    """
    steps = {}
    steps["1_original_roi"] = _scale_nearest(roi_gray.copy())

    pad    = max(4, min(roi_gray.shape) // 6)
    padded = cv2.copyMakeBorder(roi_gray, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    steps["2_padded"] = _scale_nearest(padded.copy())

    scale  = (target - 4) / max(padded.shape)
    nw     = max(1, int(padded.shape[1] * scale))
    nh     = max(1, int(padded.shape[0] * scale))
    small  = cv2.resize(padded, (nw, nh), interpolation=cv2.INTER_AREA)
    steps["3_resized"] = _scale_nearest(small.copy())

    canvas = np.zeros((target, target), dtype=np.uint8)
    y0, x0 = (target - nh) // 2, (target - nw) // 2
    canvas[y0:y0 + nh, x0:x0 + nw] = small
    steps["4_centered_28x28"] = _scale_nearest(canvas.copy())

    return canvas, steps


# ── Prediction ────────────────────────────────────────────────────────────────

def segment_and_predict(
    gray: np.ndarray,
    model,
    class_names: list[str],
    img_size: int,
) -> tuple[list[str], np.ndarray, dict]:
    """
    Detect and classify every symbol.
    Returns: symbols, debug_img, pipeline_steps (for visualization)
    """
    pipeline_steps = {}
    pipeline_steps["1_grayscale"] = gray.copy()

    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    pipeline_steps["2_threshold"] = thresh.copy()

    kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=3)
    pipeline_steps["3_dilated"] = dilated.copy()

    debug_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return [], debug_img, pipeline_steps

    # 1. Get raw boxes
    boxes = [cv2.boundingRect(c) for c in contours]
    boxes = [(x, y, w, h) for x, y, w, h in boxes if w * h >= MIN_BOX_AREA]
    boxes.sort(key=lambda b: b[0])
    
    # -- NEW: Capture UNMERGED boxes for visualization --
    unmerged_viz_img = cv2.cvtColor(gray.copy(), cv2.COLOR_GRAY2BGR)
    for x, y, w, h in boxes:
        cv2.rectangle(unmerged_viz_img, (x, y), (x + w, y + h), (255, 0, 0), 2) # Blue
    pipeline_steps["4a_unmerged_boxes"] = unmerged_viz_img

    # 2. Merge boxes
    boxes = merge_nearby_boxes(boxes)

    # -- Capture MERGED boxes for visualization --
    box_viz_img = cv2.cvtColor(gray.copy(), cv2.COLOR_GRAY2BGR)
    for x, y, w, h in boxes:
        cv2.rectangle(box_viz_img, (x, y), (x + w, y + h), (0, 0, 255), 2) # Red
    pipeline_steps["4b_merged_boxes"] = box_viz_img

    results: list[str] = []
    
    for i, (x, y, w, h) in enumerate(boxes):
        roi_gray = 255 - gray[y:y + h, x:x + w]
        canvas, roi_steps = _preprocess_roi(roi_gray, target=img_size)
        
        # Save the single-symbol processing steps for the very first detected symbol
        if i == 0:
            pipeline_steps["roi_example"] = roi_steps

        img = canvas.reshape(1, img_size, img_size, 1) / 255.0

        probs      = model.predict(img, verbose=0)[0]
        confidence = float(np.max(probs))
        class_idx  = int(np.argmax(probs))

        if confidence < CONFIDENCE:
            color, label = (0, 140, 255), f"? {confidence:.0%}"
            results.append("?")
        else:
            folder_name = class_names[class_idx]
            symbol      = FOLDER_TO_SYMBOL.get(folder_name, folder_name)
            color       = (34, 139, 34) if symbol.isdigit() else (200, 60, 0)
            label       = f"{symbol}  {confidence:.0%}"
            results.append(symbol)

        cv2.rectangle(debug_img, (x, y), (x + w, y + h), color, 2)
        font, fscale, thick = cv2.FONT_HERSHEY_SIMPLEX, 0.60, 1
        (tw, th), bl = cv2.getTextSize(label, font, fscale, thick)
        tx, ty = x, y - 6 if y - 6 > th else y + h + th + 4
        cv2.rectangle(debug_img, (tx - 1, ty - th - 2), (tx + tw + 2, ty + bl), (255, 255, 255), -1)
        cv2.putText(debug_img, label, (tx, ty), font, fscale, color, thick, cv2.LINE_AA)

    return results, debug_img, pipeline_steps

# ── Expression evaluation ────────────────────────────────────────────────────

_OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv}

def safe_eval(expr: str) -> float | int:
    def _eval(node):
        if isinstance(node, ast.Constant): return node.value
        if isinstance(node, ast.BinOp): return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub): return -_eval(node.operand)
        raise ValueError("Unsupported expression node")
    return _eval(ast.parse(expr, mode="eval").body)

def evaluate_expression(symbols: list[str]) -> dict:
    equation = "".join(symbols)
    if "?" in equation:
        return {"equation": equation, "result": "⚠ Uncertain symbol(s) — please redraw", "ok": False}
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
    model_path = os.path.join(OUTPUT_DIR, "best_model.keras")
    class_names_path = os.path.join(OUTPUT_DIR, "class_names.json")

    mdl = load_model(model_path, compile=False)
    img_size: int = mdl.input_shape[1]
    with open(class_names_path, encoding="utf-8") as f:
        class_names: list[str] = json.load(f)

    return mdl, class_names, img_size


# ── Streamlit UI ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Draw & Solve", page_icon="🧮", layout="wide")
st.title("🧮 Draw & Solve")

try:
    with st.spinner("Loading model …"):
        math_model, class_names, img_size = load_math_model()
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
        symbols, debug_img, pipeline = segment_and_predict(gray, math_model, class_names, img_size)
        st.image(debug_img, caption="Final Detection")

        if symbols:
            eval_result = evaluate_expression(symbols)
            equation    = eval_result["equation"]

            with result_area.container():
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Expression**")
                    st.markdown(f"<span style='font-size:2.2rem;font-family:monospace'>{equation}</span>", unsafe_allow_html=True)
                with c2:
                    st.markdown("**Result**")
                    if eval_result["ok"]:
                        st.markdown(f"<span style='font-size:2.5rem;color:#2ecc71;font-weight:bold'>{eval_result['result']}</span>", unsafe_allow_html=True)
                    else:
                        st.error(eval_result["result"])

            # --- PRESENTATION / PIPELINE UI ---
            st.markdown("---")
            st.markdown("### Preprocessing Pipeline (For Presentation)")
            st.caption("Right-click any image and select 'Save Image As...' to use in your PowerPoint.")

            st.markdown("#### Step A: Global Image Segmentation")
            row1_col1, row1_col2, row1_col3 = st.columns(3)
            with row1_col1:
                st.image(pipeline["1_grayscale"], caption="1. Original (Grayscale)", use_container_width=True)
            with row1_col2:
                st.image(pipeline["2_threshold"], caption="2. Binary Threshold", use_container_width=True)
            with row1_col3:
                st.image(pipeline["3_dilated"], caption="3. Dilated (Bridging gaps)", use_container_width=True)

            st.markdown("#### Step B: Bounding Box Merging")
            st.caption("Crucial for multi-stroke symbols (like '÷' or split digits). We detect all contours, then merge boxes that are horizontally close.")
            box_col1, box_col2 = st.columns(2)
            with box_col1:
                st.image(pipeline["4a_unmerged_boxes"], caption="Before: Raw Contours (Blue)", use_container_width=True)
            with box_col2:
                st.image(pipeline["4b_merged_boxes"], caption="After: Merged Symbols (Red)", use_container_width=True)

            if "roi_example" in pipeline:
                st.markdown("#### Step C: Single Symbol Formatting (AI Input Preparation)")
                st.caption("Showing the extraction process for the first detected symbol. Scaled with nearest-neighbor to show the pixel grid.")
                r = pipeline["roi_example"]
                
                r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
                r2_c1.image(r["1_original_roi"], caption="1. Cropped ROI")
                r2_c2.image(r["2_padded"], caption="2. Padding Added")
                r2_c3.image(r["3_resized"], caption="3. Scaled Down")
                r2_c4.image(r["4_centered_28x28"], caption="4. Centered in 28x28")