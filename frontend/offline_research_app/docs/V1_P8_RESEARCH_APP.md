# V1-P8 — Offline Research Application (design)

> **Phase:** V1-P8 · **Status:** Implemented (offline)
> **Decision record:** [`../../../.gcc/decisions/ADR-0002`](../../../.gcc/decisions/ADR-0002-v1-p7-p8-offline-inference-and-research-app.md)

---

## 1. Principle: presentation only

Everything displayed originates from a **registered artifact** (output / report /
registry / dataset-intelligence record). The app reads `inference_index.json` to
discover artifact paths, loads them, and reshapes them into view-models. There is
**no hidden calculation in the UI** — structurally guaranteed because the frontend
imports no domain code (NR-8).

## 2. Data contract (the only coupling to the backend)

The backend writes a run directory; the app reads it:

```
inference_index.json     # ids, version bundle, validation, and paths to everything
outputs/*_output.json    # the 10 output contracts
reports/*.json           # 6 inference reports
registries/*.json        # inference / model / benchmark / lineage
dataset_intelligence.json
_manifest.json           # artifact checksums
```

This file layout is the contract — not shared Python types. The app defines its
own view-model schemas independently.

## 3. View-model pipeline

```
AppState.load(run_dir)
   → workflows (5)  → Page view-models (sections + visualizations)
   → AppValidator   → app-consistency report
   → pages.build_app_view → AppView
   → reports.render_app_html → deterministic static HTML
```

## 4. Rendering

The static HTML uses **CSS-only tabs** (radio inputs) and **inline SVG** for bar/
line/graph/layout charts. No JavaScript, no external assets, no timestamps — so the
page is fully offline and **byte-deterministic** for a given run.

## 5. App-consistency validation

`AppValidator` checks artifact consistency (every referenced path exists), registry
consistency (inference id registered), output consistency (prediction/probability/
clinical counts agree), version consistency (index vs summary bundle), and lineage
consistency (lineage id present). A failing check means the app would display an
inconsistent run — surfaced as a FAILED badge in the header.

## 6. Faithful uncertainty (NR-4)

The Inference workflow always shows calibration, the conformal set, coverage, and
risk alongside the prediction; the per-window table shows each window's calibrated
confidence and conformal set. Uncertainty is never hidden or flattened.
