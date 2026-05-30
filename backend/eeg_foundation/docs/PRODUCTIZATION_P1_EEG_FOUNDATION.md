# Productization P1 — Real EEG Foundation (design & contracts)

> **Phase:** Productization P1 · **Status:** Implemented
> **Decision record:** [`../../../.gcc/decisions/ADR-0014`](../../../.gcc/decisions/ADR-0014-productization-p1-real-eeg-foundation.md)

The objective is narrow and concrete: a **real EEG file** can enter the platform,
be understood, validated, and stored, and become a traceable NeuroVision **EEG
asset** under a clinical Case. No DSP, features, models, inference, analytics, APIs,
or deployment (forbidden in this phase).

---

## 1. Supported formats (closed vocabulary)

`EDF`, `EDF+`, `BDF`, `BDF+`, `FIF`, `SET` — read with MNE-Python. The exact format
is detected from the file's **bytes**, not its extension:

| format | detection signature | reader |
|--------|--------------------|--------|
| EDF    | 8-byte version field is ASCII `0` | `mne.io.read_raw_edf` |
| EDF+   | …and the reserved field starts `EDF+C`/`EDF+D` | `mne.io.read_raw_edf` |
| BDF    | byte 0 = `0xFF` then `BIOSEMI` | `mne.io.read_raw_bdf` |
| BDF+   | …and the reserved field starts `BDF+C`/`BDF+D` | `mne.io.read_raw_bdf` |
| FIF    | first FIFF tag kind = 100 (`FIFF_FILE_ID`) | `mne.io.read_raw_fif` |
| SET    | MATLAB v5 (`MATLAB 5.0`) or v7.3 (HDF5 magic) | `mne.io.read_raw_eeglab` |

## 2. Identity model

An EEG asset id is `"eeg+{hash16}"`, a content hash of `(kind, identity_version,
{case_id, eeg_key})` where `eeg_key` is the file's content fingerprint (first 16
hex of its sha256). Properties: **stable · deterministic · collision-resistant ·
versioned · traceable** (`derived_from = case_id`). The id is **content-derived,
never filename-derived**, so the same recording under the same case is always the
same asset, and a renamed/moved file is recognized as identical.

| kind | components | parent | minted here |
|------|-----------|--------|-------------|
| eeg | case_id, eeg_key | case | yes |
| case | patient_id, case_key | patient | no (validated only) |
| patient | patient_key | — | no (validated only) |

## 3. Ingestion (real files, never raises)

`load_eeg(path)` returns a `ParsedEEG`. It extracts: file size, format, channel
count, sampling frequency, duration, channel names + normalized types, annotations,
recording start time, de-identified patient identifier (if present), and the
source-reported acquisition metadata. A corrupted/unreadable/unsupported file does
**not** raise — it returns `parse_ok=False` with an `error`, so validation can turn
it into a structured finding.

## 4. Validation (structured findings, not exceptions)

`EEGFileValidator.validate(parsed)` → `EEGValidationResult` (a tuple of
`EEGValidationFinding` with `INFO/WARNING/ERROR/CRITICAL` severity). It detects the
mandated conditions: corrupted files, unreadable files, unsupported formats,
missing channels, invalid sampling rates, invalid durations, metadata errors, and
annotation errors. `ok` is true iff there is no blocking (ERROR/CRITICAL) finding.

`EEGIntegrityValidator` separately checks a *built* asset (identity, registry,
validation-state, storage, metadata, audit, lineage, version) reusing
`ml.validation.ValidationReport` so the result shape matches the rest of the
platform.

## 5. Metadata (deterministic, stored independently)

`extract_metadata(parsed)` → `EEGMetadata`: recording id (content-addressed),
optional patient identifier, acquisition date, duration, sampling frequency,
channel layout + labels, annotation count + types, and the available source
metadata. It is a pure function of the parsed file (same file → same metadata and
the same `metadata_signature`). It contains no raw signal.

## 6. Storage (local, content-addressed; no cloud)

`LocalEEGStore` copies the raw bytes to `<root>/<content_fingerprint>/<name>` and
records an `EEGStorageRecord` (storage id, raw file reference, full sha256 checksum,
fingerprint, size, version, lineage refs). `verify()` re-reads the stored bytes to
detect silent modification. No S3/cloud/database/deployment — just correct
architecture behind the `EEGStorageRecord` contract.

## 7. Registry (no orphans)

`EEGRegistry` holds the latest record per `asset_id`, tracking format, status,
validation/storage/metadata state, audit head, and lineage id. A new *version* is
an update; re-registering the *same* version with different content is a forbidden
silent overwrite.

## 8. Audit & lineage (reused, not duplicated)

Audit reuses the platform's single hash-chained `ImmutableAuditLog` (bound to
`EEGAuditRecord`); every ingestion/validation/metadata/storage/lineage/version/
registration step is appended immutably. Lineage reuses the shared
`ml.lineage.LineageTracker`: the EEG node parents the **case** node, so a single
`verify_chain(asset.lineage_id)` proves:

    Patient → Case → EEG Asset

## 9. Asset status

`REGISTERED` (validation ok) or `QUARANTINED` (a recognized file with a blocking
finding — still identified, stored, audited, and traced). Unreadable/unsupported
inputs are rejected before an asset exists (findings still returned). No workflow
or lifecycle beyond this is built in this phase.

## 10. Out of scope (forbidden in P1)

Signal filtering, artifact removal, feature extraction, model training, inference,
predictions, clinical analytics, FastAPI, PostgreSQL, Redis, authentication,
frontend, Docker/Kubernetes, deployment, monitoring, Version 5, and any later
productization phase.
