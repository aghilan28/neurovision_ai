# Real Dataset Platform (`backend/dataset_acquisition`) — Track 1

Closes the Production Reality Audit V2's **#1 blocker — "NO REAL DATASETS."** It turns the
DRP-1 dataset *framework* into a **Real Dataset Platform**: it **acquires** real public EEG
corpora locally, **validates** them from the **actual files** (not manifests), extracts
**real metadata + labels**, builds inventories, tracks lineage + audit, and scores **training
readiness**.

It **acquires / validates / registers / verifies / prepares datasets for training** — and
nothing more. It trains no models and modifies no other subsystem.

## What it does (and does not)

* **Does:** acquire OPEN corpora on demand (PhysioNet over HTTPS, no account); track the real
  local state of files (downloaded / partial / unavailable / corrupted / verified / ready);
  read recordings from the **actual files** via the `eeg_foundation` MNE reader; extract real
  channels / sampling / duration / patient / session / labels; validate directory / file /
  metadata / label / recording / patient / session / channel / sampling integrity; verify
  labels (coverage / consistency / classes / missing / corrupted / unsupported); build
  inventories; score training readiness; track lineage + audit; emit deterministic reports.
* **Does not:** train or tune models; run inference; change serving / persistence / security /
  frontend / deployment; auto-download corpora that require an account or a signed data-use
  agreement (TUH EEG, Temple/TUSZ) — those are *reported*, never fetched.

## Acquisition — mandatory corpora

| Source | Access | Auto-download | Format | Labels |
|---|---|---|---|---|
| **CHB-MIT** | open (PhysioNet) | ✅ yes (proof corpus) | EDF, 256 Hz, 23 ch | seizure intervals (`chbNN-summary.txt`) |
| Siena Scalp | open (PhysioNet) | ➖ (open, large) | EDF, 512 Hz | seizure intervals |
| TUH EEG | data-use agreement | ❌ reported only | EDF | term/event annotations |
| Temple/TUSZ | data-use agreement | ❌ reported only | EDF | binary seizure (`.csv_bi`) |
| Bonn | open (mirror down) | ❌ reported only | ASCII, 173.61 Hz | set membership |

Real recordings are acquired into a **gitignored** data root (`data/real`, override with
`$NV_DATASET_ROOT`) — never committed (size + redistribution).

## Pipeline (T1-A … T1-K)

```
acquire (OPEN only)        # sources/ + acquisition/ (urllib; never fetches approval-gated corpora)
  -> track availability    # storage/ (StorageManager, LocationRegistry, VerificationManager, AvailabilityTracker)
  -> connect ACTUAL files  # connectors/ (ChbMitConnector + EdfDirectoryConnector; reuses eeg_foundation reader)
  -> validate structure    # validation/ (9 structured checks, never raises)
  -> verify labels         # labels/ (coverage / consistency / classes / missing / corrupted / unsupported)
  -> build inventory       # inventory/ (actual counts)
  -> lineage + registry + audit   # lineage/ + registry/ + audit/ (shared systems, no parallel)
  -> score training readiness     # readiness/ (NOT_READY / PARTIALLY_READY / READY_FOR_TRAINING)
  -> reports               # reports/ (9 deterministic reports)
```

## Lineage (required chain)

```
Dataset Source -> Dataset -> Patient -> Recording -> Label -> Registry
```

One `verify_chain` from the registry node reaches the source. Audit is the shared
hash-chained `ImmutableAuditLog`; lineage is the single `ml.lineage` tracker — no parallel
systems.

## Readiness

`READY_FOR_TRAINING` requires: files present + verified, structure valid, **real labels**
(coverage 1.0, consistent, ≥2 classes), complete metadata, registered + traceable, and
channel/sampling train-consistency — i.e. trainable **without synthetic labels**.

## Run it

```bash
# acquire the real CHB-MIT subset (PhysioNet, no account) + report readiness
python -m scripts.acquire_real_dataset --source chb_mit

# the 15 final-validation criteria against the real corpus
python -m scripts.verify_track1_real_data            # NV_TRACK1_NO_DOWNLOAD=1 forbids network

# tests (network-free; uses the committed real EDF fixtures laid out as CHB-MIT)
python -m pytest tests/test_dataset_acquisition.py tests/test_dataset_acquisition_e2e.py
```

## Boundary

Imports `ml` + sibling `backend` (`eeg_foundation`, `clinical_cases.audit`) only — never
`frontend` (enforced by `tests/test_boundaries.py`). Determinism: ids/fingerprints are
content-addressed from real file checksums + labels; download timings are never hashed.

See [`docs/DESIGN.md`](./docs/DESIGN.md) and [`docs/DECISIONS.md`](./docs/DECISIONS.md), and
the decision record [`ADR-0030`](../../.gcc/decisions/ADR-0030-track1-real-data-acquisition.md).
