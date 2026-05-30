# `backend/model_foundation/` — Model Foundation Platform (Productization P4)

> **Layer:** Application (`backend/`) · **Status:** Implemented (Productization P4).
> **Decision record:** [`../../.gcc/decisions/ADR-0017`](../../.gcc/decisions/ADR-0017-productization-p4-model-foundation.md)
> **Builds on:** P1 ([`../eeg_foundation/`](../eeg_foundation/README.md)) + P2 ([`../signal_processing/`](../signal_processing/README.md)) + P3 ([`../feature_engineering/`](../feature_engineering/README.md)).
> **Governing docs:** AP-5/AP-8/NR-11 (traceability/audit), AP-6/NR-10 (reproducibility), AP-3/NR-3 (patient-disjoint), AP-7/NR-8 (boundaries)

Transforms **feature assets** (from Productization P3) into **validated trained
models**. The scope is *model creation* and nothing else:

    build dataset → train → evaluate → track experiment → validate → register model
    → track + audit + trace

There is **no production inference, serving, API, user prediction, or frontend
integration** in this layer (all out of scope for this phase).

Built **strictly on P1 + P2 + P3**: it reuses the existing EEG, processed-EEG, and
feature assets; it never redesigns prior phases or creates parallel EEG pipelines. A
model's lineage parents its training run → dataset → feature assets, so the
platform-wide chain is:

    Patient → Case → EEG → Processed EEG → Feature Asset → Dataset → Training Run → Model

---

## Subsystems

| Subsystem | Role |
|-----------|------|
| `models/` | Domain entities + closed vocabularies (`ModelArchitecture`, `DatasetSource`, `SplitName`, `DatasetStatus`, `ModelStatus`, `ExperimentStatus`) + `DatasetRecord`, `TrainingRunRecord`, `EvaluationRecord`, `ExperimentRecord`, `ModelMetadata`, `ModelValidationRecord`, `ModelRegistryRecord`, the immutable `ModelRecord`, … |
| `identity/` | Deterministic `dataset` / `training_run` / `evaluation` / `experiment` / `model` ids (content-addressed; never filename-derived). |
| `datasets/` | External dataset integration framework — **TUH EEG / CHB-MIT / Temple EEG** connectors (manifest-based, **no download, no internet**) + a builder that assembles a trainable, **patient-disjoint** dataset from feature assets. |
| `training/` | Baseline architectures (**EEGNet / DeepConvNet / Temporal CNN / Transformer**) — deterministic pure-NumPy reference models — and a reproducible (seeded) trainer. |
| `evaluation/` | Deterministic metrics (accuracy / precision / recall / F1 / confusion matrix / calibration ECE+Brier / uncertainty) + evaluator. |
| `experiments/` | Experiment tracking — binds dataset + model + config + metrics + artifacts into a reproducible `ExperimentRecord` + registry. |
| `registry/` | `DatasetRegistry` + `ModelRegistry` — no orphan datasets/models; silent overwrite rejected. |
| `validation/` | `ModelContentValidator` (dataset/training/evaluation/model/determinism) + `ModelIntegrityValidator` (the full 9 checks, reusing `ml.validation.ValidationReport`). |
| `audit/` | Reuses the shared tamper-evident `ImmutableAuditLog` bound to `ModelAuditRecord` (no parallel audit). |
| `lineage/` | Dataset / training-run / evaluation / model lineage nodes on the shared `ml.lineage.LineageTracker` (no parallel lineage). |
| `reports/` | Dataset / training / evaluation / experiment / registry / audit / lineage / validation / model reports (deterministic). |
| `schemas/` | Per-entity contracts: Schema · Version · Validation/Lineage/Audit rules. |
| `service.py` | `ModelFoundationService` — the governed orchestration hub. |

> **Tests & fixtures** live in the repository-root `tests/`
> (`tests/test_model_foundation*.py`) and **reuse the P1/P2/P3 assets** + the P1 EEG
> fixtures (no replacement systems). Design notes are in `docs/`.

## The single use case

```python
from ml.lineage import LineageTracker
from backend.clinical_cases import CaseService
from backend.eeg_foundation import EEGFoundationService, LocalEEGStore
from backend.signal_processing import SignalProcessingService, ProcessedSignalStore
from backend.feature_engineering import FeatureEngineeringService
from backend.model_foundation import ModelFoundationService, ModelArchitecture

tracker = LineageTracker()
# ... ingest (P1) -> process (P2) -> generate_features (P3) for several patients ...
feature_assets = [...]                               # P3 FeatureRecord assets (shared tracker)

mf = ModelFoundationService(lineage_tracker=tracker)
outcome = mf.train_model(feature_assets, architecture=ModelArchitecture.EEGNET,
                         dataset_key="cohort-1", seed=7)
model = outcome.model                                # an immutable, validated trained model
assert tracker.verify_chain(model.lineage_id)        # Patient → ... → Training Run → Model verifies
```

External datasets are integrated via the framework (no download):

```python
from backend.model_foundation import DatasetSource
mf.register_external_dataset(DatasetSource.TUH_EEG,
    {"name": "TUH", "n_recordings": 100, "patients": [...], "channels": [...],
     "sampling_frequency": 256}, dataset_key="tuh-v2")
```

## Models (P4-F)

`EEGNet`, `DeepConvNet`, `Temporal CNN`, and `Transformer` are implemented as
**deterministic, pure-NumPy reference baselines** (a fixed seeded front-end transform
+ a softmax head trained by deterministic gradient descent — consistent with the
platform's framework-free V1 approach). Per the directive: **correctness first, no
optimization, no tuning** — they exist to exercise the training/evaluation/registry/
lineage machinery reproducibly, not to maximize accuracy.

## Determinism, immutability & boundaries

* All ids, versions, fingerprints, weights, and metrics are content-derived; training
  is **seeded** so every run is bit-for-bit reproducible (NR-9/NR-10). Determinism is
  *validated* (the service re-trains and asserts identical parameter fingerprints).
* Splits are **patient-disjoint** by construction (NR-3).
* The `ModelRecord` is **immutable** (a frozen dataclass with a content-addressed
  parameter fingerprint — not raw weights).
* Imports `ml` (provenance/lineage/validation) and reuses the audit primitive from
  `backend.clinical_cases.audit` (intra-`backend` reuse). It never imports `frontend`
  and performs **no serving/inference/predictions** (NR-8 / NR-13). Enforced by
  `tests/test_boundaries.py`.

## Verification

```bash
python -m scripts.verify_productization_p4     # the 15 phase-completion criteria
python -m pytest tests/test_model_foundation.py tests/test_model_foundation_e2e.py
```
