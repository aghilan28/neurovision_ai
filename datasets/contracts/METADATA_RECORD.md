# Contract 3 — Metadata Record

> Schema: [`datasets/schemas/metadata_record.py`](../schemas/metadata_record.py) → `MetadataRecord`

## Purpose
The single **canonical** representation of everything extracted from an EDF/EDF+
file. The rest of the platform consumes this — never the raw EDF header — so EDF
header conventions are interpreted in exactly one place and the canonical shape is
stable for the platform's lifetime.

## Required fields
| Field | Type | Meaning |
|-------|------|---------|
| `file_id` | str | Links to the Raw EEG File. |
| `patient_id` | str | Deterministic patient identity (AP-2 anchor). |
| `recording_id` | str | One recording per EDF file in V1 (`rec-<sha[:16]>`). |
| `file_format` | `FileFormat` | EDF / EDF+C / EDF+D. |
| `start_date` / `start_time` | str | Raw EDF header strings (no TZ assumptions). |
| `duration_seconds` | float | Total duration (`records × record_duration`). |
| `channels` | tuple[`ChannelDescriptor`] | Per-channel descriptors incl. derived type. |
| `reference` | `ReferenceInfo` | Inferred reference/derivation scheme. |
| `technical` | `TechnicalMetadata` | Verbatim low-level header fields. |

## Optional fields
| Field | Type | Meaning |
|-------|------|---------|
| `dataset_id` | str \| None | Set when the record joins a dataset. |
| `recording_date_iso` | str \| None | Normalized date (EDF+ `Startdate` preferred). |
| `annotations` | tuple[`Annotation`] | EDF+ TAL annotations (onset, duration, text). |
| `extractor_version` | str | Version of the extraction logic (provenance). |
| `extra` | dict | e.g. `patient_identity_present` flag. |

## Validation rules
- `record_duration_seconds > 0` (else `INVALID_RECORD_DURATION`, error).
- At least one **data** channel (`NO_DATA_CHANNELS` error otherwise).
- Sampling rates positive (`INVALID_SAMPLING_RATE` error); a single shared rate is
  expected (`NON_UNIFORM_SAMPLING` warning otherwise).
- Degenerate digital/physical ranges are warned (`DEGENERATE_*`).
- Absent patient identity ⇒ `MISSING_PATIENT_IDENTITY` warning (still ingestible).

## Quality rules
- The metadata record is the input to the record-level quality verdict; it does
  not itself drop or alter channels. Richer *signal* quality is owned by
  `preprocessing/quality`.

## Version rules
- `extractor_version` is recorded; changes to extraction semantics bump it via a
  governance decision (NR-5) and invalidate cached metadata fingerprints honestly.

## Lineage rules
- Lineage node `metadata:<file_id>` (`artifact_type = "metadata_record"`), input =
  the raw file, `content_fingerprint = sha256(canonical_json(metadata))`.

## Traceability rules
- Fully serializable and reproducible: re-extraction from the same bytes + same
  `extractor_version` yields a byte-identical canonical JSON (AP-6 / NR-10).
- Patient/recording ids deterministically link metadata to Patient Record and
  Recording Session.
