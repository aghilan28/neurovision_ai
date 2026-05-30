# Productization P5 — Clinical Inference Foundation (design & contracts)

> **Phase:** Productization P5 · **Status:** Implemented
> **Decision record:** [`../../../.gcc/decisions/ADR-0018`](../../../.gcc/decisions/ADR-0018-productization-p5-clinical-inference.md)

The objective is narrow: transform **feature assets + trained models** into **validated
prediction assets**, with execution, predictions, confidence, calibration, and
explanations — and *nothing else* (no APIs/serving/deployment/frontend).

---

## 1. Identity model

A prediction asset id is `"prediction+{hash16}"`, content-addressed from `(kind,
identity_version, {model_id, prediction_key})` where `prediction_key` fingerprints the
input feature asset + the prediction output. The same model + same input always yields
the same `prediction_id`. The `prediction` kind is parented on `model`.

## 2. Model execution (P5-C)

`ModelExecutionEngine` loads a model by **deterministic reconstruction** — it rebuilds
the dataset from the original feature assets (reusing P4's `build_feature_dataset`) and
re-trains (reusing P4's `train`) with the model's recorded seed/hyperparameters/
architecture — then **verifies** the reconstructed parameter fingerprint and training-run
id match the registered `ModelRecord`. Input/output validation guards the numeric
execution (feature-name match, finite values, probabilities summing to 1).

## 3. Prediction (P5-D)

`PredictionEngine` turns validated class probabilities into a `PredictionRecord`:
predicted class + label, per-class probabilities, prediction scores (max probability,
margin, normalized entropy), and decision metadata. Deterministic + reproducible.

## 4. Confidence (P5-E)

`ConfidenceEngine` produces a confidence score, a derived confidence interval,
perturbation-based **prediction stability** (a fixed deterministic perturbation set),
a reliability blend, an uncertainty summary, and a closed-vocabulary `ConfidenceLevel`.

## 5. Calibration (P5-F, NR-4)

`CalibrationEngine` assesses probability calibration against the model's dataset
(reusing the P4 ECE + Brier metrics), plus a reliability assessment, a per-prediction
confidence-consistency measure, and a closed-vocabulary `CalibrationQuality`.

## 6. Explainability (P5-G)

`ExplainabilityEngine` produces **structured** explanations (no images/UI): occlusion
feature contributions + normalized importance, band importance (model attribution over
`band_summary.*` features), input-derived channel importance (from the P3 `absolute_power`
per-channel vector), decision factors (top features), and a model-attribution summary.

## 7. Prediction asset, registry, audit, lineage (P5-H/I/J)

The immutable `InferenceRecord` bundles the prediction, confidence, calibration, and
explanation records + execution/model/feature metadata, validation, status, version,
lineage node, and audit head. `InferenceRegistry` admits no orphan assets and rejects
silent overwrite. Audit reuses the shared `ImmutableAuditLog`; lineage reuses the shared
`ml.lineage.LineageTracker` with the prediction node parenting the model + input feature
nodes, so `verify_chain` proves
`Patient → Case → EEG → Processed → Feature → Dataset → Training Run → Model → Prediction`.

## 8. Validation (the nine checks, P5-K)

Build-time **content** checks (persisted in `InferenceValidationRecord`): prediction,
confidence, calibration, explanation, determinism integrity. Post-build **structural**
checks (`InferenceIntegrityValidator`, reusing `ml.validation.ValidationReport`):
registry, audit, lineage (reaches the patient), version.

## 9. Out of scope (forbidden in P5)

FastAPI, REST APIs, serving infrastructure, WebSockets, authentication, frontend,
deployment, monitoring, databases, cloud infrastructure, Productization P6+, and Version 5.
