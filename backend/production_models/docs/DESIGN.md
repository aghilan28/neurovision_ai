# Production Model Program — Design (DRP-2)

## Objective

Transform reference-grade models into **production-candidate models** with objective
training, evaluation, benchmark, comparison, and readiness evidence — strictly inside model
development and validation. No serving, APIs, frontend/backend-API/operations/deployment/
security, or inference-architecture changes.

## Package layout

```
backend/production_models/
  version.py            component versions + DETERMINISTIC_EPOCH + DEFAULT_SEED
  models/domain.py      closed vocabularies + 11 records (DRP2-B)
  identity/             mints production_model/training_experiment/benchmark/
                        model_evaluation/readiness; validates upstream ids
  architectures/        ReferenceArchitectureWrapper (reuses model_foundation) + HybridModel
                        + build_production_model + PRODUCTION_ARCHITECTURES (DRP2-C)
  training/             TrainingConfig + HYPERPARAMETER_REGISTRY + train_production (DRP2-D)
  benchmarking/         ROC-AUC/PR-AUC metrics + benchmark_model (DRP2-E)
  evaluation/           build_model_evaluation + compare_models (DRP2-F)
  readiness/            ReadinessEngine — 7 dimensions -> score/findings/class (DRP2-G)
  registry/             ProductionModelRegistry (DRP2-H)
  audit/                make_production_audit_log (shared ImmutableAuditLog) (DRP2-I)
  lineage/              production lineage helpers (shared ml.lineage) (DRP2-I)
  validation/           content validators + integrity validator (ml.validation) 
  reports/              nine deterministic report builders (DRP2-J)
  schemas/contracts.py  entity contracts (DRP2-K)
  service.py            ProductionModelService — the governed orchestration hub
```

## Domain records (DRP2-B)

`ProductionModelIdentity`, `ProductionModelRecord`, `ModelBenchmarkRecord`,
`ModelEvaluationRecord`, `ModelReadinessRecord`, `ModelValidationRecord`,
`ModelRegistryRecord`, `ModelAuditRecord`, `ModelLineageRecord`, `TrainingExperimentRecord`,
`BenchmarkVersion`. Closed vocabularies only.

## Reuse, not duplication

- `model_foundation.build_feature_dataset` + shared `DatasetRegistry` (datasets).
- `model_foundation.build_model` + reference architectures (the four standard wrappers).
- `model_foundation.evaluate` + `model_foundation.metrics` (base evaluation).
- shared `ModelRegistry` (the base trained model is registered there — no parallel registry).
- shared `ml.lineage.LineageTracker` + shared `ImmutableAuditLog` + `ml.validation`.

The `ProductionModelRegistry` only stores the **new** production-candidate concepts
(production models, experiments, benchmarks, evaluations, readiness assessments).

## Determinism & honest performance

Deterministic metrics (accuracy / precision / recall / F1 / ROC-AUC / PR-AUC / ECE / Brier)
enter ids + signatures. Performance measures (latency / memory / training / inference time)
are **informational** and excluded from every signature (the V1 offline-inference / P9
convention) — verdicts reproduce bit-for-bit while timings are still reported.

## Lineage chain

```
ds(parents = feature nodes) -> training_run -> training_experiment -> model
                                       \-> evaluation
model + evaluation -> benchmark -> readiness_assessment
```

`verify_chain(readiness.lineage_id)` reaches the patient.

## Readiness criteria

`READY` ⇔ training ∧ evaluation ∧ benchmark ∧ registry ∧ audit ∧ lineage records all
present ∧ a readiness score exists ∧ content validation passes. Otherwise
`PARTIALLY_READY` (score ≥ 0.5 and validation ok) or `NOT_READY`.

## Out of scope (forbidden in DRP-2)

FastAPI, frontend changes, backend-API changes, deployment changes, operations changes,
security changes, clinical validation, inference-architecture changes, DRP-3+.
