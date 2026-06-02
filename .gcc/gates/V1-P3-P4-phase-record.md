# Phase Record — V1-P3 (Dataset Intelligence Layer) + V1-P4 (Evaluation Foundation)

> **Rule:** NR-12 (never skip a version) · **Type:** phase delivery record (not a
> full version-exit certification).

## What this record asserts
The **V1-P3** and **V1-P4** subsystems are implemented, tested, and consistent with
the V0 constitution/architecture and the V1-P1/P2 foundations. This is a **phase
delivery**, not a claim that all of Version 1's exit criteria are satisfied.

## Delivered
- **V1-P3 — Dataset Intelligence Layer** (`evaluation/dataset_intelligence/`):
  profiling, statistics/distributions, patient/channel/recording analysis, class
  distribution (annotation→class, analysis only), data-quality scoring, and
  pre-split **leakage-risk** analysis — assembled into versioned, reproducible,
  content-fingerprinted reports. Consumes the V1-P1 `ValidatedEegRecord` contract;
  alters nothing in `datasets`/`preprocessing`.
- **V1-P4 — Evaluation Foundation** (`evaluation/`): patient-disjoint splits + LOSO
  (deterministic, disjoint by construction), the **leakage gate** (blocks runs),
  pure-NumPy metrics + registry (calibration/clinical = placeholders), provenance-
  bound benchmarking, evaluation registry, evaluation lineage, the run orchestrator,
  audit, and reports.

## Honest status against Version-1 exit criteria (VERSION_EVOLUTION_MODEL §2)
| V1 exit criterion | Status after V1-P1..P4 |
|-------------------|------------------------|
| 1. Preprocessing deterministic & versioned | **Met** (V1-P2). |
| 2. All reported metrics patient-disjoint; zero leakage | **Mechanism complete & enforced** (V1-P4 gate blocks leaky runs); awaits real model metrics (later phase). |
| 3. Uncertainty calibrated & coverage measured | **Reserved** — calibration/coverage are registered **placeholders**; computation is the future uncertainty phase (NR-13). |
| 4. Every result reproducible | **Met** for data/DSP/intelligence/evaluation artifacts (content-addressed, fingerprinted, tested). |
| 5. No principle/boundary violated | **Met** (leaf-purity + evaluation boundary tests; ruff + mypy clean). |

## Prerequisites & open items (transparency)
- **V0-P3 (GCC mechanisms)** remains *not yet implemented* (repo has V0-P1/P2);
  decisions/debt are recorded here as documentation (NR-5/NR-2), their *mechanized
  enforcement* is V0-P3 work.
- **Remaining V1 phases** before full V1 exit can be certified (NR-12): baseline ML
  (EEGNet/TCN/Mamba), calibrated uncertainty (Conformal Prediction), and reporting
  real patient-disjoint metrics through this framework.
- No models are trained in V1-P3/P4 (NR-13) — these phases build *understanding* and
  *truth* only.

## Evidence
- Tests: `datasets/tests` (49) + `preprocessing/tests` (70) +
  `evaluation/dataset_intelligence/tests` (33) + `evaluation/tests` (37) +
  `tests/` end-to-end (2) = **191 passing**.
- Lint: `ruff` clean. Types: `mypy` clean (169 source files).
- Decisions: [`../decisions/`](../decisions) (DR-0008..0012). Debt: [`../debt/`](../debt) (none).
