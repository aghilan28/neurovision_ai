# ADR-0018 — Productization P5: Clinical Inference Foundation

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Productization P5
> **Builds on:** ADR-0001 … ADR-0017 (esp. P1 ADR-0014 … P4 ADR-0017)
> **Enforces / honors:** AP-1 (vertical population), AP-6/NR-9/NR-10 (determinism/
> reproducibility), NR-4 (calibrated uncertainty), AP-5/AP-8/NR-11 (traceability/audit),
> AP-7/NR-8 (boundaries), AP-9/NR-5 (this record), NR-6 (reuse), NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the Productization P5 **Clinical Inference Foundation**
(`backend/inference_foundation`) is shaped as it is, so the rationale survives turnover
(NR-14).

---

## 1. Context

P1–P4 took a real EEG file to validated, clean, feature-engineered assets and trained
models. P5 takes the next narrow step: turn **feature assets + trained models** into
**validated prediction assets** — execution, predictions, confidence, calibration, and
explanations — and nothing else. No APIs, serving, deployment, frontend, user accounts,
or serving infrastructure.

This is **productization**, not a new version. It must build strictly on P1–P4 and reuse
existing platform patterns.

## 2. Decisions

### D1 — One new `backend` subsystem, vertical population only (AP-1)
`backend/inference_foundation` mirrors the established subsystem shape (models / inference
/ confidence / calibration / explainability / registry / validation / lineage / audit /
reports / schemas + identity/service). It imports `ml`, reuses P4 modules, reuses the
shared audit primitive, and never imports `frontend` (enforced by `tests/test_boundaries.py`).

### D2 — Model loading via reproducibility + verification (P5-C)
P4 persists only a model's parameter *fingerprint*, not raw weights. P5 reconstructs the
trained model deterministically by reusing P4's `build_feature_dataset` + `train` on the
original feature assets, then **verifies** the reconstructed parameter fingerprint *and*
training-run id equal the registered `ModelRecord`. This reuses the P4 pipeline (no
parallel training) and the verification is the guarantee — a mismatch raises.

### D3 — Immutable, content-addressed prediction assets (P5-D/H)
The `InferenceRecord` (prediction asset) is **frozen** and content-addressed; the same
model + same input always produce the same `prediction_id` (idempotent, reproducible).
It bundles the prediction, confidence, calibration, and explanation records + execution/
model/feature metadata. It carries no model weights and no raw signal.

### D4 — Deterministic confidence + calibrated uncertainty (P5-E/F, NR-4)
Confidence (score, derived interval, fixed-perturbation stability, reliability blend,
uncertainty summary, level) and calibration (ECE + Brier via the reused P4 metrics,
reliability, confidence consistency, quality) are deterministic functions — uncertainty
is always reported alongside the label (NR-4).

### D5 — Structured explanations only (P5-G)
Explainability is occlusion-based feature contributions/importance + band importance
(model attribution) + input-derived channel importance (from the P3 feature asset) +
decision factors + a model-attribution summary. **Structured outputs only — no images,
no UI, no dashboards.**

### D6 — Reuse the shared audit + lineage; the full chain (P5-J)
Audit reuses the single hash-chained `ImmutableAuditLog` (`InferenceAuditRecord`);
lineage reuses the shared `ml.lineage.LineageTracker`. A prediction node parents **both**
the model node and the input feature node, so a single `verify_chain` from a prediction
reaches the patient:
`Patient → Case → EEG → Processed → Feature → Dataset → Training Run → Model → Prediction`.

### D7 — Nine-check validation (P5-K)
`InferenceContentValidator` (build-time) covers prediction / confidence / calibration /
explanation / determinism integrity; `InferenceIntegrityValidator` (post-build) reuses
`ml.validation.ValidationReport` to produce all nine (content + registry / audit /
lineage / version).

## 3. Consequences

- The deliverable executes with complete traceability: a real EEG file is loaded,
  cleaned, feature-engineered, used to train + evaluate a model, and then a prediction +
  confidence + calibration + explanation are generated, validated, tracked, audited, and
  traced — `verify_chain` proves the full nine-stage chain.
  `python -m scripts.verify_productization_p5` exercises all 15 criteria; the inference
  suite passes and the full repository suite remains green.
- No new runtime dependencies beyond P1–P4 (numpy/scipy/mne already pinned).
- Acyclic DAG preserved; P1–P4 and V0–V4 remain intact (P5 only reads upstream assets +
  reuses P4 modules and extends the shared lineage/audit).

## 4. Scope guard (explicitly NOT built — NR-13)

FastAPI, REST APIs, serving infrastructure, WebSockets, authentication, frontend,
deployment, monitoring, databases, cloud infrastructure, Productization P6+, and Version 5.

## 5. Follow-ups / recorded debt (NR-2)

- Persisting model weights (so inference need not reconstruct the model) shares the
  inherited Gap G3 and is future work behind the same `ModelRecord`/execution contract.
- Richer explanations (gradient/SHAP-style attributions through a framework-backed model)
  can replace the occlusion attribution behind the same `ExplanationRecord` contract.
- Clinical labels + real calibration cohorts (vs. the deterministic demo labeling) attach
  behind the same dataset/calibration contracts in a later phase.
