# Contract 6 — Recording Session

> Schema: [`datasets/schemas/recording_session.py`](../schemas/recording_session.py) → `RecordingSession`

## Purpose
Represents one continuous acquisition (in EDF, one file) and links a patient to a
file with temporal descriptors. Keeping the session distinct from the file and the
metadata lets later versions model multi-file or **streaming** sessions (V3)
without reshaping the data contracts (AP-1, no rewrites).

## Required fields
| Field | Type | Meaning |
|-------|------|---------|
| `recording_id` | str | One recording per EDF file in V1. |
| `patient_id` | str | Owning patient (AP-2). |
| `file_id` | str | Source file. |
| `start_date` / `start_time` | str | Raw EDF header strings. |
| `duration_seconds` | float | Recording duration. |

## Optional fields
| Field | Type | Meaning |
|-------|------|---------|
| `start_datetime_iso` | str \| None | Normalized ISO start (date + time) when parseable. |
| `equipment` | str \| None | From the EDF+ recording field, when present. |
| `admin_code` | str \| None | EDF+ administration code, when present. |

## Validation rules
- `duration_seconds >= 0`; zero duration is surfaced as a `ZERO_DURATION` warning
  at the record level.
- `recording_id` and `patient_id` must be consistent with the Metadata Record.

## Quality rules
- The session carries no independent quality verdict; temporal anomalies (e.g. zero
  duration) are reported via the record's validation/quality reports.

## Version rules
- Temporal interpretation (date/time normalization) is owned by the extractor
  version; changes bump it via a governance decision (NR-5).

## Lineage rules
- Derived from the Metadata Record; referenced by the Validated EEG Record.

## Traceability rules
- The session deterministically connects `patient_id ↔ recording_id ↔ file_id`,
  supporting both patient-disjoint grouping and end-to-end provenance.
