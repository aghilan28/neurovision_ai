# Productization P4 — Model Foundation Platform (design & contracts)

> **Phase:** Productization P4 · **Status:** Implemented
> **Decision record:** [`../../../.gcc/decisions/ADR-0017`](../../../.gcc/decisions/ADR-0017-productization-p4-model-foundation.md)

The objective is narrow: transform **feature assets** (P3) into **validated trained
models**, with datasets, training, evaluation, experiments, and a model registry — and
*nothing else* (no serving/inference/predictions).

---

## 1. Identity model

Content-addressed `"{kind}+{hash16}"` ids: `dataset` (from source + key + data
fingerprint), `training_run` (from dataset + training key), `evaluation` (from training
run), `experiment` (from dataset), `model` (from training run + parameter fingerprint).
A model derives from a training run, which derives from a dataset — so the
Patient → … → Dataset → Training Run → Model identity lineage is checkable.

## 2. Dataset foundation (P4-C/D)

* **External connectors** (`TUH EEG`, `CHB-MIT`, `Temple EEG`) register dataset metadata
  from a local **manifest** (validated + content-addressed). They never download data
  and never require internet — this is the integration *framework*.
* **Feature dataset builder** assembles a trainable matrix `X` (and labels `y`) from
  registered feature assets using a fixed-length, channel-count-independent set of
  feature vectors (`recording_temporal_summary`, `synchronization`, `spatial_summary`,
  `topographic_stat`, `band_summary`, `regional_rms`).
* **Patient-disjoint split** (NR-3): whole patients are assigned to train/val/test by a
  deterministic seeded ordering; no patient appears in two splits.
* The `DatasetRegistry` tracks datasets, versions, splits, metadata, validation state,
  and audit/lineage references.

## 3. Training foundation (P4-E/F)

Four deterministic pure-NumPy baseline architectures (`EEGNet`, `DeepConvNet`,
`Temporal CNN`, `Transformer`) — a fixed seeded front-end transform + a softmax head
trained by deterministic full-batch gradient descent. The trainer produces a
reproducible `TrainingRunRecord` (seed, hyperparameters, training metrics + history,
parameter fingerprint, parameter count). **Correctness first; no optimization/tuning.**

## 4. Evaluation engine (P4-G)

Deterministic metrics: accuracy, macro precision/recall/F1, confusion matrix,
calibration (ECE + multiclass Brier), uncertainty (mean normalized entropy + mean
confidence), and dataset metrics → a reproducible `EvaluationRecord`.

## 5. Experiment tracking (P4-H)

An `ExperimentRecord` binds dataset + model + configuration + metrics + artifacts +
content-addressed training/evaluation ids, stored in an `ExperimentRegistry`. Every run
is reproducible.

## 6. Model registry, audit, lineage (P4-I/J)

* **Model registry** — no orphan models; re-registering a version with different content
  is a forbidden silent overwrite. Tracks training/evaluation/experiment references.
* **Audit** — reuses the shared hash-chained `ImmutableAuditLog` (`ModelAuditRecord`);
  every dataset/training/evaluation/experiment/version/registration event is appended.
* **Lineage** — reuses the shared `ml.lineage.LineageTracker`; `verify_chain` from a
  model proves `Patient → Case → EEG → Processed → Feature → Dataset → Training Run → Model`.

## 7. Validation (the nine checks, P4-K)

Build-time **content** checks (persisted in `ModelValidationRecord`): dataset, training,
evaluation, model, determinism integrity. Post-build **structural** checks
(`ModelIntegrityValidator`, reusing `ml.validation.ValidationReport`): registry, audit,
lineage (reaches the patient), version.

## 8. Out of scope (forbidden in P4)

Inference APIs, serving, predictions, clinical decisions, FastAPI, database systems,
authentication, frontend, deployment, monitoring, Productization P5+, and Version 5.
