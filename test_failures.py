"""
test_failures.py — Failure-mode test suite for Draw & Solve
============================================================
Provokes and quantifies each failure mode identified in the error analysis.

Usage
-----
# Fast tests only (no model load, ~1 s):
    pytest test_failures.py -v -s -m "not model"

# All tests including model-dependent (loads model once, ~1-2 min):
    pytest test_failures.py -v -s

# Just model tests:
    pytest test_failures.py -v -s -m model

Failure modes covered
---------------------
1. Expression grammar failures      — consecutive ops, leading/trailing ops,
                                      division by zero, uncertain symbols
2. Multi-digit join (correct path)  — verify "1","2","*","3" → "12*3" = 36
3. Proximity merging boundaries     — quantify MERGE_GAP threshold exactly
4. Under-segmentation               — close symbols merge into one box
5. Noise filtering                  — MIN_BOX_AREA removes stray pixels
6. Segmentation on synthetic canvas — full pipeline geometry check
7. Confidence distribution          — per-class below-threshold rate [model]
8. Near-identical class confusion   — 1↔sub, mul↔div, 0↔6, 9↔add [model]
9. Top-2 ambiguity                  — confused class in top-2 softmax [model]
10. Multi-digit under-segmentation  — fused digit pair misclassification [model]
11. Scale robustness                — accuracy at 25 %–400 % symbol size [model]
"""

