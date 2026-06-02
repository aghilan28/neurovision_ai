# ADR-0022 — Productization P9: Validation & Performance Assurance Program

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Productization P9
> **Builds on:** ADR-0001 … ADR-0021 (the full P1–P8 productization stack)
> **Enforces / honors:** AP-4/NR-4 (faithful uncertainty), AP-6/NR-9/NR-10 (determinism/
> reproducibility), AP-5/AP-8/NR-11 (traceability), AP-7/NR-8 (boundaries), AP-9/NR-5 (this
> record), NR-2 (zero hidden debt), NR-13 (scope)
> **Decision owner:** Platform/validation engineering (Kiro-assisted, subject to NR-7)

Captures why the Productization P9 **Validation & Performance Assurance Program**
(`validation/`) is shaped as it is, so the rationale survives turnover (NR-14).

---

## 1. Context

P1–P8 produced a deployable product. P9 produces **evidence**: how accurate are the models,
how reliable is the pipeline, how robust is the system, how stable are predictions, how
ready is the product. The scope is **validation only** — no new capability, no
architectural expansion, no Version 5 (NR-13).

## 2. Decisions

### D1 — A top-level `validation/` evaluation layer (peer of `scripts/`/`operations/`)
Validation **measures** the existing systems and modifies none of them. It is not one of the
six governed domain packages, so the per-module import DAG does not constrain it; it imports
`backend`/`operations` **lazily** to exercise the real platform. The dependency is strictly
one-way — **no domain package imports `validation`** (asserted in tests). It is distinct from
the V1 `evaluation/` foundation, which it reuses indirectly through the services.

### D2 — Deterministic evidence is signed; performance is informational
Output fingerprints, success/failure counts, model metric values, and readiness scores are
**deterministic** and enter reproducible signatures. Wall-clock latency, throughput, and
peak memory are **informational** and never enter a signature — so verdicts reproduce
bit-for-bit while timings are still reported (mirrors the V1 offline-inference convention,
NR-9/NR-10).

### D3 — Reuse existing metrics; reimplement nothing
Model metrics come from the P4 evaluation engine (accuracy / precision / recall / F1 /
confusion / ECE / Brier / entropy / confidence); calibration evidence comes from P4 + the P5
inference asset; the validated pipeline is the real P1–P5 pipeline. Validation orchestrates
and reads — it computes no parallel metric.

### D4 — "Do not retrain" is honored
The platform persists no model weights — a model *is* its deterministic reconstruction
(P4/P5). To obtain each baseline's evaluation, validation invokes the existing deterministic
P4 training; it introduces no new training regime, no tuning, and no new models.

### D5 — Accuracy is evidence, not a readiness gate
The four baselines (EEGNet / DeepConvNet / Temporal CNN / Transformer) are deterministic,
untuned reference models (P4, "correctness first, do not optimize"). Their accuracy is
**reported** in the executive summary; readiness gates instead on correctness, determinism,
calibration validity, and traceability. This is honest evidence, not an inflated claim.

### D6 — Drift is measured, never corrected (P9-H)
The drift module quantifies input/feature/prediction/pipeline drift + model consistency and
reports it; it performs no correction.

### D7 — Robustness = graceful handling + recovery
The platform must never crash on bad input; it must return a structured outcome
(rejected/quarantined) and recover for the next input. The robustness suite feeds corrupted/
partial/empty/truncated/noisy/unsupported/nonexistent inputs and asserts exactly that.

## 3. Consequences

- `python -m scripts.verify_productization_p9` exercises all 15 criteria (**ALL PASS**),
  including determinism (within + cross instance), traceability to the patient, nine
  readiness scorecards, nine reports, and an executive summary.
- The new suite adds 14 tests; the full repository suite is **824 passed** (was 810).
  `ruff` is clean on all new code; `tests/test_boundaries.py` stays green; no domain package
  imports `validation`.
- No new runtime dependencies; validation runs in isolated temp workspaces and changes no
  repository state.

## 4. Scope guard (explicitly NOT built — NR-13)

New models, model retraining (as a regime), new features, frontend/backend/operational
changes, clinical validation, pilot deployments, Version 5, Productization P10.

## 5. Measured findings (disclosed, not hidden — NR-2)

- On the committed deterministic EEG fixtures, the untuned reference baselines vary widely in
  accuracy (e.g., Transformer 1.00, others 0.00 on this tiny synthetic cohort). This is
  expected for *untuned reference* baselines and is reported as evidence — **not** a clinical
  or tuned-performance claim (Gap G1: synthetic-data lineage).
- Determinism, reliability, robustness, calibration validity, traceability, and overall
  readiness all hold and are reproducible.
