# The EEG Data Lifecycle (V1-P1)

Every EDF/EDF+ file entering the repository follows one **deterministic,
validated, traceable** path. This document describes each stage and the artifact
it produces.

```
 ┌────────────┐   detect format + SHA-256        ┌──────────────┐
 │  EDF file  │ ───────────────────────────────► │ Raw EEG File │
 └────────────┘                                  └──────┬───────┘
        unsupported/unknown ──► IngestionError (+ ValidationReport)
                                                        │ read (header + annotations)
                                                        ▼
                                              ┌────────────────────┐
                                              │  Metadata Record   │── derive ─► Patient Record
                                              │  (canonical)       │── derive ─► Recording Session
                                              └─────────┬──────────┘
                                       verify integrity │  run all checks
                                                        ▼
                                              ┌────────────────────┐
                                              │ Validated EEG      │  status: VALIDATED | QUARANTINED
                                              │ Record (+ reports) │  quality: OK | FLAGGED
                                              └─────────┬──────────┘
                                          register      │      record lineage (4-node chain)
                                                        ▼
                                  ┌────────────────────────────────────────┐
                                  │ RecordRegistry (discoverable by id/     │
                                  │ content/patient)  +  LineageTracker     │
                                  └─────────┬────────────────────────────────┘
                                  assign to dataset │
                                                    ▼
                              Dataset Entry → Dataset Manifest (fingerprint)
                                                    ▼
                              Dataset Version (append-only chain) → audit/reproduce
```

## Stage-by-stage

1. **Detect format** (`ingestion.signature.detect_format`). Structural, byte-based.
   EDF / EDF+C / EDF+D proceed; BDF and other magics are `UNSUPPORTED`; anything
   unrecognized is `UNKNOWN`.
2. **Hash + identity** (`_canonical.sha256_file`). The file's SHA-256 yields
   `file_id = edf-<sha[:16]>`; identical bytes ⇒ identical identity (duplicate
   detection).
3. **Read** (`ingestion.edf_reader.read_edf`). Pure-Python decode of header,
   per-channel signals (optional), and EDF+ annotations. Ingestion uses
   `materialize_signals=False` (annotations + metadata without large float arrays).
4. **Extract metadata** (`metadata.extract_metadata`). EDF+ patient/recording
   subfields, dates, channels, reference, annotations → canonical `MetadataRecord`.
   Derives `PatientRecord` and `RecordingSession`.
5. **Verify integrity** (`ingestion.integrity.verify_integrity`). File size vs.
   declared record layout → `IntegrityResult`.
6. **Validate** (`validation.run_all_checks`). Format, integrity, channels,
   sampling, metadata, missing-channels, duplicate → `ValidationReport`.
   `VALIDATED` if no ERROR, else `QUARANTINED` (record retained, never deleted).
7. **Register** (`registry.RecordRegistry`). Indexed by `file_id`,
   `content_sha256` (duplicate detection), and `patient_id` (patient-disjoint).
8. **Lineage** (`lineage.build_ingestion_lineage`). Records the acyclic chain
   raw → validation → metadata → record.
9. **Curate → version** (`versioning`). Build a content-addressed `DatasetManifest`,
   commit it as an immutable `DatasetVersion`, and `audit`/`verify` it later.

## Guarantees enforced at each stage
- **Determinism**: same bytes ⇒ same artifacts (tested in `tests/test_determinism.py`).
- **Traceability**: every artifact reaches the raw file's content hash via lineage.
- **No silent change**: dataset membership is fingerprinted; re-versioning a no-op
  is rejected.
- **Patient safety**: unknown identities never merge (conservative for AP-2/NR-3).