import glob
import json
import os
import random
import sys
from collections import Counter

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from draw import (
    CONFIDENCE,
    FOLDER_TO_SYMBOL,
    MERGE_GAP,
    MIN_BOX_AREA,
    _preprocess_roi,
    evaluate_expression,
    merge_nearby_boxes,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
DATASET_DIR      = os.path.join(os.path.dirname(__file__), "dataset")
OUTPUTS_DIR      = os.path.join(os.path.dirname(__file__), "outputs")
SAMPLES_PER_CLASS = 100
SEED              = 42

# Folder names matching class_names.json ordering
CLASSES = list(FOLDER_TO_SYMBOL.keys())   # "0".."9", "add","sub","mul","div"


# ── Utilities ─────────────────────────────────────────────────────────────────

def load_class_images(cls: str, n: int = SAMPLES_PER_CLASS) -> list[np.ndarray]:
    """Load up to *n* greyscale images for dataset class *cls*."""
    paths = sorted(glob.glob(os.path.join(DATASET_DIR, cls, "*")))
    random.seed(SEED)
    paths = random.sample(paths, min(n, len(paths)))
    imgs = []
    for p in paths:
        img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            imgs.append(img)
    return imgs


def batch_classify(model, class_names: list[str], img_size: int,
                   imgs: list[np.ndarray]) -> tuple[list[str], list[float]]:
    """
    Classify a list of dataset images (dark ink on white) in one model call.
    Applies the same inversion + preprocessing as draw.py's inference path.
    """
    batch = []
    for img in imgs:
        roi_gray = 255 - img           # invert: white ink on black (matches draw.py)
        canvas   = _preprocess_roi(roi_gray, target=img_size)
        batch.append(canvas.reshape(img_size, img_size, 1) / 255.0)
    arr   = np.array(batch, dtype=np.float32)
    probs = model.predict(arr, verbose=0)
    preds = [class_names[int(np.argmax(p))] for p in probs]
    confs = [float(np.max(p)) for p in probs]
    return preds, confs


def make_canvas(height: int = 100, width: int = 400) -> np.ndarray:
    """White uint8 greyscale canvas."""
    return np.full((height, width), 255, dtype=np.uint8)


def paste_symbol(canvas: np.ndarray, img: np.ndarray,
                 x: int, y: int = 10, target_h: int = 60) -> int:
    """
    Resize *img* to *target_h* and paste it at (*x*, *y*) on *canvas*.
    Only dark pixels (ink) are written; returns the x position after the paste.
    """
    h0, w0 = img.shape[:2]
    scale  = target_h / max(h0, 1)
    nw     = max(1, int(w0 * scale))
    resized = cv2.resize(img, (nw, target_h), interpolation=cv2.INTER_AREA)
    ch, cw  = canvas.shape
    pw = min(nw, cw - x);  ph = min(target_h, ch - y)
    if pw > 0 and ph > 0:
        region = canvas[y:y + ph, x:x + pw]
        mask   = resized[:ph, :pw] < 200      # paint only ink pixels
        region[mask] = resized[:ph, :pw][mask]
    return x + nw


def count_segmented_boxes(gray: np.ndarray) -> int:
    """
    Run the same threshold → dilate → contour → area-filter → merge pipeline
    as draw.py and return the number of final bounding boxes.
    """
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    kernel    = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated   = cv2.dilate(thresh, kernel, iterations=3)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0
    boxes = [cv2.boundingRect(c) for c in contours]
    boxes = [(x, y, w, h) for x, y, w, h in boxes if w * h >= MIN_BOX_AREA]
    boxes.sort(key=lambda b: b[0])
    return len(merge_nearby_boxes(boxes))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def model_bundle():
    """Load the Keras model exactly once for the whole test session."""
    from tensorflow.keras.models import load_model as kload
    mdl = kload(os.path.join(OUTPUTS_DIR, "best_model.keras"), compile=False)
    img_size = mdl.input_shape[1]
    with open(os.path.join(OUTPUTS_DIR, "class_names.json")) as f:
        class_names = json.load(f)
    return mdl, class_names, img_size


# ══════════════════════════════════════════════════════════════════════════════
# 1 ── Expression grammar failures  (no model)
# ══════════════════════════════════════════════════════════════════════════════

class TestExpressionGrammar:
    """Failures at the expression-evaluation stage — no model required."""

    # ── happy paths ───────────────────────────────────────────────────────────

    def test_simple_arithmetic(self):
        r = evaluate_expression(["3", "+", "4"])
        assert r["ok"] and r["result"] == "7"

    @pytest.mark.parametrize("symbols,expected", [
        (["1", "2", "*", "3"], "36"),    # 12 × 3
        (["9", "9", "+", "1"], "100"),   # 99 + 1
        (["1", "0", "/", "2"], "5"),     # 10 ÷ 2
        (["1", "2", "3", "+", "0"], "123"),
    ])
    def test_multidigit_join_evaluates_correctly(self, symbols, expected):
        """
        Adjacent digit symbols concatenate into a multi-digit number —
        this is correct behaviour, not a bug.
        """
        r = evaluate_expression(symbols)
        assert r["ok"], f"Unexpected failure: {r['result']}"
        assert r["result"] == expected

    # ── failure modes ─────────────────────────────────────────────────────────

    @pytest.mark.parametrize("symbols", [
        ["3", "+", "+", "4"],
        ["3", "*", "/", "4"],
        ["+", "-"],
    ])
    def test_consecutive_operators_fail(self, symbols):
        assert not evaluate_expression(symbols)["ok"], \
            f"Consecutive operators should fail: {symbols}"

    def test_leading_unary_minus_is_valid(self):
        """
        '-7' parses as unary negation — ast.USub is whitelisted in safe_eval.
        This is intentional; it is NOT a failure mode.
        """
        r = evaluate_expression(["-", "7"])
        assert r["ok"] and r["result"] == "-7"

    @pytest.mark.parametrize("symbols", [
        ["+", "3"], ["*", "2"],    # '+' and '*' have no unary form
    ])
    def test_leading_operator_fails(self, symbols):
        assert not evaluate_expression(symbols)["ok"], \
            f"Leading operator should fail: {symbols}"

    @pytest.mark.parametrize("symbols", [
        ["3", "+"], ["8", "*"],
    ])
    def test_trailing_operator_fails(self, symbols):
        assert not evaluate_expression(symbols)["ok"], \
            f"Trailing operator should fail: {symbols}"

    def test_division_by_zero_caught(self):
        r = evaluate_expression(["8", "/", "0"])
        assert not r["ok"]
        assert "zero" in r["result"].lower()

    def test_uncertain_symbol_blocks_eval(self):
        r = evaluate_expression(["3", "?", "4"])
        assert not r["ok"]
        assert "Uncertain" in r["result"]

    def test_all_uncertain(self):
        assert not evaluate_expression(["?", "?"])["ok"]

    def test_empty_expression(self):
        r = evaluate_expression([])
        assert not r["ok"] or r["result"] == ""

    def test_grammar_failure_rate(self, capsys):
        """
        Quantify: what fraction of random symbol sequences are syntactically valid?
        Models the distribution of errors coming from garbled segmentation output.
        """
        vocab   = list("0123456789") + ["+", "-", "*", "/", "?"]
        weights = [1.0] * 10 + [0.5, 0.5, 0.5, 0.5, 0.2]
        random.seed(SEED)

        total = 500
        ok_count    = 0
        fail_reasons: Counter = Counter()

        for _ in range(total):
            length = random.randint(1, 6)
            seq    = random.choices(vocab, weights=weights, k=length)
            r      = evaluate_expression(seq)
            if r["ok"]:
                ok_count += 1
            else:
                res = r["result"]
                if "Uncertain" in res:
                    fail_reasons["uncertain_symbol"] += 1
                elif "zero" in res.lower():
                    fail_reasons["division_by_zero"] += 1
                else:
                    fail_reasons["syntax_error"] += 1

        fail_count = total - ok_count
        print(f"\n{'─'*52}")
        print(f"[Grammar] {total} random sequences")
        print(f"  ok:   {ok_count:4d} ({ok_count/total:5.1%})")
        print(f"  fail: {fail_count:4d} ({fail_count/total:5.1%})")
        for reason, count in fail_reasons.most_common():
            print(f"    {reason}: {count}")
        print(f"{'─'*52}")
        assert ok_count > 0, "sanity: at least some sequences must be valid"


# ══════════════════════════════════════════════════════════════════════════════
# 2 ── Proximity merging / segmentation geometry  (no model)
# ══════════════════════════════════════════════════════════════════════════════

class TestProximityMerging:
    """
    Tests for merge_nearby_boxes — covers both over- and under-segmentation.
    MERGE_GAP = 20 px is the key constant.
    """

    @pytest.mark.parametrize("gap,should_merge", [
        (0,  True),   # touching strokes → must merge
        (5,  True),
        (10, True),
        (19, True),   # 1 px below threshold
        (20, True),   # exactly at threshold (≤ condition)
        (21, False),  # 1 px above → split! (over-segmentation failure)
        (40, False),
    ])
    def test_two_stroke_merge_boundary(self, gap: int, should_merge: bool):
        """
        Two strokes of the SAME symbol: they should merge when gap ≤ MERGE_GAP.
        A gap of 21 px already causes over-segmentation.
        """
        # box1 right edge = 30; box2 left edge = 30 + gap
        boxes  = [(10, 10, 20, 40), (30 + gap, 10, 20, 40)]
        result = merge_nearby_boxes(boxes)
        assert len(result) == (1 if should_merge else 2), (
            f"gap={gap}px: expected {'merge' if should_merge else 'split'}, "
            f"got {len(result)} box(es)"
        )

    @pytest.mark.parametrize("gap", [0, 5, 10, 15, 20])
    def test_close_symbols_silently_merge(self, gap: int):
        """
        Two DIFFERENT symbols with gap ≤ MERGE_GAP are silently fused —
        this is under-segmentation that the system cannot detect.
        """
        boxes  = [(10, 10, 30, 50), (40 + gap, 10, 30, 50)]
        result = merge_nearby_boxes(boxes)
        # gap ≤ 20 → merge (bad: should be two boxes but isn't)
        assert len(result) == 1, \
            f"gap={gap}px: symbols should have merged (under-segmentation confirmed)"

    @pytest.mark.parametrize("gap", [21, 30, 50])
    def test_well_separated_symbols_stay_separate(self, gap: int):
        boxes  = [(10, 10, 30, 50), (40 + gap, 10, 30, 50)]
        result = merge_nearby_boxes(boxes)
        assert len(result) == 2, \
            f"gap={gap}px: separate symbols should not merge"

    def test_single_box_unchanged(self):
        boxes  = [(10, 10, 30, 50)]
        result = merge_nearby_boxes(boxes)
        assert result == boxes

    def test_empty_input(self):
        assert merge_nearby_boxes([]) == []

    def test_merge_gap_value(self):
        """Document the current MERGE_GAP setting."""
        assert MERGE_GAP == 20, \
            f"MERGE_GAP changed to {MERGE_GAP} — update tests accordingly"


class TestNoiseFiltering:
    """MIN_BOX_AREA filter removes stray pixel blobs before classification."""

    @pytest.mark.parametrize("w,h,should_keep", [
        (1,  1,  False),   # 1 px²
        (5,  4,  False),   # 20 px² — below threshold
        (5,  5,  False),   # 25 px² — below threshold
        (5,  6,  True),    # 30 px² — exactly at threshold
        (10, 10, True),    # 100 px² — normal
        (20, 40, True),    # 800 px² — normal digit
    ])
    def test_area_threshold(self, w: int, h: int, should_keep: bool):
        boxes    = [(0, 0, w, h)]
        filtered = [(x, y, bw, bh) for x, y, bw, bh in boxes
                    if bw * bh >= MIN_BOX_AREA]
        assert (len(filtered) == 1) == should_keep, \
            f"w={w} h={h} area={w*h}: expected kept={should_keep}"

    def test_min_area_value(self):
        assert MIN_BOX_AREA == 30, \
            f"MIN_BOX_AREA changed to {MIN_BOX_AREA} — update tests accordingly"


class TestSegmentationSynthetic:
    """Run the full draw.py segmentation pipeline on synthetic canvas images."""

    def test_empty_canvas_zero_boxes(self):
        assert count_segmented_boxes(make_canvas()) == 0

    def test_solid_rectangle_one_box(self):
        canvas = make_canvas(80, 200)
        cv2.rectangle(canvas, (20, 10), (70, 70), 0, -1)
        assert count_segmented_boxes(canvas) == 1

    def test_single_pixel_survives_dilation(self):
        """
        After 3 iterations of 3×3 dilation a single-pixel noise mark grows to
        ~7×7 = 49 px² — above MIN_BOX_AREA=30.  The area filter is therefore
        ineffective for post-dilation contours: this is a known limitation.
        """
        canvas         = make_canvas(80, 200)
        canvas[40, 40] = 0          # single ink pixel
        # dilation expands it to ~49 px² → survives the area filter
        assert count_segmented_boxes(canvas) == 1, (
            "Single pixel IS kept after dilation — "
            "MIN_BOX_AREA only catches contours that remain tiny post-dilation."
        )

    @pytest.mark.parametrize("gap", [0, 5, 10, 15, 20, 25, 30, 40])
    def test_two_bar_gap_sweep(self, gap: int):
        """
        Two ink bars with varying horizontal gap — quantifies how dilation
        affects the effective merge boundary in the full pipeline.

        Dilation (3×3, 3 iter) expands each bar by ~3 px per side, so the
        effective gap ≈ gap − 6.  Boxes then merge when effective_gap ≤ 20.
        Expected split point: gap > 26 px.
        """
        canvas = make_canvas(80, 200)
        # bar 1: x=20..32; bar 2: x=32+gap..44+gap
        cv2.rectangle(canvas, (20, 10), (32, 70), 0, -1)
        x2 = 32 + gap
        cv2.rectangle(canvas, (x2, 10), (x2 + 12, 70), 0, -1)
        count = count_segmented_boxes(canvas)
        print(f"\n  gap={gap:3d}px → {count} box(es) "
              f"(effective≈{gap - 6:+d}px after dilation)")
        assert count in (1, 2), f"Unexpected box count {count} at gap={gap}"


# ══════════════════════════════════════════════════════════════════════════════
# 3 ── Model-dependent tests
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.model
class TestConfidenceDistribution:
    """
    For each class: what fraction of real dataset images falls below
    the CONFIDENCE threshold and would be flagged as '?'?
    """

    def test_per_class_below_threshold(self, model_bundle):
        mdl, class_names, img_size = model_bundle

        print(f"\n{'─'*58}")
        print(f"[Confidence] threshold = {CONFIDENCE:.2f}  "
              f"(n = {SAMPLES_PER_CLASS} per class)")
        print(f"  {'class':>6}  {'n':>4}  {'below_thr':>9}  "
              f"{'mean_conf':>9}  {'min_conf':>8}")
        print(f"  {'─'*6}  {'─'*4}  {'─'*9}  {'─'*9}  {'─'*8}")

        overall_below = 0
        overall_total = 0

        for cls in CLASSES:
            imgs = load_class_images(cls)
            if not imgs:
                continue
            preds, confs = batch_classify(mdl, class_names, img_size, imgs)
            below = sum(1 for c in confs if c < CONFIDENCE)
            overall_below += below
            overall_total += len(imgs)
            print(f"  {cls:>6}  {len(imgs):>4}  "
                  f"{below:>4} ({below/len(imgs):>5.1%})  "
                  f"{np.mean(confs):>8.3f}  "
                  f"{np.min(confs):>7.3f}")

        rate = overall_below / overall_total if overall_total else 0
        print(f"\n  Overall: {overall_below}/{overall_total} below threshold "
              f"({rate:.2%})")
        print(f"{'─'*58}")

        assert rate < 0.10, \
            f"Too many images flagged uncertain: {rate:.1%} (threshold 10 %)"


@pytest.mark.model
class TestNearIdenticalConfusion:
    """
    Quantify direct misclassification and top-2 ambiguity between the
    visually similar class pairs identified in the error analysis.
    """

    PAIRS = [
        ("1",   "sub"),   # vertical bar ≈ horizontal dash
        ("mul", "div"),   # crossing lines look similar
        ("9",   "add"),   # loop + stem ≈ cross
        ("0",   "6"),     # closed loop vs open loop
    ]

    @pytest.mark.parametrize("true_cls,confused_cls", PAIRS)
    def test_direct_confusion_rate(self, true_cls, confused_cls, model_bundle):
        mdl, class_names, img_size = model_bundle
        imgs  = load_class_images(true_cls)
        preds, _ = batch_classify(mdl, class_names, img_size, imgs)
        errors   = sum(1 for p in preds if p == confused_cls)
        rate     = errors / len(imgs) if imgs else 0
        print(f"\n  {true_cls!r:>6} → misclassified as {confused_cls!r}: "
              f"{errors}/{len(imgs)} ({rate:.1%})")
        assert rate < 0.05, \
            f"High confusion {true_cls!r}→{confused_cls!r}: {rate:.1%} (threshold 5 %)"

    @pytest.mark.parametrize("true_cls,confused_cls", PAIRS)
    def test_top2_ambiguity_rate(self, true_cls, confused_cls, model_bundle):
        """
        How often does the confused class appear in the top-2 softmax outputs,
        even without winning?  This signals near-miss confusion.
        """
        mdl, class_names, img_size = model_bundle
        imgs = load_class_images(true_cls)
        if confused_cls not in class_names:
            pytest.skip(f"{confused_cls!r} not in class_names")

        confused_idx = class_names.index(confused_cls)
        in_top2 = 0

        # Predict in batch but need raw probs for top-2
        batch = []
        for img in imgs:
            roi   = _preprocess_roi(255 - img, target=img_size)
            batch.append(roi.reshape(img_size, img_size, 1) / 255.0)
        probs_all = mdl.predict(np.array(batch, dtype=np.float32), verbose=0)

        for probs in probs_all:
            top2 = np.argsort(probs)[-2:]
            if confused_idx in top2:
                in_top2 += 1

        rate = in_top2 / len(imgs) if imgs else 0
        print(f"\n  {true_cls!r:>6} has {confused_cls!r} in top-2: "
              f"{in_top2}/{len(imgs)} ({rate:.1%})")
        # Top-2 presence rate is informational — soft bound only
        assert len(imgs) > 0


@pytest.mark.model
class TestMultiDigitUnderSegmentation:
    """
    Quantify the failure when two digit images are placed close enough
    to be fused by proximity-merging.  The CNN never saw multi-digit
    glyphs during training, so it cannot classify them correctly.
    """

    TARGET_H = 50   # px — height of each pasted symbol

    def _compose_pair(self, img1: np.ndarray, img2: np.ndarray,
                      gap: int) -> np.ndarray:
        """Paste img1 and img2 side by side with horizontal *gap*."""
        h, w1 = img1.shape
        _, w2  = img2.shape
        scale  = self.TARGET_H / max(h, 1)
        nw1    = max(1, int(w1 * scale))
        nw2    = max(1, int(w2 * scale))
        r1     = cv2.resize(img1, (nw1, self.TARGET_H))
        r2     = cv2.resize(img2, (nw2, self.TARGET_H))
        canvas = make_canvas(self.TARGET_H + 20, 10 + nw1 + gap + nw2 + 10)
        paste_symbol(canvas, r1, 10,       y=10, target_h=self.TARGET_H)
        paste_symbol(canvas, r2, 10+nw1+gap, y=10, target_h=self.TARGET_H)
        return canvas

    @pytest.mark.parametrize("gap", [0, 5, 10, 15])
    def test_fused_pair_misclassification_rate(self, gap: int, model_bundle):
        """
        Place '1' and '2' images with gap ≤ MERGE_GAP.  Count how often the
        merged box is NOT classified as '1' or '2' (i.e., totally wrong).
        """
        mdl, class_names, img_size = model_bundle
        ones = load_class_images("1", 30)
        twos = load_class_images("2", 30)
        n    = min(len(ones), len(twos))

        fused_count   = 0
        wrong_count   = 0
        total_pairs   = 0
        class_counter: Counter = Counter()

        for img1, img2 in zip(ones[:n], twos[:n]):
            canvas  = self._compose_pair(img1, img2, gap)
            n_boxes = count_segmented_boxes(canvas)
            total_pairs += 1

            if n_boxes == 1:
                fused_count += 1
                # Crop the merged ink region and classify it
                _, thresh = cv2.threshold(canvas, 127, 255,
                                          cv2.THRESH_BINARY_INV)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                                               cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    pts = np.vstack(contours)
                    bx, by, bw, bh = cv2.boundingRect(pts)
                    roi    = canvas[by:by+bh, bx:bx+bw]
                    preds, _ = batch_classify(mdl, class_names, img_size, [roi])
                    pred   = preds[0]
                    class_counter[pred] += 1
                    if pred not in ("1", "2"):
                        wrong_count += 1

        fuse_rate  = fused_count / total_pairs if total_pairs else 0
        wrong_rate = wrong_count / fused_count if fused_count else 0

        print(f"\n  gap={gap:2d}px | pairs={total_pairs} | "
              f"fused={fused_count} ({fuse_rate:.0%}) | "
              f"of fused → wrong={wrong_count} ({wrong_rate:.0%})")
        if fused_count:
            top5 = class_counter.most_common(5)
            print(f"    predicted as: "
                  + ", ".join(f"{cls!r}:{cnt}" for cls, cnt in top5))

        # All pairs with gap ≤ MERGE_GAP should fuse (after dilation)
        if gap <= MERGE_GAP - 6:   # approximate dilation margin
            assert fuse_rate > 0.5, \
                f"gap={gap}: expected most pairs to fuse, got {fuse_rate:.0%}"

    def test_well_separated_pair_correct(self, model_bundle):
        """
        Control: with gap >> MERGE_GAP, both symbols are separate and classified correctly.
        """
        mdl, class_names, img_size = model_bundle
        gap   = MERGE_GAP + 30     # well above threshold + dilation margin
        ones  = load_class_images("1", 30)
        twos  = load_class_images("2", 30)
        n     = min(len(ones), len(twos))

        both_correct = 0
        total        = 0

        for img1, img2 in zip(ones[:n], twos[:n]):
            canvas  = self._compose_pair(img1, img2, gap)
            n_boxes = count_segmented_boxes(canvas)
            if n_boxes != 2:
                continue   # segmentation itself failed — skip pair

            # Extract each box individually
            _, thresh = cv2.threshold(canvas, 127, 255, cv2.THRESH_BINARY_INV)
            kernel    = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            dilated   = cv2.dilate(thresh, kernel, iterations=3)
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
            boxes = sorted([cv2.boundingRect(c) for c in contours
                            if cv2.boundingRect(c)[2] * cv2.boundingRect(c)[3]
                            >= MIN_BOX_AREA],
                           key=lambda b: b[0])
            boxes = merge_nearby_boxes(boxes)
            if len(boxes) != 2:
                continue

            rois  = [canvas[b[1]:b[1]+b[3], b[0]:b[0]+b[2]] for b in boxes]
            preds, _ = batch_classify(mdl, class_names, img_size, rois)
            total += 1
            if preds[0] == "1" and preds[1] == "2":
                both_correct += 1

        acc = both_correct / total if total else 0
        print(f"\n  gap={gap}px (control): {both_correct}/{total} "
              f"pairs both correct ({acc:.0%})")
        assert acc > 0.70, \
            f"Well-separated symbols should classify correctly: {acc:.0%}"


@pytest.mark.model
class TestScaleRobustness:
    """
    Quantify classification accuracy when symbols are drawn at extreme sizes.
    The preprocessing (pad → scale → centre in 28×28) should normalise this,
    but very small symbols lose detail at 28×28 resolution.
    """

    SCALES = [0.25, 0.5, 1.0, 2.0, 4.0]

    @pytest.mark.parametrize("scale", SCALES)
    def test_accuracy_at_scale(self, scale: float, model_bundle):
        mdl, class_names, img_size = model_bundle

        correct = 0
        total   = 0
        per_cls: dict[str, tuple[int, int]] = {}

        for cls in CLASSES:
            imgs = load_class_images(cls, 20)
            scaled_imgs = []
            for img in imgs:
                h, w = img.shape
                nh   = max(1, int(h * scale))
                nw   = max(1, int(w * scale))
                scaled_imgs.append(
                    cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
                )
            preds, _ = batch_classify(mdl, class_names, img_size, scaled_imgs)
            cls_correct = sum(1 for p in preds if p == cls)
            correct     += cls_correct
            total       += len(imgs)
            per_cls[cls] = (cls_correct, len(imgs))

        acc = correct / total if total else 0
        print(f"\n  scale={scale:5.2f}×  overall accuracy: "
              f"{correct}/{total} ({acc:.1%})")
        for cls, (c, t) in per_cls.items():
            marker = " ←" if c / t < 0.80 else ""
            print(f"    {cls:>6}: {c}/{t} ({c/t:.0%}){marker}")

        if scale == 1.0:
            assert acc > 0.90, f"Normal scale should be > 90 %: {acc:.1%}"
        elif scale in (0.5, 2.0):
            assert acc > 0.70, f"Moderate scale {scale}× should be > 70 %: {acc:.1%}"
        else:
            # 0.25× and 4× are extreme — warn but don't hard-fail
            if acc < 0.50:
                pytest.warns(None)   # just surface the number
            print(f"  ⚠  extreme scale {scale}×: {acc:.1%} — informational only")


# ══════════════════════════════════════════════════════════════════════════════
# 4 ── Summary (printed at session end by pytest -s)
# ══════════════════════════════════════════════════════════════════════════════

def pytest_sessionfinish(session, exitstatus):
    print("\n\n" + "═" * 58)
    print("FAILURE-MODE TEST SUMMARY")
    print("═" * 58)
    print("Run with -v -s to see per-class quantification tables.")
    print("Tests marked @pytest.mark.model require the Keras model.")
    print("═" * 58)
