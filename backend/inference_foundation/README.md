# `backend/inference_foundation/` — Clinical Inference Foundation (Productization P5)

> **Layer:** Application (`backend/`) · **Status:** Implemented (Productization P5).
> **Decision record:** [`../../.gcc/decisions/ADR-0018`](../../.gcc/decisions/ADR-0018-productization-p5-clinical-inference.md)
> **Builds on:** P1 ([`../eeg_foundation/`](../eeg_foundation/README.md)) + P2 ([`../signal_processing/`](../signal_processing/README.md)) + P3 ([`../feature_engineering/`](../feature_engineering/README.md)) + P4 ([`../model_foundation/`](../model_foundation/README.md)).
> **Governing docs:** AP-5/AP-8/NR-11 (traceability/audit), AP-6/NR-9/NR-10 (determinism/reproducibility), NR-4 (calibrated uncertainty), AP-7/NR-8 (boundaries)

Transforms **feature assets + trained models** into **validated prediction assets**.
The scope is *inference* and nothing else:

    load + verify model → execute → predict → confidence → calibration →
    explanation → validate → register → track + audit + trace

There is **no API, serving, deployment, frontend, user account, or serving
infrastructure** in this layer (all out of scope for this phase).

Built **strictly on P1–P4**: it reuses the existing EEG / processed-EEG / feature /
dataset / training / evaluation / model artifacts; it never redesigns prior phases or
creates parallel pipelines. A prediction's lineage parents the **model** node *and* the
**input feature** node, so the platform-wide chain is:

    Patient → Case → EEG → Processed EEG → Feature Asset → Dataset → Training Run → Model → Prediction

---

## Subsystems

| Subsystem | Role |
|-----------|------|
| `models/` | Domain entities + closed vocabularies (`ConfidenceLevel`, `CalibrationQuality`, `ExplanationMethod`, `InferenceStatus`) + `PredictionRecord` / `ConfidenceRecord` / `CalibrationRecord` / `ExplanationRecord` / `InferenceRegistryRecord` + the immutable `InferenceRecord` (prediction asset). |
| `identity/` | Deterministic `prediction+{hash16}` ids (content-addressed from model + input; never filename-derived). |
| `inference/` | `ModelExecutionEngine` (deterministic model loading + **verification** by reconstruction + input/output validation) + `PredictionEngine` (structured `PredictionRecord`). |
| `confidence/` | `ConfidenceEngine` — confidence score, derived interval, perturbation stability, reliability blend, uncertainty summary, confidence level. |
| `calibration/` | `CalibrationEngine` — ECE + Brier (reusing P4 metrics), reliability, confidence consistency, calibration quality. |
| `explainability/` | `ExplainabilityEngine` — occlusion feature contributions/importance, band importance, input-derived channel importance, decision factors, model-attribution summary. **Structured only — no images/UI.** |
| `registry/` | `InferenceRegistry` — no orphan assets; silent overwrite rejected. |
| `validation/` | `InferenceContentValidator` (prediction/confidence/calibration/explanation/determinism) + `InferenceIntegrityValidator` (the full 9 checks, reusing `ml.validation.ValidationReport`). |
| `audit/` | Reuses the shared tamper-evident `ImmutableAuditLog` bound to `InferenceAuditRecord` (no parallel audit). |
| `lineage/` | Prediction lineage nodes on the shared `ml.lineage.LineageTracker`, parenting the model + input feature nodes (no parallel lineage). |
| `reports/` | Prediction / confidence / calibration / explainability / registry / audit / lineage / validation / inference reports (deterministic). |
| `schemas/` | Per-entity contracts: Schema · Version · Validation/Lineage/Audit rules. |
| `service.py` | `InferenceFoundationService` — the governed orchestration hub. |

> **Tests & fixtures** live in the repository-root `tests/`
> (`tests/test_inference_foundation*.py`) and **reuse the P1–P4 assets** + the P1 EEG
> fixtures (no replacement systems). Design notes are in `docs/`.

## The single use case

```python
from ml.lineage import LineageTracker
from backend.model_foundation import ModelFoundationService, ModelArchitecture
from backend.inference_foundation import InferenceFoundationService

tracker = LineageTracker()
# ... P1 ingest -> P2 process -> P3 features for several patients => feature_assets ...
model = ModelFoundationService(lineage_tracker=tracker).train_model(
    feature_assets, architecture=ModelArchitecture.EEGNET, dataset_key="cohort", seed=7).model

inf = InferenceFoundationService(lineage_tracker=tracker)
outcome = inf.predict(model, feature_assets[0], train_feature_records=feature_assets,
                      dataset_key="cohort")
asset = outcome.asset                                # an immutable, validated prediction asset
assert tracker.verify_chain(asset.lineage_id)        # Patient → ... → Model → Prediction verifies
```

## Model loading via reproducibility (P5-C)

P4 persists only the model's *parameter fingerprint*, not raw weights. `ModelExecutionEngine`
therefore **reconstructs** the trained model deterministically (reusing P4's
`build_feature_dataset` + `train` on the original feature assets) and **verifies** that
the reconstructed parameter fingerprint *and* training-run id match the registered
`ModelRecord` (Model Loading + Model Verification + Version Verification). The
verification is the guarantee; a mismatch raises.

## Determinism, immutability & boundaries

* All ids, versions, fingerprints, probabilities, and report contents are
  content-derived; no wall-clock or randomness enters a hash (the confidence-stability
  perturbations are a fixed deterministic set). Determinism is *validated* (re-inference
  reproduces an identical prediction fingerprint).
* The `InferenceRecord` is **immutable** (frozen; carries derived artifacts + fingerprints,
  not model weights or raw signal).
* Imports `ml` (provenance/lineage/validation), reuses P4 modules (dataset/training/
  metrics) for reconstruction + calibration, and reuses the audit primitive from
  `backend.clinical_cases.audit` (intra-`backend` reuse). It never imports `frontend` and
  performs **no serving/APIs/deployment** (NR-8 / NR-13). Enforced by `tests/test_boundaries.py`.

## Verification

```bash
python -m scripts.verify_productization_p5     # the 15 phase-completion criteria
python -m pytest tests/test_inference_foundation.py tests/test_inference_foundation_e2e.py
```
