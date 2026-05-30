# `backend/feature_engineering/` — Feature Engineering Platform (Productization P3)

> **Layer:** Application (`backend/`) · **Status:** Implemented (Productization P3).
> **Decision record:** [`../../.gcc/decisions/ADR-0016`](../../.gcc/decisions/ADR-0016-productization-p3-feature-engineering.md)
> **Builds on:** Productization P1 ([`../eeg_foundation/`](../eeg_foundation/README.md)) + P2 ([`../signal_processing/`](../signal_processing/README.md)).
> **Governing docs:** AP-5/AP-8/NR-11 (traceability/audit), AP-6/NR-10 (reproducibility), AP-7/NR-8 (boundaries)

Transforms a **processed (clean) EEG asset** (from Productization P2) into an
**immutable validated feature asset**. The scope is *feature generation* and nothing
else:

    load processed (read-only) → generate features → validate → create feature
    asset → track (lineage + audit) → report on

There is **no model training, model registry, inference, prediction, classification,
or clinical decision** in this layer (all out of scope for this phase).

Built **strictly on P1 + P2**: it reads the immutable processed-signal bytes from the
P2 store and references the P2 `ProcessedEEGRecord`; it never redesigns, replaces, or
duplicates the EEG Foundation or Signal Processing layers. The feature asset's lineage
parents the processed-EEG node, so the platform-wide chain is:

    Patient → Case → EEG Asset → Processed EEG → Feature Asset

---

## Feature families & groups

| Family | Engine | Feature groups |
|--------|--------|----------------|
| **frequency** | `frequency/` | band power (δ/θ/α/β/γ + total), relative power, band ratios, spectral entropy |
| **temporal** | `temporal/` | statistical (mean/var/skew/kurtosis/RMS/ZCR), Hjorth (activity/mobility/complexity), signal entropy — per-channel + per-recording |
| **connectivity** | `connectivity/` | coherence matrix, PLV matrix, cross-correlation matrix, synchronization summary |
| **spectral** | `spectral/` | PSD, spectrogram, band summaries, frequency histogram (structured, **no images**) |
| **topography** | `topography/` | channel-layout model, regional groups, spatial summaries, topographic statistics (structured, **no images**) |

All features are deterministic pure-NumPy/SciPy functions of the processed signal.

## Subsystems

| Subsystem | Role |
|-----------|------|
| `models/` | Domain entities + closed vocabularies (`FeatureFamily`, `FeatureGroup`, `FeatureScope`, `FrequencyBand`, `FeatureAssetStatus`) + `FeatureVector`, `FeatureGroupRecord`, `FeatureMetadata`, `FeatureValidationRecord`, `FeatureRegistryRecord`, the immutable `FeatureRecord` asset, … |
| `identity/` | Deterministic `feature+{hash16}` ids derived from the processed `signal` id + the extraction fingerprint (never filename-derived). |
| `frequency/` `temporal/` `connectivity/` `spectral/` `topography/` | The five deterministic feature engines. |
| `loader.py` | Reads the processed signal array from the P2 store (read-only) + fingerprints. |
| `registry/` | `FeatureRegistry` — no feature asset exists outside it; silent overwrite rejected. |
| `validation/` | `FeatureContentValidator` (completeness/integrity/consistency/determinism) + `FeatureIntegrityValidator` (the full 8 checks, reusing `ml.validation.ValidationReport`). |
| `audit/` | Reuses the shared tamper-evident `ImmutableAuditLog` bound to `FeatureAuditRecord` (no parallel audit). |
| `lineage/` | Feature lineage nodes on the shared `ml.lineage.LineageTracker`, parented on the processed-EEG node (no parallel lineage). |
| `reports/` | Frequency / temporal / connectivity / spectral / topography / registry / audit / lineage / validation reports (deterministic). |
| `schemas/` | Per-entity contracts: Schema · Version · Validation/Lineage/Audit rules. |
| `service.py` | `FeatureEngineeringService` — the governed orchestration hub. |

> **Tests & fixtures** live in the repository-root `tests/`
> (`tests/test_feature_engineering*.py`) and **reuse the P1/P2 assets** + the P1 EEG
> fixtures in `tests/fixtures/eeg/` (no replacement systems). Design notes are in `docs/`.

## The single use case

```python
from ml.lineage import LineageTracker
from backend.clinical_cases import CaseService
from backend.eeg_foundation import EEGFoundationService, LocalEEGStore
from backend.signal_processing import SignalProcessingService, ProcessedSignalStore
from backend.feature_engineering import FeatureEngineeringService

tracker = LineageTracker()
case = CaseService(lineage_tracker=tracker).create_case(patient_key="P-1", case_key="C-1")
eeg = EEGFoundationService(LocalEEGStore("/var/lib/nv/raw"), lineage_tracker=tracker)
raw = eeg.ingest_eeg("recording.edf", case_id=case.case_id, patient_id=case.patient_id,
                     case_lineage_id=case.lineage_id).asset
sig = SignalProcessingService(eeg.store, ProcessedSignalStore("/var/lib/nv/proc"), lineage_tracker=tracker)
processed = sig.process(raw).asset

feat = FeatureEngineeringService(sig.processed_store, lineage_tracker=tracker)
outcome = feat.generate_features(processed)          # processed → features
asset = outcome.asset                                # an immutable feature asset
assert tracker.verify_chain(asset.lineage_id)        # Patient → Case → EEG → Processed → Feature verifies
```

## Determinism, immutability & boundaries

* All ids, versions, fingerprints, feature values, and report contents are
  content-derived; no wall-clock or randomness enters a hash (AP-6 / NR-10). The
  service re-extracts features a second time and asserts identical fingerprints
  (the `feature_determinism` validation check).
* The **feature asset is immutable** (a frozen dataclass with content fingerprints);
  the processed signal is read-only. `FeatureIntegrityValidator` asserts the eight
  mandated checks (completeness/integrity/consistency/determinism + registry/audit/
  lineage/version).
* Imports `ml` (provenance/lineage/validation), reads the P2 store, and reuses the
  audit primitive from `backend.clinical_cases.audit` (intra-`backend` reuse). It
  never imports `frontend` and performs no model training/inference/classification
  (NR-8 / NR-13). Enforced by `tests/test_boundaries.py`.

## Verification

```bash
python -m scripts.verify_productization_p3     # the 15 phase-completion criteria
python -m pytest tests/test_feature_engineering.py tests/test_feature_engineering_e2e.py
```
