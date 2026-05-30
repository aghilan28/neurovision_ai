# `backend/eeg_foundation/` — Real EEG Foundation Layer (Productization P1)

> **Layer:** Application (`backend/`) · **Status:** Implemented (Productization P1).
> **Decision record:** [`../../.gcc/decisions/ADR-0014`](../../.gcc/decisions/ADR-0014-productization-p1-real-eeg-foundation.md)
> **Governing docs:** AP-5/AP-8/NR-11 (traceability/audit), AP-6/NR-10 (reproducibility),
> AP-7/NR-8 (boundaries)

Turns NeuroVision from a synthetic-data platform into one that can accept a **real
EEG file**. The scope is deliberately narrow — a real recording can:

    enter → be loaded → validated → parsed → have metadata extracted →
    become a NeuroVision EEG asset → be stored → tracked (lineage + audit) →
    reported on

…and **nothing more**. There is no signal filtering, artifact removal, feature
extraction, model training, inference, analytics, API, dashboard, or deployment in
this layer (all explicitly out of scope for this phase).

An EEG asset attaches to the existing clinical **Case**, so the platform-wide chain
is:

    Patient → Case → EEG Asset

---

## Supported formats (closed vocabulary)

`EDF` · `EDF+` · `BDF` · `BDF+` · `FIF` · `SET` — and no others.

Real files are read with **[MNE-Python](https://mne.tools/)** (`mne==1.12.1`), the
industry-standard EEG reader (`scipy` is required for the EEGLAB `.set` container).
There are **no mock files, synthetic placeholders, or hand-rolled parsers** in the
ingestion path. The precise format (e.g. EDF vs EDF+) is determined by inspecting
the file's bytes, not by trusting the extension.

## Subsystems

| Subsystem | Role |
|-----------|------|
| `models/` | Domain entities + closed vocabularies (`EEGFormat`, `EEGChannelType`, `EEGAssetStatus`, `EEGValidationSeverity`, `EEGIdentity`, `EEGRecord`, `EEGMetadata`, `EEGSource`, `EEGChannel`, `EEGChannelSet`, `EEGAnnotation`, `EEGStorageRecord`, `EEGAuditRecord`, `EEGLineageRecord`, `EEGRegistryRecord`). |
| `identity/` | Deterministic, content-addressed `eeg+{hash16}` ids derived from a case + the file's content fingerprint (never the filename). |
| `ingestion/` | Magic-byte format detection + real MNE loaders. `load_eeg()` never raises — a bad file becomes a `ParsedEEG(parse_ok=False)`. |
| `validation/` | `EEGFileValidator` → structured findings (never exceptions); `EEGIntegrityValidator` → asset-integrity checks reusing `ml.validation.ValidationReport`. |
| `metadata/` | Deterministic normalized metadata, stored independently of the raw bytes. |
| `storage/` | `LocalEEGStore` — content-addressed local storage with checksum + fingerprint + integrity verification (no cloud/S3/db). |
| `registry/` | `EEGRegistry` — no asset exists outside it; silent overwrite of a version is rejected. |
| `audit/` | Reuses the platform's single tamper-evident `ImmutableAuditLog` bound to `EEGAuditRecord` (no parallel audit). |
| `lineage/` | EEG lineage nodes on the shared `ml.lineage.LineageTracker`, parented on the case node (no parallel lineage). |
| `reports/` | Summary / metadata / validation / audit / lineage / registry reports (deterministic). |
| `schemas/` | Per-entity contracts: Schema · Version · Validation/Lineage/Audit rules. |
| `service.py` | `EEGFoundationService` — the governed orchestration hub. |

> **Tests & fixtures** live in the repository-root `tests/` (`tests/test_eeg_foundation*.py`,
> fixtures in `tests/fixtures/eeg/`), matching the established platform convention
> (e.g. `clinical_cases`). Design notes are in `docs/`.

## The single use case

```python
from ml.lineage import LineageTracker
from backend.clinical_cases import CaseService
from backend.eeg_foundation import EEGFoundationService, LocalEEGStore

tracker = LineageTracker()                       # one shared platform lineage graph
cases = CaseService(lineage_tracker=tracker)
case = cases.create_case(patient_key="P-001", case_key="C-001")

eeg = EEGFoundationService(LocalEEGStore("/var/lib/neurovision/eeg"), lineage_tracker=tracker)
outcome = eeg.ingest_eeg(
    "recording.edf",
    case_id=case.case_id, patient_id=case.patient_id, case_lineage_id=case.lineage_id,
)
assert outcome.accepted
asset = outcome.asset                            # a registered NeuroVision EEG asset
assert tracker.verify_chain(asset.lineage_id)    # Patient → Case → EEG verifies
```

For every accepted file the governed flow is:

    load (real parse) → validate (structured findings) → extract metadata →
    store (content-addressed) → mint identity → record lineage (parented on the
    case) → append immutable audit events → bump version → sync registry

* A **valid** file becomes a `REGISTERED` asset.
* A file that is **recognized but undecodable** (corrupted) becomes a `QUARANTINED`
  asset — still identified, stored, audited, and lineage-tracked, with a CRITICAL
  validation finding explaining why.
* An **unreadable / unsupported** file is **rejected** (no asset) but always returns
  its structured validation findings; nothing fails silently.

## Determinism & boundaries

* All ids, versions, fingerprints, recording ids, and report contents are
  content-derived; no wall-clock or randomness enters a hash (AP-6 / NR-10). The
  same bytes under the same case always yield the same `asset_id`.
* Imports `ml` (provenance/lineage/validation) and reuses the audit primitive from
  `backend.clinical_cases.audit` (intra-`backend` reuse). It never imports
  `frontend` and performs no modelling/inference/DSP (NR-8 / NR-13). Enforced by
  `tests/test_boundaries.py`.

## Verification

```bash
python -m scripts.verify_productization_p1   # the 15 phase-completion criteria
python -m pytest tests/test_eeg_foundation.py tests/test_eeg_foundation_e2e.py
```
