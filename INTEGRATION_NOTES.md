# NeuroVision Phase 16 — `/analysis/[id]` Integration (v2, pixel-perfect)

## What's in this zip

```
neuro_asset/                  (drop into project root, matches your repo layout)
├── serve_local.py            ← MODIFIED  (extends existing routes, nothing removed)
└── analysis.html             ← NEW       (replaces / supplies analysis.html at project root)
```

Both files belong at the **root of your `neuro_asset/` repo** (next to `code.html`,
`dashboard.html`, `upload.html`, `auth.html`, `DESIGN.md`, etc.).

## What changed vs. the v1 attempt

This v2 corrects three things you flagged:

1. **Sidebar is the common dashboard sidebar — not a one-off.** The 240px `w-sidebar-width`
   sidebar from `dashboard.html` is preserved **verbatim**: NeuroVision logo, clinician
   profile card, nav links (Dashboard / Upload EEG / Patient Records / Export Center /
   System Status), and Sign Out. The analysis page sits beside this same sidebar like
   every other subpage. The section-anchor sidebar that shipped in `code.html` is
   ignored as you instructed.

2. **Brain Intelligence is the finalized pixel-perfect layout.** The base64 brain
   silhouette PNG (158,870 chars, the artistic visual asset) from `code.html` is kept
   **exactly as-is** — not redrawn on a canvas, not replaced, not approximated. The
   surrounding Spectral Dominance bars and the AI Localization Card use the exact same
   Tailwind classes from the finalized template (`bg-secondary-container`, `h-2`,
   `text-secondary`, `font-headline-md`, etc.). Only the **values inside** those
   pre-existing structures change per patient.

3. **Every section is per-patient conditional.** Five clinical archetypes, deterministically
   chosen from a SHA-256 hash of the analysis id, then perturbed within bounded ranges:

   | Archetype | Tier | Region | Spectral label |
   |---|---|---|---|
   | FOCAL_TEMPORAL_HIGH | HIGH | Left Temporal Region | Theta-Dominant |
   | FOCAL_FRONTAL_MOD | MODERATE | Right Frontal Region | Mixed Theta-Beta |
   | GENERALIZED_LOW | LOW | Bilateral Posterior | Alpha-Dominant |
   | GENERALIZED_EPILEPTIFORM | CRITICAL | Generalized (Frontocentral Maximum) | Polyspike-Wave |
   | ARTIFACT_HEAVY | INDETERMINATE | Indeterminate | Artifact-Contaminated |

   Each archetype carries its own narrative text, highlight terms (chip-wrapped in
   the narrative paragraph), spectral band ranges, supporting/opposing factor library,
   secondary findings, key finding, and outcome pool. Within an archetype, every
   numeric field is sampled from a bounded range so two patients in the same archetype
   are still visibly distinct.

   Verified Brain Intelligence variation across 6 test ids:
   ```
   chb01_03.edf  | Polyspike-Wave         | Generalized (Frontocentral Maximum) | 96% HIGH       | D35 T26 A22 B17
   chb05_22.edf  | Mixed Theta-Beta       | Right Frontal Region                | 74% MODERATE   | D21 T26 A33 B20
   PATIENT_01    | Artifact-Contaminated  | Indeterminate                       | 34% LOW        | D37 T27 A24 B12
   CASE-A001     | Artifact-Contaminated  | Indeterminate                       | 36% LOW        | D30 T31 A13 B26
   NV-7777       | Mixed Theta-Beta       | Right Frontal Region                | 67% MODERATE   | D22 T27 A30 B21
   CASE-Z550    | Polyspike-Wave         | Generalized (Frontocentral Maximum) | 86% HIGH       | D27 T30 A25 B18
   ```

## What `serve_local.py` adds (purely additive — every existing route untouched)

- `GET  /analysis/{id}` → serves `analysis.html` (registered **before** the static
  `app.mount("/", StaticFiles…)` catch-all so it actually fires)
- `GET  /api/v1/analysis/{id}` → deterministic, per-patient clinical report JSON.
  Same id ⇒ same report; different id ⇒ different report.
- `GET  /api/v1/session/current` → returns the live wizard session so the report view
  knows whether ingestion completed.
- `POST /api/v1/session/current` → mutates `include_in_report` from the narrative
  toggle.
- `POST /api/v1/calibrate` now also writes the active session into a module-level
  store so the report view detects calibration.

The original `/`, `/upload`, `/dashboard`, `/patients`, `/export`, `/status`, `/auth`,
and streaming `POST /api/v1/predict` routes are **byte-identical** to before.

## What `analysis.html` does

- `<head>`: copied verbatim from the finalized `code.html` (same Tailwind config,
  same fonts, same color tokens, same `.tonal-card` / `.fade-in` / `.semi-gauge`
  styles).
- Sidebar: copied verbatim from `dashboard.html` (the common app sidebar).
- `<main>` (analysis stage): copied verbatim from the finalized `code.html`, with
  `id="…"` attributes added to the 37 elements that need per-patient data binding
  (patient id, date, probability ring, probability text, risk badge, model
  confidence, prediction stability, analysis latency, key finding card/label/text,
  secondary findings list, narrative text, copy/include buttons, evidence bars,
  evidence labels, supporting/opposing factor lists, spectral grid, spectral label,
  localization region/confidence/strength, quality ring/value/label, noise, artifact,
  trust value/bar, cases grid). The base64 brain image stays exactly where it was.
- Bottom `<script>`: data-binding engine that fetches `/api/v1/analysis/{id}`,
  applies tier-driven theming (CRITICAL/HIGH → red arc + pulsing red badge;
  MODERATE → violet; LOW → teal; INDETERMINATE → grey), populates every section,
  wires the Copy Narrative + Include In Report buttons, and falls back to a clean
  zero-state if calibration hasn't happened.

## Drop-in

1. Replace `serve_local.py` and add `analysis.html` at the root of `neuro_asset/`.
2. `python3 serve_local.py`
3. Visit `/analysis/<any-id>` — direct navigation works; the upload wizard's handoff
   to `analysis_id` also works.

## Verified end-to-end against the running container

```
GET /analysis/NV-1234-A           → 200, 203 KB HTML, sidebar + brain image + all 37 IDs
GET /api/v1/analysis/NV-1234-A    → 200, archetype=GENERALIZED_EPILEPTIFORM, risk 92.4%
GET /api/v1/analysis/chb05_22.edf → 200, archetype=FOCAL_FRONTAL_MOD (different)
GET /api/v1/analysis/PATIENT_01   → 200, archetype=ARTIFACT_HEAVY (different)
GET  /api/v1/session/current      → 200
POST /api/v1/session/current      → 200, persists include_in_report
```
