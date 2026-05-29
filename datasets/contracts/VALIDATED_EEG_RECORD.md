# Contract 2 — Validated EEG Record

> Schema: [`datasets/schemas/validated_record.py`](../schemas/validated_record.py) → `ValidatedEegRecord`

## Purpose
The lifecycle's **central composite artifact** for a single file: it binds the raw
file, its canonical metadata, derived patient/session, and its validation & quality
reports into one fully-traceable record. It is the unit a dataset is built from.

## Required fields
| Field | Type | Meaning |
|-------|------|---------|
| `raw_file` | `RawEegFile` | Content identity. |
| `metadata` | `MetadataRecord` | Canonical metadata. |
| `patient` | `PatientRecord` | Patient identity (AP-2). |
| `session` | `RecordingSession` | Temporal descriptors. |
| `validation` | `ValidationReport` | All check findings + derived status. |
| `quality` | `QualityReport` | Record-level quality posture. |
| `status` | `RecordStatus` | `VALIDATED` or `QUARANTINED`. |

## Optional fields
| Field | Type | Meaning |
|-------|------|---------|
| `lineage_id` | str \| None | Id of the record node in the lineage DAG. |

## Validation rules
- `status = VALIDATED` iff `validation.status` is acceptable (no `ERROR`).
- `status = QUARANTINED` if any `ERROR` finding exists; the record still exists and
  remains fully traceable (it is *not* discarded — report, never delete).
- Files that cannot be read/parsed never produce a record; they raise
  `IngestionError` carrying a `ValidationReport` instead (so the failure is still
  structured evidence).

## Quality rules
- `quality.state = FLAGGED` when any non-INFO finding exists, else `OK`.
- Quality is advisory: a `FLAGGED` record may still be `VALIDATED` (e.g. a duplicate
  warning) — the decision to include it in a dataset is explicit and recorded.

## Version rules
- The record inherits the versions of its parts (`extractor_version`,
  `validator_version`) and the data-foundation version; a re-ingest with the same
  bytes + versions reproduces the same record.

## Lineage rules
- Lineage node `record:<file_id>` (`artifact_type = "validated_record"`) with
  inputs = the validation node and the metadata node. Set as `lineage_id`.

## Traceability rules
- One object answers "what is this, is it valid, whose is it, and where did it come
  from?" end-to-end — the data-layer expression of AP-5 / NR-11.
- Serializable; `from_dict(to_dict(r))` reproduces the record exactly.
