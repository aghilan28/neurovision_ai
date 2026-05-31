# ADR-0030 — Track 1: Real Data Acquisition & Integration Program

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Product Completion Program — Track 1 (Real Data Acquisition & Integration)
> **Builds on:** ADR-0001 … ADR-0029 (Productization P1–P10 + DRP-1 … DRP-6)
> **Resolves:** Production Reality Audit V2 blocker — *NO REAL DATASETS* (the dataset
> framework existed, but no recordings/labels were actually present or usable for training)
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-5/AP-8/NR-11 (traceability),
> AP-7/NR-8 (boundaries), NR-6 (reuse, no parallel systems), AP-9/NR-5 (this record),
> NR-13 (scope), NR-2 (honesty)

## 1. Context

DRP-1 (ADR-0024) delivered the dataset **framework** — inventory, registry, validation,
governance, readiness — but **from manifests only (never downloaded)**. The Production
Reality Audit V2 confirmed the framework exists yet **datasets are not downloaded, real
recordings/labels do not exist, and no dataset can be used for training**.

Track 1 closes that blocker by turning the *dataset framework* into a **Real Dataset
Platform**: acquire real public EEG corpora locally, validate them from the **actual files**
(not manifests), extract real metadata + labels, build inventories, track lineage + audit,
and score **training readiness**. Scope is strictly real-data integration — no model
training/tuning, inference, serving, persistence, security, frontend, or deployment changes
(NR-13).

## 2. Decisions

### D1 — A new governed `backend/dataset_acquisition` subsystem (not a DRP-1 rewrite)
DRP-1 (`dataset_integration`) is preserved and used; Track 1 adds a sibling subsystem that
operates on **real local files**. It mirrors the platform subsystem shape (models, identity,
sources, acquisition, storage, connectors, validation, labels, inventory, readiness, registry,
audit, lineage, reports, schemas, service). As a `backend` package it obeys the import DAG
(imports `ml` + sibling `backend`, never `frontend`; enforced by `tests/test_boundaries.py`).

### D2 — Real-file reading reuses `eeg_foundation` (no parallel parser)
Recordings are read from the **actual files** via the platform's real MNE reader
(`eeg_foundation.ingestion.reader.load_eeg`) and identified with its content-addressed
`recording+{hash16}` id (`metadata.extractor.compute_recording_id`). Connectors enumerate
recordings / channels / sampling / duration / patient / session from the real bytes — never a
manifest. `ChbMitConnector` additionally parses the real `chbNN-summary.txt` seizure
annotations; a generic `EdfDirectoryConnector` handles any EDF tree.

### D3 — Acquisition policy: OPEN only; approval-gated corpora are reported, never downloaded
`sources/` carries the acquisition spec (official source / mechanism / access / license /
storage / directory structure / expected labels / expected metadata) for all five mandatory
corpora. Only OPEN, no-account corpora are auto-downloadable. **CHB-MIT** (PhysioNet, Open
Data Commons) is the proof corpus, acquired over HTTPS via stdlib `urllib`. **TUH EEG** and
**Temple/TUSZ** require a signed data-use agreement → their plan is reported, never fetched.
**Siena** is open but large (not auto-fetched by default); **Bonn** is open but its public
mirror is currently unavailable. Real recordings are acquired into a **gitignored** data root
(`data/real`, `$NV_DATASET_ROOT`) — never committed (size + redistribution).

### D4 — `READY_FOR_TRAINING` readiness with a hard, label-aware gate
A new classification extends DRP-1: **NOT_READY < PARTIALLY_READY < READY_FOR_TRAINING**.
Six weighted dimensions (acquisition / validation / labels / metadata / registry / training).
`READY_FOR_TRAINING` requires the files to physically exist + verify, structure validation to
pass, **real labels** with coverage 1.0 + consistent + ≥2 classes, complete metadata, the
dataset registered + traceable, and channel/sampling train-consistency — i.e. usable for
training **without synthetic labels**.

### D5 — Reuse the shared audit + lineage (no parallel systems)
Acquire/track/connect/validate/label/inventory/score/register events are appended to the
shared hash-chained `ImmutableAuditLog`; lineage nodes are recorded in the single
`ml.lineage` tracker, realizing **Dataset Source → Dataset → Patient → Recording → Label →
Registry** (one `verify_chain` from the registry node reaches the source).

### D6 — Determinism (NR-9/NR-10)
Ids/fingerprints are content-addressed from **real file checksums + labels**; download timing,
file mtimes, and durations are never hashed. The same local files reproduce the same dataset
id, readiness, reports, and serialized outcome bit-for-bit.

## 3. Consequences

- `python -m scripts.verify_track1_real_data` → **ALL 15 CRITERIA PASS** against a **real,
  locally-acquired CHB-MIT subset** (the script acquires the minimal real subset if missing).
  Proof: 2 genuine 1-hour recordings (256 Hz, 23 bipolar channels), **real** labels from the
  actual summary (`chb01_01`=background, `chb01_03`=seizure at the documented **2996–3036 s**),
  coverage 1.0, 2 classes, lineage + audit verified, registry orphan-free, **READY_FOR_TRAINING**.
- New suite adds **25 tests**; full repository suite **967 passed** (was 942). Tests run
  **network-free** by laying out the committed real EDF fixtures as a CHB-MIT dataset; a
  real-corpus test runs over the genuine PhysioNet recordings **when available**.
- `ruff` clean on all new code; `tests/test_boundaries.py` green; prior verify scripts
  (DRP-1 … DRP-6, productization) unaffected. No new runtime dependencies (`urllib` is stdlib).
- A CLI (`python -m scripts.acquire_real_dataset`) acquires a corpus + reports its readiness.

## 4. Scope guard (explicitly NOT built — NR-13)

Model training/tuning, inference changes, serving changes, persistence changes, security
changes, frontend changes, deployment changes, DRP-system changes. Track 1 acquires,
validates, registers, verifies, and prepares datasets for training — **only**.

## 5. Honesty statement (NR-2)

Track 1 delivers a **real** dataset platform and a **genuinely real** READY_FOR_TRAINING
dataset: the CHB-MIT recordings are the actual PhysioNet EDF files and the labels are the
actual seizure annotations parsed from the real summary — **no synthetic labels** for that
dataset. The acquired subset is a **single subject** (chb01, the minimal verifiable subset);
acquiring additional subjects/corpora is the same governed flow over more `sample_files` or a
larger `NV_DATASET_ROOT`. TUH/Temple require a signed agreement and are intentionally not
auto-downloaded; Bonn's public mirror is currently unavailable. This closes the *no real
datasets* blocker: NeuroVision can now discover, validate, label, inventory, trace, and score
the training readiness of **actual EEG recordings** rather than synthetic fixtures.
