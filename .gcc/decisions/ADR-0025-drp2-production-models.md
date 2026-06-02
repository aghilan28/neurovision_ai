# ADR-0025 — DRP-2: Production Model Program

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Deployment Remediation Program DRP-2 (post-audit remediation)
> **Builds on:** ADR-0001 … ADR-0024 (Productization P1–P10 + DRP-1 Real Dataset Integration)
> **Resolves:** Audit blocker — *NO VALIDATED MODELS* (reference-grade models; insufficient
> evaluation / benchmark / readiness evidence)
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-5/AP-8/NR-11 (traceability),
> AP-7/NR-8 (boundaries), NR-6 (reuse), AP-9/NR-5 (this record), NR-13 (scope), NR-2 (honesty)

## 1. Context

After DRP-1 integrated real datasets, the Independent Production Reality Audit's next gap was
that the platform's models were **reference-grade** with **insufficient evaluation, benchmark,
and readiness evidence**. DRP-2 adds the governed program that develops **production-candidate
models** and the objective evidence to judge them. The scope is strictly model development and
validation: no model serving, no APIs, and no frontend / backend-API / operations / deployment
/ security / inference-architecture changes (NR-13).

## 2. Decisions

### D1 — A new governed `backend/production_models` subsystem
Adds the architecture framework, training, benchmarking, evaluation, readiness, registry,
lineage, audit, reports, schemas, and a service hub. It develops + validates models; it does
**not** serve models or modify any other subsystem. As a `backend` package it obeys the import
DAG (imports `ml` + sibling `backend`, never `frontend`; enforced by `tests/test_boundaries.py`).

### D2 — Five production architectures; reuse the reference models, don't remove them
`eegnet`, `deepconvnet`, `temporal_cnn`, `transformer_eeg` are production **wrappers** around
the existing `model_foundation` deterministic reference models (reused, never modified or
removed). `hybrid_eeg` is a **new** deterministic pure-NumPy composition (two fixed seeded
front-ends + a shared softmax head). All five expose one uniform contract so training /
evaluation / benchmarking treat them identically.

### D3 — Reuse the shared registries; no parallel registries
Datasets are built with `model_foundation.build_feature_dataset` and registered in the shared
`DatasetRegistry`; each base trained model is registered in the shared `ModelRegistry`
(architecture carried as a string). Only the genuinely-new production-candidate artifacts
(production models with benchmark + readiness, training experiments, benchmarks, evaluations,
readiness assessments) live in this subsystem's `ProductionModelRegistry`. No parallel
dataset / base-model registry is created.

### D4 — Reuse shared lineage / audit / validation / evaluation
One `ml.lineage` tracker (extending the model-foundation dataset/training/evaluation helpers
with `training_experiment`, `model`, `benchmark`, `readiness_assessment` nodes), the shared
`ImmutableAuditLog` (bound to `ModelAuditRecord`), `ml.validation.ValidationReport`, and the
`model_foundation` base evaluator + metrics. No parallel systems.

### D5 — Deterministic verdicts; informational performance
Deterministic metrics (accuracy / precision / recall / F1 / ROC-AUC / PR-AUC / ECE / Brier)
are content-addressed and enter every id + signature. Performance measures (latency, peak
memory, training time, inference time) are measured live but are **informational** and
excluded from every signature (the V1 offline-inference / P9 convention) — so a benchmark id
and a model version reproduce bit-for-bit while timings are still reported. Reproducibility is
*verified*: each architecture is trained twice and the parameter fingerprints compared.

### D6 — Readiness = development-readiness, with a hard gate
Seven weighted dimensions (training / evaluation / benchmark / registry / validation / lineage
/ audit) → score + findings + NOT_READY / PARTIALLY_READY / READY. A model can be `READY` only
when **all** of those records exist **and** content validation passes — a missing benchmark or
a failed validation can never be `READY`.

## 3. Consequences

- `python -m scripts.verify_drp2_production_models` → **ALL 15 CRITERIA PASS**; all five
  architectures are trained, evaluated, benchmarked, scored **READY**, traceable
  (Patient → … → Feature → Dataset → Training Run → Training Experiment → Model → Benchmark →
  Readiness), and audited.
- The new suite adds 21 tests; the full repository suite is **872 passed** (was 851). `ruff`
  clean on all new code; `tests/test_boundaries.py` green; prior verify scripts unaffected.
- No new runtime dependencies; the subsystem runs offline and deterministically.

## 4. Scope guard (explicitly NOT built — NR-13)

FastAPI, frontend changes, backend-API changes, deployment changes, operations changes,
security changes, clinical validation, inference-architecture changes, DRP-3+.

## 5. Honesty statement (NR-2)

DRP-2 produces production-**candidate** models and the evidence to judge them; it does not
claim clinical performance. On the synthetic feature cohort the reference baselines are
**untuned** (Gap G1 from the P10 certification), so reported accuracies / ROC-AUC are
*evidence about untuned reference baselines on synthetic data*, never a clinical-performance
claim. Real-data tuning, large-cohort benchmarking, and formal clinical validation remain open
conditions for later remediation phases. The `hybrid_eeg` architecture is a deterministic
reference composition for exercising the production machinery, not a tuned clinical model.
