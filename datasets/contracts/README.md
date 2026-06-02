# `datasets/contracts/` — Data Contracts (V1-P1)

> **Layer:** Data Access & Curation (`datasets/`) · **Phase:** V1-P1 (EEG Data Foundation)
> **Status:** Authoritative for the *shape and rules* of every data artifact.
> **Code home:** [`datasets/schemas/`](../schemas) (each contract is a frozen dataclass with `to_dict`/`from_dict`).
> **Governing V0 docs:** AP-2 (patient-disjoint), AP-3/AP-6 (determinism/reproducibility), AP-5/AP-8 (traceability/audit), NR-3, NR-8, NR-9, NR-10, NR-11.

A **data contract** is the formal, durable definition of one artifact in the EEG
data lifecycle: its purpose, its required and optional fields, and the rules that
govern its **validation**, **quality**, **versioning**, **lineage**, and
**traceability**. Contracts are the stable interface the rest of the platform
depends on; the *code* in `datasets/schemas/` realizes them, but these documents
**govern intent** (a discrepancy between code and contract is a defect to fix).

## The eight contracts

| # | Contract | Document | Schema class |
|---|----------|----------|--------------|
| 1 | Raw EEG File | [`RAW_EEG_FILE.md`](./RAW_EEG_FILE.md) | `RawEegFile` |
| 2 | Validated EEG Record | [`VALIDATED_EEG_RECORD.md`](./VALIDATED_EEG_RECORD.md) | `ValidatedEegRecord` |
| 3 | Metadata Record | [`METADATA_RECORD.md`](./METADATA_RECORD.md) | `MetadataRecord` |
| 4 | Dataset Entry | [`DATASET_ENTRY.md`](./DATASET_ENTRY.md) | `DatasetEntry` |
| 5 | Patient Record | [`PATIENT_RECORD.md`](./PATIENT_RECORD.md) | `PatientRecord` |
| 6 | Recording Session | [`RECORDING_SESSION.md`](./RECORDING_SESSION.md) | `RecordingSession` |
| 7 | Dataset Manifest | [`DATASET_MANIFEST.md`](./DATASET_MANIFEST.md) | `DatasetManifest` |
| 8 | Dataset Version | [`DATASET_VERSION.md`](./DATASET_VERSION.md) | `DatasetVersion` |

## Lifecycle (how the contracts relate)

```
  Raw EEG File ──(detect format + hash)──┐
                                         ▼
                            read + extract -> Metadata Record
                                         │
                                         ├── derive ──► Patient Record
                                         ├── derive ──► Recording Session
                                         ▼
                            validate + quality -> Validated EEG Record
                                         │
                                         ├── assign ──► Dataset Entry  (membership)
                                         ▼
                          collect entries -> Dataset Manifest (content fingerprint)
                                         ▼
                          certify snapshot -> Dataset Version (append-only chain)
```

## Cross-contract conventions

- **Determinism (AP-3 / NR-9).** Every artifact is a pure function of its inputs.
  Identifiers and fingerprints are content-derived; identical bytes always yield
  identical artifacts.
- **Timestamps are provenance, not identity.** Any `*_at` / `*_iso` "now"
  timestamp is **caller-supplied** and **excluded from fingerprints**, so
  reproducibility never depends on the wall clock (AP-6 / NR-10).
- **Patient identity is sacred (AP-2 / NR-3).** A patient is anchored once; when
  identity is absent it is treated as a *distinct* patient (conservative — never
  merges, never leaks).
- **Report, never mutate.** Validation/quality produce evidence; they never alter
  or drop data.
- **Traceability (AP-5 / NR-11).** Every artifact is reachable in the lineage DAG
  back to the raw file's content hash.

## Future extension points (documented, not built — NR-13)

- Additional input formats beyond EDF/EDF+ attach at `datasets/ingestion` behind
  the same `RawEegFile` + `MetadataRecord` contracts (see
  [`../docs/EXTENSION_POINTS.md`](../docs/EXTENSION_POINTS.md)).
- Site/montage metadata for domain-shift analysis (AP-10) extends
  `MetadataRecord.extra` and `RecordingSession` without reshaping the contracts.
