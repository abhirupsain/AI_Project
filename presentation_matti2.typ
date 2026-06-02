// ─────────────────────────────────────────────────────────────────────────────
//  Draw & Solve — 20-minute Presentation (v2)
// ─────────────────────────────────────────────────────────────────────────────

#let polylux-slide(body) = { body; pagebreak(weak: true) }

// ── Palette ──────────────────────────────────────────────────────────────────
#let title-color = rgb("#0D1B2A")   // R13 G27 B42 — used for all titles
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
#set page(width: 33.867cm, height: 19.05cm, margin: 0pt)
#set text(size: 18pt, fill: black)
#set strong(delta: 200)

// ── Helpers ───────────────────────────────────────────────────────────────────

#let slide-frame(header-color: navy, title: [], slide-num: [], body) = {
  polylux-slide[
    #grid(rows: (52pt, 1fr),
      rect(width: 100%, height: 100%, fill: header-color,
           inset: (x: 28pt, y: 0pt))[
        #align(left + horizon)[
          #grid(columns: (1fr, auto), gutter: 0pt,
            text(font: "Calibri", fill: white, size: 20pt, weight: "bold")[#title],
            align(right + horizon)[
              #rect(fill: white.transparentize(70%), radius: 4pt,
                    inset: (x: 8pt, y: 3pt))[
                #text(fill: white, size: 12pt, weight: "bold")[#slide-num]
              ]
            ]
          )
        ]
      ],
      rect(width: 100%, height: 100%, fill: white,
           inset: (x: 32pt, y: 18pt))[#body],
    )
  ]
}

#let section-slide(color: navy, label: [], title: [], subtitle: [], slide-num: []) = {
  polylux-slide[
    #rect(width: 100%, height: 100%, fill: color)[
      #place(right + top, dx: -14pt, dy: 14pt)[
        #rect(fill: white.transparentize(70%), radius: 4pt,
              inset: (x: 8pt, y: 3pt))[
          #text(fill: white, size: 12pt, weight: "bold")[#slide-num]
        ]
      ]
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

#slide-frame(title: "Error Analysis", slide-num: "28")[
  #grid(columns: (1fr, 1fr), gutter: 24pt,
    [
      *Top confusion pairs* (test set, 59 total errors)

      #table(
        columns: (auto, auto, auto, 1fr),
        fill: (_, row) => if row == 0 { navy }
                          else if calc.odd(row) { light } else { white },
        stroke: none, inset: (x: 8pt, y: 7pt),
        [*True*], [*Predicted*], [*Count*], [*Why?*],
        [`4`], [`9`], [5], [Open loop vs. stem],
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
//  ABHIRUP — Demo (~2 min)
// ══════════════════════════════════════════════════════════════════════════════

#slide-frame(title: "Demo", slide-num: "29")[
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
//  MATTI — Conclusion (~1 min)
// ══════════════════════════════════════════════════════════════════════════════

#slide-frame(title: "Conclusion", slide-num: "30")[
  // ── Top stat row ──
  #grid(columns: (1fr, 1fr, 1fr, 1fr), gutter: 10pt,
    rect(fill: navy, stroke: none, radius: 5pt, inset: (x: 10pt, y: 10pt))[
      #align(center)[
        #text(size: 24pt, fill: white, weight: "bold")[99.44%]
        #text(size: 10pt, fill: white.transparentize(30%))[Test accuracy]
      ]
    ],
    rect(fill: blue, stroke: none, radius: 5pt, inset: (x: 10pt, y: 10pt))[
      #align(center)[
        #text(size: 24pt, fill: white, weight: "bold")[14]
        #text(size: 10pt, fill: white.transparentize(30%))[Unified classes]
      ]
    ],
    rect(fill: teal, stroke: none, radius: 5pt, inset: (x: 10pt, y: 10pt))[
      #align(center)[
        #text(size: 24pt, fill: white, weight: "bold")[~178K]
        #text(size: 10pt, fill: white.transparentize(30%))[Parameters]
      ]
    ],
    rect(fill: purple, stroke: none, radius: 5pt, inset: (x: 10pt, y: 10pt))[
      #align(center)[
        #text(size: 24pt, fill: white, weight: "bold")[< 3 min]
        #text(size: 10pt, fill: white.transparentize(30%))[Training time]
      ]
    ],
  )

  #v(16pt)

  // ── Two-column body ──
  #grid(columns: (1fr, 1fr), gutter: 24pt,
    [
      #callout(color: navy)[
        *What we built* — End-to-end math solver running in the browser.
      ]

      #v(8pt)
      - One unified CNN — digits *and* operators
      - Safe AST evaluator (no `exec` / `eval`)
      - OpenCV segmentation with proximity merging

      #v(12pt)
      #callout(color: green)[
        Adding a new symbol class = more training data only, no new code.
      ]
    ],
    [
      #callout(color: teal)[
        *Future work* — Next steps to extend the project.
      ]

      #v(8pt)
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
    #place(right + top, dx: -14pt, dy: 14pt)[
      #rect(fill: white.transparentize(70%), radius: 4pt,
            inset: (x: 8pt, y: 3pt))[
        #text(fill: white, size: 11pt, weight: "bold")[31]
      ]
    ]
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
