# Real Dataset Platform — Design (Track 1)

## Objective

Transform the DRP-1 dataset **framework** into a **Real Dataset Platform**: acquire real
public EEG corpora locally, validate them from the **actual files**, extract real metadata +
labels, build inventories, track lineage + audit, and score **training readiness** — proving
at least one real dataset is `READY_FOR_TRAINING` using actual EEG recordings.

## Module map

| Module | Phase | Responsibility |
|---|---|---|
| `version.py` | — | version coordinates + `DETERMINISTIC_EPOCH` |
| `models/domain.py` | T1-B | closed vocabularies + records (acquisition / availability / recording / label / validation / inventory / readiness / dataset / registry / audit / lineage) |
| `identity/` | — | content-addressed `{kind}+{hash16}` ids (source / dataset / patient / session / label / registry) |
| `sources/` | T1-A | acquisition specs for the five mandatory corpora + auto-download policy |
| `acquisition/` | T1-A | the real downloader (stdlib `urllib`) + acquisition records; never fetches approval-gated corpora |
| `storage/` | T1-B | `DatasetStorageManager` / `DatasetLocationRegistry` / `DatasetVerificationManager` / `DatasetAvailabilityTracker` |
| `connectors/` | T1-C | `RealDatasetConnector`, `EdfDirectoryConnector`, `ChbMitConnector` (+ `parse_chb_summary`) — read ACTUAL files via the `eeg_foundation` reader |
| `validation/` | T1-D | `StructureValidator` — 9 structured-finding integrity checks (never raises) |
| `labels/` | T1-E | `LabelVerifier` — coverage / consistency / classes / missing / corrupted / unsupported |
| `inventory/` | T1-F | `InventoryBuilder` — actual dataset/patient/recording/session/label/duration/channel counts |
| `readiness/` | T1-G | `TrainingReadinessEngine` — NOT_READY / PARTIALLY_READY / READY_FOR_TRAINING |
| `audit/` | T1-H | the shared `ImmutableAuditLog` (no parallel system) |
| `lineage/` | T1-H | the shared `ml.lineage` tracker; Source → Dataset → Patient → Recording → Label → Registry |
| `registry/` | T1-F/H | `RealDatasetRegistry` — no orphan records |
| `reports/` | T1-I | 9 deterministic reports |
| `schemas/` | — | a documented contract per entity |
| `service.py` | — | `RealDatasetService` — `acquire` / `integrate` / `reports` / `acquisition_plan` |

## Determinism

Every id, fingerprint, and report is a pure function of the real file checksums + the parsed
content + the labels. Download timings, file mtimes, and durations never enter a hash, so the
same local files reproduce the same `dataset_id`, readiness, reports, and serialized outcome
bit-for-bit (NR-9/NR-10). The only non-deterministic input — *when* a file was downloaded — is
deliberately excluded from every signature.

## Reuse (no parallel systems)

* Real EDF/BDF/FIF/SET reading + recording identity reuse `backend.eeg_foundation`.
* Audit reuses `backend.clinical_cases.audit.ImmutableAuditLog`; lineage reuses
  `ml.lineage.LineageTracker`; validation reports reuse `ml.validation.ValidationReport`;
  hashing reuses `ml.provenance`.
* DRP-1 (`dataset_integration`) is preserved and complementary (manifest inventory + governance
  metadata); Track 1 adds the real-file lifecycle.

## Test strategy

* **Network-free** unit + e2e tests lay out the committed **real EDF fixtures**
  (`tests/fixtures/eeg/valid*.edf`) as a CHB-MIT dataset with a real-format summary, so the
  connector reads genuine EDF bytes and parses real seizure annotations without a network.
* A **real-corpus** test runs over the locally-acquired PhysioNet recordings **when available**
  (skips otherwise), asserting 23 channels and the documented chb01_03 seizure interval.
