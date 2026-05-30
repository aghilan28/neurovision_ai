# `backend/signal_processing/` — Signal Processing Foundation (Productization P2)

> **Layer:** Application (`backend/`) · **Status:** Implemented (Productization P2).
> **Decision record:** [`../../.gcc/decisions/ADR-0015`](../../.gcc/decisions/ADR-0015-productization-p2-signal-processing.md)
> **Builds on:** Productization P1 ([`../eeg_foundation/`](../eeg_foundation/README.md)).
> **Governing docs:** AP-5/AP-8/NR-11 (traceability/audit), AP-6/NR-10 (reproducibility),
> AP-7/NR-8 (boundaries)

Transforms a **raw EEG asset** (produced by Productization P1) into a **validated
clean EEG asset**. The scope is *signal quality* and nothing else:

    load raw (read-only) → assess quality → detect artifacts → filter +
    remove artifacts → generate clean EEG → store → track (lineage + audit) →
    report on

There is **no AI, model training, inference, classification, prediction, or clinical
decision** in this layer (all out of scope for this phase).

This layer is built **strictly on P1**: it reads the immutable raw EEG bytes from the
P1 store and references the P1 `EEGRecord`; it never redesigns, replaces, or
duplicates the EEG Foundation. The **raw EEG is never modified** — the cleaned signal
is written to a *separate* content-addressed store, and the processed asset's lineage
parents the raw EEG node, so the platform-wide chain is:

    Patient → Case → EEG Asset → Processed EEG

---

## Subsystems

| Subsystem | Role |
|-----------|------|
| `models/` | Domain entities + closed vocabularies (`SignalKind`, `FilterType`, `ArtifactType`, `RemovalMethod`, `ArtifactSeverity`, `QualityFindingSeverity`, `QualityGrade`, `ProcessedAssetStatus`) + `SignalRecord`, `SignalQualityRecord`, `SignalArtifactRecord`, `SignalProcessingRecord`, histories, `ProcessedEEGRecord`, …). |
| `identity/` | Deterministic `signal+{hash16}` ids derived from the raw `eeg` asset id + the processing fingerprint (never filename-derived). |
| `filtering/` | `FilteringEngine` — deterministic, zero-phase scipy filters: bandpass / highpass / lowpass / notch / reference correction. Each returns a new array + its tracked `FilterConfig`. |
| `quality/` | `SignalQualityEngine` — deterministic channel/recording quality, noise, stability, completeness, sampling consistency, scores, grade, findings, recommendations. |
| `artifacts/` | `ArtifactDetectionEngine` (eye-blink, EMG, movement, powerline, channel dropout, flat/saturated channels → structured `SignalArtifactRecord`s) + `ArtifactRemovalEngine` (ICA, adaptive filtering, interpolation, channel repair, noise suppression). |
| `preprocessing/` | Raw-signal loading (via MNE from the P1 store) + deterministic fingerprints/serialization + the `ProcessingPipeline` (raw → clean). |
| `storage/` | `ProcessedSignalStore` — content-addressed local store for the cleaned signal (checksum + fingerprint + integrity verify). Separate from the raw store. |
| `registry/` | `SignalRegistry` — no processed asset exists outside it; silent overwrite rejected. |
| `audit/` | Reuses the platform's single tamper-evident `ImmutableAuditLog` bound to `SignalAuditRecord` (no parallel audit). |
| `lineage/` | Processed-EEG lineage nodes on the shared `ml.lineage.LineageTracker`, parented on the raw EEG node (no parallel lineage). |
| `reports/` | Quality / artifact / filtering / processing / registry / audit / lineage reports (deterministic). |
| `schemas/` | Per-entity contracts: Schema · Version · Validation/Lineage/Audit rules. |
| `validation/` | `SignalIntegrityValidator` — identity/registry/storage/quality/processing-traceability/artifact/audit/lineage/version checks **plus raw-immutability**. |
| `service.py` | `SignalProcessingService` — the governed orchestration hub. |

> **Tests & fixtures** live in the repository-root `tests/`
> (`tests/test_signal_processing*.py`) and **reuse the P1 EEG fixtures** in
> `tests/fixtures/eeg/` (no synthetic replacement fixtures). Design notes are in `docs/`.

## The single use case

```python
from ml.lineage import LineageTracker
from backend.clinical_cases import CaseService
from backend.eeg_foundation import EEGFoundationService, LocalEEGStore
from backend.signal_processing import SignalProcessingService, ProcessedSignalStore

tracker = LineageTracker()                       # one shared platform lineage graph
case = CaseService(lineage_tracker=tracker).create_case(patient_key="P-1", case_key="C-1")

eeg = EEGFoundationService(LocalEEGStore("/var/lib/nv/raw"), lineage_tracker=tracker)
raw_asset = eeg.ingest_eeg("recording.edf", case_id=case.case_id,
                           patient_id=case.patient_id, case_lineage_id=case.lineage_id).asset

sig = SignalProcessingService(eeg.store, ProcessedSignalStore("/var/lib/nv/processed"),
                              lineage_tracker=tracker)
outcome = sig.process(raw_asset)                 # raw → clean
clean = outcome.asset                            # a registered processed-EEG asset
assert tracker.verify_chain(clean.lineage_id)    # Patient → Case → EEG → Processed verifies
```

For every processed asset the governed flow is:

    load raw (read-only) → quality (before) → detect artifacts → deterministic
    cleaning pipeline → quality (after) → mint identity → store clean signal →
    record lineage (parented on the raw EEG node) → append immutable audit events →
    bump version → sync registry

The default cleaning pipeline always applies a bandpass and a powerline notch, and
**conditionally** applies channel repair / ICA / adaptive filtering / noise
suppression when the corresponding artifact is detected. (Average re-referencing is a
supported, tested filter but is *not* applied by default, as it is montage-dependent.)

## Determinism, immutability & boundaries

* All ids, versions, fingerprints, processing steps, and report contents are
  content-derived; no wall-clock or randomness enters a hash (AP-6 / NR-10). The ICA
  is a self-contained FastICA with a fixed initialization, so the whole pipeline is
  bit-for-bit reproducible.
* The **raw EEG is immutable**: this layer only *reads* the P1 store and writes the
  cleaned signal to a separate store. `SignalIntegrityValidator` asserts raw
  immutability and full raw → processed traceability.
* Imports `ml` (provenance/lineage/validation), `backend.eeg_foundation` types, and
  reuses the audit primitive from `backend.clinical_cases.audit` (intra-`backend`
  reuse). It never imports `frontend` and performs no feature extraction, modelling,
  inference, or classification (NR-8 / NR-13). Enforced by `tests/test_boundaries.py`.

## Verification

```bash
python -m scripts.verify_productization_p2     # the 15 phase-completion criteria
python -m pytest tests/test_signal_processing.py tests/test_signal_processing_e2e.py
```
