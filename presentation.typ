// ─────────────────────────────────────────────────────────────────────────────
//  Draw & Solve — 20-minute Presentation
// ─────────────────────────────────────────────────────────────────────────────

// polylux 0.3.1 incompatible with Typst ≥ 0.12 — simple wrapper suffices.
#let polylux-slide(body) = { body; pagebreak(weak: true) }

// ── Palette ──────────────────────────────────────────────────────────────────
#let navy   = rgb("#1a237e")
#let blue   = rgb("#1565c0")
#let sky    = rgb("#42a5f5")
#let green  = rgb("#2e7d32")
#let orange = rgb("#e65100")
#let grey   = rgb("#546e7a")
#let light  = rgb("#f5f7fa")
#let white  = rgb("#ffffff")
#let black  = rgb("#212121")
#let purple = rgb("#6a1b9a")
#let teal   = rgb("#00695c")

// ── Page ─────────────────────────────────────────────────────────────────────
#set page(paper: "presentation-16-9", margin: 0pt)
#set text(size: 18pt, fill: black)
#set strong(delta: 200)

// ── Helpers ───────────────────────────────────────────────────────────────────

#let slide-frame(header-color: navy, title: [], body) = {
  polylux-slide[
    #grid(rows: (52pt, 1fr),
      rect(width: 100%, height: 100%, fill: header-color,
           inset: (x: 28pt, y: 0pt))[
        #align(left + horizon)[
          #text(fill: white, size: 22pt, weight: "bold")[#title]
        ]
      ],
      rect(width: 100%, height: 100%, fill: white,
           inset: (x: 32pt, y: 18pt))[#body],
    )
  ]
}

#let section-slide(color: navy, label: [], title: [], subtitle: []) = {
  polylux-slide[
    #rect(width: 100%, height: 100%, fill: color)[
      #place(left + bottom, dx: 36pt, dy: -36pt)[
        #text(fill: sky, size: 12pt, weight: "bold")[#label]
        #v(4pt)
        #text(fill: white, size: 34pt, weight: "bold")[#title]
        #v(2pt)
        #text(fill: rgb("#cfd8dc"), size: 17pt)[#subtitle]
      ]
    ]
  ]
}

#let info(body) = rect(
  fill: light, stroke: none, radius: 5pt,
  inset: (x: 12pt, y: 8pt), width: 100%,
)[#body]

#let callout(color: blue, body) = rect(
  fill: color.lighten(88%),
  stroke: (left: (paint: color, thickness: 4pt)),
  radius: 4pt, inset: (x: 12pt, y: 8pt), width: 100%,
)[#body]

#let step(color: navy, n: "1", label: [], desc: []) = {
  rect(fill: color.lighten(92%), stroke: none, radius: 6pt,
       inset: (x: 8pt, y: 12pt))[
    #align(center)[
      #circle(fill: color, radius: 11pt)[
        #align(center + horizon)[
          #text(fill: white, weight: "bold", size: 12pt)[#n]
        ]
      ]
      #v(5pt)
      #text(weight: "bold", size: 14pt)[#label] \
      #text(size: 12pt, fill: grey)[#desc]
    ]
  ]
}

