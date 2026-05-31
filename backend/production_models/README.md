# `backend/production_models` — Production Model Program (DRP-2)

Transforms the platform's **reference-grade** models into **production-candidate models**
with objective **evaluation, benchmark, and readiness** evidence. The scope is *model
development and validation* and nothing else — no model serving, no APIs, and no
frontend / backend-API / operations / deployment / security / inference-architecture
changes (all explicitly out of scope).

Decision record:
[`../../.gcc/decisions/ADR-0025`](../../.gcc/decisions/ADR-0025-drp2-production-models.md).

## What it does

```
build dataset (from feature assets) -> train (deterministic, reproducible) ->
track experiment -> evaluate -> benchmark -> compare -> score readiness ->
validate -> register -> track + audit + trace
```

`ProductionModelService.develop_model(feature_records, architecture=...)` runs the whole
governed flow for one architecture; `develop_all(...)` does it for every architecture and
`compare(...)` ranks them and recommends one.

## Architecture framework (DRP2-C)

Five production-candidate architectures, all behind one uniform contract:

| Architecture | Implementation |
|---|---|
| `eegnet` / `deepconvnet` / `temporal_cnn` / `transformer_eeg` | **wrappers** that reuse the existing `model_foundation` reference models (never removed) |
| `hybrid_eeg` | a **new** deterministic pure-NumPy composition (two fixed front-ends + shared softmax head) |

## Reuse — no parallel systems

- **Datasets:** reuses `model_foundation.build_feature_dataset` + the shared
  `DatasetRegistry`.
- **Models:** the base trained model is registered in the shared `model_foundation`
  `ModelRegistry` (architecture carried as a string). The **new** production-candidate
  artifacts (models with benchmark + readiness, experiments, benchmarks, evaluations,
  readiness assessments) live in this subsystem's `ProductionModelRegistry` — no parallel
  dataset / base-model registry is created.
- **Evaluation:** reuses the `model_foundation` base evaluator + metrics, then adds the
  structured analyses (confusion / calibration / error / class-distribution / stability /
  reliability).
- **Lineage + audit:** the single shared `ml.lineage.LineageTracker` and the shared
  `ImmutableAuditLog`.

## Determinism (NR-9 / NR-10)

Every id, version, fingerprint, metric, and report is content-derived (no wall-clock, no
randomness). Reproducibility is *verified* (each architecture is trained twice and the
parameter fingerprints compared). **Performance measures** (latency, memory, training /
inference time) are reported but are **informational only** — they never enter a signature,
so verdicts reproduce bit-for-bit.

## Readiness (DRP2-G)

Seven weighted dimensions — training / evaluation / benchmark / registry / validation /
lineage / audit. A model can be `READY` only when **all** of those records exist **and**
content validation passes; otherwise `PARTIALLY_READY` or `NOT_READY`.

## Traceability (DRP2-I)

A single `verify_chain` from a readiness assessment reaches the patient:

```
Patient -> Case -> EEG -> Processed -> Feature -> Dataset -> Training Run ->
Training Experiment -> Model -> Benchmark -> Readiness Assessment
```

## Boundary (NR-8)

Imports `ml` + sibling `backend` only; never imports `frontend`. Models are deterministic
pure-NumPy (no serving).

## Run

```bash
python -m scripts.verify_drp2_production_models     # the 15 final-validation criteria
python -m pytest tests/test_production_models.py tests/test_production_models_e2e.py
```

## Honest scope

This produces production-**candidate** models and the evidence to judge them. On the
synthetic feature cohort the reference baselines are **untuned** (Gap G1 from the
certification), so reported accuracies/ROC-AUC are *evidence about untuned baselines on
synthetic data*, never a clinical-performance claim. Real-data tuning and clinical
validation remain open conditions for later phases.
