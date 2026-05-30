# ADR-0017 — Productization P4: Model Foundation Platform

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Productization P4
> **Builds on:** ADR-0001 … ADR-0016 (esp. P1 ADR-0014, P2 ADR-0015, P3 ADR-0016)
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-3/NR-3
> (patient-disjoint), AP-6/NR-9/NR-10 (determinism/reproducibility), AP-5/AP-8/NR-11
> (traceability/audit), AP-7/NR-8 (boundaries), AP-9/NR-5 (this record), NR-6 (reuse),
> NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the Productization P4 **Model Foundation Platform**
(`backend/model_foundation`) is shaped as it is, so the rationale survives turnover
(NR-14).

---

## 1. Context

P1–P3 took a real EEG file to validated, clean, feature-engineered assets. P4 takes the
next narrow step: turn **feature assets** into **validated trained models** — datasets,
training, evaluation, experiments, and a model registry — and nothing else. No
production inference, serving, APIs, user predictions, or frontend integration.

This is **productization**, not a new version. It must build strictly on P1–P3 and
reuse existing platform patterns.

## 2. Decisions

### D1 — One new `backend` subsystem, vertical population only (AP-1)
`backend/model_foundation` mirrors the established subsystem shape (datasets / training
/ evaluation / registry / experiments / validation / lineage / audit / reports /
schemas + models/identity/service). It imports `ml`, reuses the shared audit primitive
from `backend.clinical_cases.audit`, and never imports `frontend` (enforced by
`tests/test_boundaries.py`).

### D2 — Build on P1–P3; never redesign or duplicate
The trainable dataset is assembled from registered P3 `FeatureRecord` assets; the model
identity/lineage are parented through training-run → dataset → feature nodes. No prior
phase is modified or re-implemented.

### D3 — Deterministic, pure-NumPy reference models (no framework, no tuning)
`EEGNet`, `DeepConvNet`, `Temporal CNN`, `Transformer` are deterministic pure-NumPy
baselines (a fixed seeded front-end transform + a softmax head trained by deterministic
gradient descent), consistent with the platform's framework-free V1 approach. Per the
directive — **correctness first, do not optimize, do not tune**. They exercise the
training/evaluation/registry/lineage machinery reproducibly; they are not accuracy
claims. Determinism is *validated* (re-training reproduces identical parameter
fingerprints).

### D4 — External datasets are an integration framework (no downloads, no internet)
`TUH EEG`, `CHB-MIT`, and `Temple EEG` connectors register dataset metadata from a
locally-provided manifest (validated, content-addressed) — they never download data and
never require internet. The trainable source is `feature_assets`, assembled from a
fixed-length, channel-count-independent feature vector per recording.

### D5 — Patient-disjoint splits (AP-3/NR-3)
Datasets are split by *whole patients* (deterministic seeded ordering), so no patient
appears in two splits. The split is recorded and validated.

### D6 — Immutable, content-addressed artifacts
`DatasetRecord`, `TrainingRunRecord`, `EvaluationRecord`, `ExperimentRecord`, and the
`ModelRecord` are content-addressed and frozen; the model carries a parameter
*fingerprint*, not raw weights. Registries reject silent overwrite of a version with
different content.

### D7 — Reuse the shared audit + lineage; the full chain
Audit reuses the single hash-chained `ImmutableAuditLog` (`ModelAuditRecord`); lineage
reuses the shared `ml.lineage.LineageTracker`. A model node parents the training-run
node, which parents the dataset node, which parents the feature-asset nodes — so a
single `verify_chain` from a model reaches the patient:
`Patient → Case → EEG → Processed → Feature → Dataset → Training Run → Model`.

### D8 — Nine-check validation
`ModelContentValidator` (build-time) covers dataset / training / evaluation / model /
determinism integrity; `ModelIntegrityValidator` (post-build) reuses
`ml.validation.ValidationReport` to produce all nine (content + registry / audit /
lineage / version).

## 3. Consequences

- The deliverable executes with complete traceability: a real EEG file is loaded,
  cleaned, feature-engineered, assembled into a patient-disjoint dataset, used to train
  + evaluate + register models, tracked/audited/traced — `verify_chain` proves the full
  eight-stage chain. `python -m scripts.verify_productization_p4` exercises all 15
  criteria; the model suite passes and the full repository suite remains green.
- No new runtime dependencies beyond P1–P3 (numpy/scipy/mne already pinned). Models are
  framework-free.
- Acyclic DAG preserved; P1–P3 and V0–V4 remain intact (P4 only reads upstream assets
  and extends the shared lineage/audit).

## 4. Scope guard (explicitly NOT built — NR-13)

Inference APIs, serving, predictions, clinical decisions, FastAPI, database systems,
authentication, frontend, deployment, monitoring, Productization P5+, and Version 5.

## 5. Follow-ups / recorded debt (NR-2)

- Real labels + real external dataset materialization (behind the same connector
  contract) are future work; the framework registers external datasets but does not
  download them, and the demo labeling is deterministic, not clinical.
- Durable persistence of trained-model weights (the registry currently keeps a content
  fingerprint) shares the inherited Gap G3 and is future work behind the same contracts.
- Deep-learning-framework architectures (real EEGNet/DeepConvNet conv stacks) can
  replace the pure-NumPy reference baselines behind the same `BaselineModel` contract
  when a framework is adopted — still no serving in this layer.