#let pill(color: navy, label: []) = rect(
  fill: color, radius: 4pt,
  inset: (x: 9pt, y: 4pt),
)[#text(fill: white, size: 15pt, weight: "bold")[#label]]


// ══════════════════════════════════════════════════════════════════════════════
//  SLIDE 1 — TITLE
// ══════════════════════════════════════════════════════════════════════════════

#polylux-slide[
  #rect(width: 100%, height: 100%, fill: navy)[
    #place(center + horizon)[
      #text(fill: sky, size: 15pt, weight: "bold")[AI PROJECT · SPRING 2026]
      #v(14pt)
      #text(fill: white, size: 48pt, weight: "bold")[Draw & Solve]
      #v(8pt)
      #text(fill: rgb("#cfd8dc"), size: 24pt)[Handwritten Math Expression Recognition]
      #v(36pt)
      #grid(columns: (1fr,) * 3, gutter: 12pt,
        align(center)[#text(fill: sky,  size: 12pt)[*Matti H. V. Lehmann*]   \ #text(fill: white, size: 11pt)[Introduction · Conclusion]],
        align(center)[#text(fill: sky,  size: 12pt)[*David A. Spickenheuer*] \ #text(fill: white, size: 11pt)[System Pipeline]],
        align(center)[#text(fill: sky,  size: 12pt)[*Jonas Schenke*]         \ #text(fill: white, size: 11pt)[Image Processing]],
      )
      #v(8pt)
      #grid(columns: (1fr,) * 3, gutter: 12pt,
        align(center)[#text(fill: sky,  size: 12pt)[*Philip Nguyen*]   \ #text(fill: white, size: 11pt)[Dataset & Data Prep]],
        align(center)[#text(fill: sky,  size: 12pt)[*Staniya Thomas*]  \ #text(fill: white, size: 11pt)[CNN & Evaluation]],
        align(center)[#text(fill: sky,  size: 12pt)[*Abhirup Sain*]    \ #text(fill: white, size: 11pt)[Live Demo]],
      )
    ]
  ]
]


// ══════════════════════════════════════════════════════════════════════════════
//  SLIDE 2 — TEAM & TASK DIVISION
// ══════════════════════════════════════════════════════════════════════════════

#slide-frame(title: "Team & Task Division")[
  #table(
    columns: (1fr, auto, 1fr),
    fill: (_, row) => if row == 0 { navy }
                      else if calc.odd(row) { light } else { white },
    stroke: none, inset: (x: 14pt, y: 11pt),
    table.cell(fill: navy)[#text(fill: white, weight: "bold")[Name]],
    table.cell(fill: navy)[#text(fill: white, weight: "bold")[Student ID]],
    table.cell(fill: navy)[#text(fill: white, weight: "bold")[Task]],

    [Matti Hannes Vincent Lehmann], [T14H06309], [Introduction · Conclusion],
    [David Axel Spickenheuer],      [T14H06329], [System Pipeline],
    [Jonas Schenke],                [T14H06307], [Image Processing & Segmentation],
    [Philip Nguyen],                [91499153X], [Dataset & Data Preparation],
    [Staniya Thomas],               [T14H06310], [CNN Architecture & Evaluation],
    [Abhirup Sain],                 [T14H06318], [Live Demo],
  )
]


// ══════════════════════════════════════════════════════════════════════════════
//  MATTI — Intro  (~3 min)
// ══════════════════════════════════════════════════════════════════════════════

#slide-frame(title: "The Problem")[
  #grid(columns: (1fr, 1fr), gutter: 24pt,
    [
      - Handwriting varies widely per writer
      - Operators share features with digits (× vs x, − vs ÷)
      - Multi-stroke digits confuse naive segmenters

      #v(18pt)
      #callout(color: orange)[
        *Goal:* Draw a math expression on screen → get the result instantly.
      ]
    ],
    align(center + horizon)[
      #rect(fill: light, stroke: grey.lighten(40%),
            width: 100%, height: 220pt, radius: 6pt)[
        #align(center + horizon)[
          #text(size: 52pt, fill: grey.lighten(20%))[3 + 4]
          #v(4pt)
          #text(size: 12pt, fill: grey)[Canvas drawing example]
        ]
      ]
    ],
  )
]

#slide-frame(title: "Our Solution: Draw & Solve")[
  #grid(columns: (1fr, 1fr), gutter: 24pt,
    [
      + Draw an expression on a browser canvas
      + OpenCV segments individual symbols
      + CNN classifies each symbol (14 classes)
      + Safe AST evaluator computes the result

      #v(16pt)
      #grid(columns: (1fr, 1fr), gutter: 8pt,
        info[*Digits* \ 0 · 1 · 2 · 3 · 4 · 5 · 6 · 7 · 8 · 9],
        info[*Operators* \ + · − · × · ÷],
      )
    ],
    align(center + horizon)[
      #rect(fill: light, stroke: grey.lighten(40%),
            width: 100%, height: 230pt, radius: 6pt)[
        #align(center + horizon)[
          #text(size: 13pt, fill: grey)[_App screenshot_]
        ]
      ]
    ],
  )
]

