# Phase Record — V1-P1 (EEG Data Foundation) + V1-P2 (Signal-Processing Foundation)

> **Rule:** NR-12 (never skip a version) · **Type:** phase delivery record (not a
> full version-exit certification).

## What this record asserts
The **V1-P1** and **V1-P2** *foundations* are implemented, tested, and consistent
with the V0 constitution and architecture. This is a **phase delivery**, not a
claim that all of Version 1's exit criteria are satisfied.

## Delivered
- **V1-P1 — EEG Data Foundation:** EDF/EDF+ ingestion, validation, canonical
  metadata, discoverable record/dataset registries, content-addressed versioning
  (manifests, version chain, change tracking, audits), and a provenance lineage
  DAG. 8 formal data contracts. Deterministic, traceable, reproducible.
- **V1-P2 — Signal-Processing Foundation:** deterministic, versioned pipeline
  (resampling → filtering → montage → normalization → windowing) with input/
  channel/output validation, report-only signal quality, artifact persistence, and
  preprocessing lineage. Filters validated by frequency response.

## Honest status against Version-1 exit criteria (VERSION_EVOLUTION_MODEL §2)
| V1 exit criterion | Status after V1-P1+P2 |
|-------------------|------------------------|
| 1. Preprocessing deterministic & versioned | **Met** for the implemented pipeline (tested). |
| 2. All reported metrics patient-disjoint; zero leakage | **N/A yet** — no ML/metrics in these phases; patient *identity* primitive is in place (AP-2). |
| 3. Uncertainty calibrated & coverage measured | **Out of scope** for V1-P1/P2 (later V1 phase; directive: no models). |
| 4. Every result reproducible | **Met** for data/DSP artifacts (content-addressed, fingerprinted, tested). |
| 5. No principle/boundary violated | **Met** (leaf purity test; lint; consistent with IMPORT_RULES). |

## Prerequisites & open items (transparency)
- **V0-P3 (GCC mechanisms)** — import-check/decision/version-gate **automation** is
  *not yet implemented* in the repository (only V0-P1+P2 are committed). Decisions
  and debt are recorded here as documentation (NR-5/NR-2); their *mechanized
  enforcement* remains V0-P3 work. Per NR-12, full V1 exit cannot be certified until
  V0-P3 and the remaining V1 phases (datasets curation surface, baseline ML,
  uncertainty, patient-disjoint evaluation) are complete and recorded.
- This record exists so that status is **explicit**, not overstated.

## Evidence
- Tests: `datasets/tests` (49) + `preprocessing/tests` (70) pass.
- Lint: `ruff` clean over `datasets/` and `preprocessing/`.
- Decisions: [`../decisions/`](../decisions). Debt: [`../debt/`](../debt) (none).