#slide-frame(title: "v1 → v2: What Changed")[
  #table(
    columns: (auto, 1fr, 1fr),
    fill: (_, row) => if row == 0 { navy }
                      else if calc.odd(row) { light } else { white },
    stroke: none, inset: (x: 14pt, y: 11pt),
    table.cell(fill: navy)[#text(fill: white, weight: "bold")[Aspect]],
    table.cell(fill: navy)[#text(fill: white, weight: "bold")[v1]],
    table.cell(fill: navy)[#text(fill: white, weight: "bold")[v2]],

    [Classifier],  [MNIST CNN + geometry heuristics], [*Unified 14-class CNN*],
    [Dataset],     [MNIST only],                      [Sagyamthapa (Kaggle)],
    [Accuracy],    [~99% digits · operators fragile], [*99.44%* all 14 classes],
  )
  #v(16pt)
  #callout(color: green)[
    *One model for everything* — no hand-crafted rules for operators, just learned features.
  ]
]


// ══════════════════════════════════════════════════════════════════════════════
//  DAVID — System Pipeline  (~2 min)
// ══════════════════════════════════════════════════════════════════════════════

#slide-frame(header-color: blue, title: "System Pipeline")[
  #grid(
    columns: (1fr, auto, 1fr, auto, 1fr, auto, 1fr, auto, 1fr),
    gutter: 0pt, column-gutter: 6pt,
    rows: (120pt,), align: center + horizon,

    step(color: blue, n: "1", label: [Canvas],   desc: [Draw with mouse/touch]),
    text(size: 22pt, fill: blue)[→],
    step(color: blue, n: "2", label: [Segment],  desc: [OpenCV bounding boxes]),
    text(size: 22pt, fill: blue)[→],
    step(color: blue, n: "3", label: [Classify], desc: [CNN → softmax(14)]),
    text(size: 22pt, fill: blue)[→],
    step(color: blue, n: "4", label: [Assemble], desc: [Sort x → string]),
    text(size: 22pt, fill: blue)[→],
    step(color: blue, n: "5", label: [Evaluate], desc: [AST safe-eval]),
  )

  #v(12pt)
  // Example data flow for "3 + 4 = 7"
  #align(center)[
    #text(size: 11pt, fill: grey, style: "italic")[Example — user draws "3 + 4":] \
    #v(6pt)
    #grid(columns: (auto, auto, auto, auto, auto, auto, auto, auto, auto),
          gutter: 0pt, column-gutter: 6pt, align: center + horizon,
      rect(fill: light, radius: 3pt, inset: (x: 9pt, y: 5pt))[#text(size: 12pt)[✏ "3 + 4" on canvas]],
      text(size: 14pt, fill: blue)[→],
      rect(fill: blue.lighten(85%), radius: 3pt, inset: (x: 9pt, y: 5pt))[#text(size: 12pt)[3 bounding boxes]],
      text(size: 14pt, fill: blue)[→],
      rect(fill: purple.lighten(85%), radius: 3pt, inset: (x: 9pt, y: 5pt))[#text(size: 12pt)["3" · "+" · "4"]],
      text(size: 14pt, fill: blue)[→],
      rect(fill: green.lighten(85%), radius: 3pt, inset: (x: 9pt, y: 5pt))[#text(size: 12pt)[`"3+4"`]],
      text(size: 14pt, fill: blue)[→],
      rect(fill: navy, radius: 3pt, inset: (x: 9pt, y: 5pt))[#text(size: 12pt, fill: white, weight: "bold")[= 7]],
    )
  ]
]

#slide-frame(header-color: blue, title: "Software Architecture")[
  #image("outputs/software_architecture.png", width: 100%)
]

#slide-frame(header-color: blue, title: "Preprocessing & Inference")[
  #grid(columns: (1fr, 1fr), gutter: 24pt,
    [
      *Per-symbol preprocessing*
      - Crop bounding box from greyscale image
      - Add white padding, scale to fit 26 × 26
      - Centre on 28 × 28 white canvas
      - Divide ÷ 255 → ink ≈ 0, background ≈ 1

      #v(10pt)
      *Inference & assembly*
      - CNN softmax → 14 class probabilities
      - Confidence < 0.60 → label as `?`
      - Sort symbols by x → expression string
      - AST evaluator: only +, −, ×, ÷ permitted (no `eval()`)
    ],
    align(center + horizon)[
      #rect(fill: light, stroke: grey.lighten(40%),
            width: 100%, height: 220pt, radius: 6pt)[
        #align(center + horizon)[
          #text(size: 12pt, fill: grey)[_Raw → ROI → 28 × 28 model input_]
        ]
      ]
    ],
  )
]


// ══════════════════════════════════════════════════════════════════════════════
//  JONAS — Segmentation  (~2 min)
// ══════════════════════════════════════════════════════════════════════════════

#slide-frame(header-color: green, title: "Thresholding & Contour Detection")[
  #grid(columns: (1fr, 1fr), gutter: 24pt,
    [
      *Binarisation*
      - Canvas: white (255), ink ≈ 0
      - `THRESH_BINARY_INV`: ink → 255, bg → 0
      - 3 × 3 dilation closes gaps between strokes
      - `findContours` detects white regions on black

      #v(10pt)
      *Bounding boxes*
      - Outermost contours only (`RETR_EXTERNAL`)
      - Box area < 30 px² discarded (noise filter)
      - Sort all boxes left → right by x-coordinate
    ],
    align(center + horizon)[
      #rect(fill: light, stroke: grey.lighten(40%),
            width: 100%, height: 230pt, radius: 6pt)[
        #align(center + horizon)[
          #text(size: 12pt, fill: grey)[_Gray → threshold → dilated → boxes_]
        ]
      ]
    ],
  )
]

#slide-frame(header-color: green, title: "Proximity Merging")[
  #grid(columns: (1fr, 1fr), gutter: 24pt,
    [
      *Problem:* digits 4, 5, 7 are multi-stroke → each stroke gets its own box

      *Solution:* merge horizontally adjacent boxes with gap ≤ *20 px*
      - Iterate boxes left → right
      - If next box starts within 20 px, expand current box
      - Otherwise, emit current box and start a new one

      #v(12pt)
      #callout(color: green)[
        Also handles the two dots in ÷ after dilation merges them with the bar.
      ]
    ],
    align(center + horizon)[
      #rect(fill: light, stroke: grey.lighten(40%),
            width: 100%, height: 230pt, radius: 6pt)[
        #align(center + horizon)[
          #text(size: 12pt, fill: grey)[_Before / after proximity merge_]
        ]
      ]
    ],
  )
]


// ══════════════════════════════════════════════════════════════════════════════
//  PHILIP — Dataset  (~3 min)
// ══════════════════════════════════════════════════════════════════════════════

#slide-frame(header-color: orange, title: "Dataset & Train/Test Split")[
  #grid(columns: (1fr, 1fr), gutter: 24pt,
    [
      #table(
        columns: (1fr, auto),
        fill: (_, row) => if row == 0 { orange.lighten(20%) }
                          else if calc.odd(row) { light } else { white },
        stroke: none, inset: (x: 9pt, y: 7pt),
        [*Source*],              [*Detail*],
        [Digits 0–9],            [MNIST (LeCun et al.)],
        [Operators +−×÷],        [Sagyamthapa (Kaggle)],
        [Classes used],          [*14* (digits + operators)],
        [Balanced per class],    [*1 048 samples*],
        [Total training pool],   [14 672 images],
        [Train / Val],           [85 % / 15 % of pool],
        [Test set (held-out)],   [*10 490 images*],
        [— MNIST test],          [10 000 images],
        [— Kaggle ops (20 %)],   [490 images (seed = 42)],
      )
    ],
    [
      #image("outputs/class_distribution.png", width: 100%)
    ],
  )
]

#slide-frame(header-color: orange, title: "Class Balancing & Augmentation")[
  #grid(columns: (1fr, 1fr), gutter: 24pt,
    [
      *Imbalance problem*
      - Digits: 5 000 – 6 700 samples each
      - Operators: ~1 048 samples each → *6:1 ratio*
      - Without fix: model predicts digits almost always

      #v(10pt)
      *Fix:* downsample digits to 1 048 per class

      #v(10pt)
      #callout(color: orange)[
        Result: *perfectly balanced* — 1 048 × 14 = 14 672 images
      ]
    ],
    [
      *Augmentation* (training only, fill = black)

      #table(
        columns: (1fr, auto),
        fill: (_, row) => if row == 0 { orange.lighten(20%) }
                          else if calc.odd(row) { light } else { white },
        stroke: none, inset: (x: 10pt, y: 8pt),
        [*Transform*], [*Range*],
        [Rotation],    [± 8°],
        [Zoom],        [± 10%],
        [Translation], [± 8% x/y],
      )

      #v(10pt)
      - Simulates real writing variation
      - Fill = *0 (black)* — matches MNIST convention
      - Key to generalizing from only 1 048 samples
    ],
  )
]


// ══════════════════════════════════════════════════════════════════════════════
//  STANIYA — CNN + Evaluation  (~5 min)
// ══════════════════════════════════════════════════════════════════════════════

#slide-frame(header-color: purple, title: "CNN Architecture — Overview")[
  #image("outputs/nn_architecture.png", width: 100%)
]

#slide-frame(header-color: purple, title: "CNN Architecture — Details")[
  #grid(columns: (1fr, 1fr), gutter: 20pt,
    [
      *Input:* 28 × 28 × 1 greyscale

      #table(
        columns: (1fr, auto, auto),
        fill: (_, row) => if row == 0 { purple.lighten(20%) }
                          else if calc.odd(row) { light } else { white },
        stroke: none, inset: (x: 8pt, y: 7pt),
        [*Block*], [*Output shape*], [*Params*],
        [Conv32×2 + BN, MaxPool, Drop 0.25], [(14,14,32)], [9.9K],
        [Conv64×2 + BN, MaxPool, Drop 0.25], [(7, 7, 64)], [55.7K],
        [Conv128 + BN, GlobalAvgPool, Drop 0.25], [(128)], [74.4K],
        [Dense 256 + BN, Drop 0.5],       [(256)],         [34.1K],
        [Dense 14, softmax],              [(14)],           [3.6K],
        table.cell(colspan: 2)[*Total*],  [*~178K*],
      )
    ],
    [
      *Design choices*

      - BatchNorm after every conv → stable training
      - Dropout 0.25 (conv) / 0.5 (dense) → regularization
      - Filters double per block: 32 → 64 → 128
      - *GlobalAveragePooling2D* in block 3 — 128 features instead of 1152 → less overfitting
      - AdamW (lr = 0.001, weight decay = 1e-4)
      - Early stopping: patience = 5

      #v(8pt)
      #callout(color: purple)[
        ~178K params — trains in *< 3 min*.
      ]
    ],
  )
]

#slide-frame(header-color: purple, title: "Training Results")[
  #grid(columns: (1fr, 1fr), gutter: 20pt,
    [
      #image("outputs/training_curves.png", width: 100%)
    ],
    [
      #table(
        columns: (1fr, auto),
        fill: (_, row) => if row == 0 { purple.lighten(20%) }
                          else if calc.odd(row) { light } else { white },
        stroke: none, inset: (x: 10pt, y: 9pt),
        [*Metric*], [*Value*],
        [Total epochs],  [13 (early stop patience = 5)],
        [Best epoch],    [8],
        [Best val acc],  [*99.46%*],
        [Train/val gap], [< 0.5%],
      )

      #v(12pt)
      - Val acc reaches *98%* after just 1 epoch
      - AdamW weight decay prevents overfitting
      - No overfitting despite only 14 672 training samples
    ],
  )
]

#slide-frame(header-color: purple, title: "Confusion Matrix")[
  #grid(columns: (1fr, 1fr), gutter: 20pt,
    [
      #image("outputs/confusion_matrix.png", width: 100%)
    ],
    [
      #callout(color: green)[
        *Overall:  99.44%* (10 490 test images) \
        Digits:    99.49 % \
        Operators: 98.78 %
      ]

      #v(10pt)
      The matrix is nearly diagonal — 59 misclassified out of 10 490.

      #v(10pt)
      #image("outputs/operator_confusion_matrix.png", width: 100%)
    ],
  )
]

#slide-frame(header-color: purple, title: "Per-Class Accuracy")[
  #image("outputs/per_class_accuracy.png", width: 100%)
]

#slide-frame(header-color: purple, title: "Failure Cases — All 59 Misclassified Symbols")[
  #image("outputs/misclassified_samples.png", width: 100%)
  #v(4pt)
  #align(center)[
    #text(size: 12pt, fill: grey)[Each cell: true label → predicted label, with confidence score]
  ]
]

#slide-frame(header-color: purple, title: "Error Analysis")[
  #grid(columns: (1fr, 1fr), gutter: 24pt,
    [
      *Top confusion pairs* (test set, 59 total errors)

      #table(
        columns: (auto, auto, auto, 1fr),
        fill: (_, row) => if row == 0 { purple.lighten(20%) }
                          else if calc.odd(row) { light } else { white },
        stroke: none, inset: (x: 8pt, y: 7pt),
        [*True*], [*Predicted*], [*Count*], [*Why?*],
        [`4`], [`9`], [5], [Open loop vs. closed],
        [`5`], [`3`], [5], [Similar curvature],
        [`9`], [`4`], [4], [Open loop vs. stem],
        [`7`], [`2`], [4], [Diagonal bar confusion],
        [`×`], [`7`], [3], [Cross ≈ slanted stroke],
      )
    ],
    [
      *Key observations*

      - *×* is the weakest class: 94.8% accuracy (6 errors in 116)
      - *−* and *÷*: 100% accuracy on the test set
      - Most errors are *digit-to-digit*, not cross-type
      - Worst pairs are visually near-identical shapes

      #v(10pt)
      #callout(color: orange)[
        With only 1 048 operator samples, × is most sensitive to style variation — being confused as a slanted 7.
      ]
    ],
  )
]


// ══════════════════════════════════════════════════════════════════════════════
//  ABHIRUP — Demo  (~2 min)
// ══════════════════════════════════════════════════════════════════════════════

#slide-frame(header-color: teal, title: "Demo")[
  #grid(columns: (1fr, 1fr), gutter: 24pt,
    [
      + Draw `3 + 4` → verify result *7*
      + Draw `12 × 3` → verify *36*
      + Draw `8 ÷ 2` → verify *4*
      + Draw an ambiguous symbol → show `?` chip
      + Point out per-symbol color coding

      #v(16pt)
      #info[
        ```bash
        streamlit run draw.py
        ```
        Model: `outputs/best_model.keras` · 14 classes
      ]
    ],
    align(center + horizon)[
      #rect(fill: light, stroke: grey.lighten(40%),
            width: 100%, height: 250pt, radius: 6pt)[
        #align(center + horizon)[
          #text(size: 13pt, fill: grey)[_App screenshot_]
        ]
      ]
    ],
  )
]


// ══════════════════════════════════════════════════════════════════════════════
//  MATTI — Conclusion  (~1 min)
// ══════════════════════════════════════════════════════════════════════════════

#slide-frame(title: "Conclusion")[
  #grid(columns: (1fr, 1fr), gutter: 24pt,
    [
      *What we built*

      - End-to-end math solver running in the browser
      - *99.44% val accuracy* across 14 classes
      - One unified CNN — digits *and* operators
      - Safe AST evaluator (no `exec` / `eval`)

      #v(12pt)
      #callout(color: green)[
        Adding a new symbol class = more training data only, no new code.
      ]
    ],
    [
      *Future work*

      - Multi-digit numbers as a single unit
      - Fractions and parentheses
      - More classes: =, decimal point, variables
      - Larger operator dataset → reduce failure cases
      - Mobile / touch input optimization
    ],
  )
]

#polylux-slide[
  #rect(width: 100%, height: 100%, fill: navy)[
    #place(center + horizon)[
      #text(fill: white, size: 52pt, weight: "bold")[Thank You]
      #v(12pt)
      #text(fill: sky, size: 24pt)[Questions?]
      #v(36pt)
      #grid(columns: (1fr,) * 3, gutter: 12pt,
        align(center)[#text(fill: sky, size: 12pt)[*Matti H. V. Lehmann*]],
        align(center)[#text(fill: sky, size: 12pt)[*David A. Spickenheuer*]],
        align(center)[#text(fill: sky, size: 12pt)[*Jonas Schenke*]],
      )
      #v(6pt)
      #grid(columns: (1fr,) * 3, gutter: 12pt,
        align(center)[#text(fill: sky, size: 12pt)[*Philip Nguyen*]],
        align(center)[#text(fill: sky, size: 12pt)[*Staniya Thomas*]],
        align(center)[#text(fill: sky, size: 12pt)[*Abhirup Sain*]],
      )
    ]
  ]
]
