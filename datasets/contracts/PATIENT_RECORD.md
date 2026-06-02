# Contract 5 — Patient Record

> Schema: [`datasets/schemas/patient_record.py`](../schemas/patient_record.py) → `PatientRecord`

## Purpose
Anchors **patient identity** — the load-bearing primitive for **patient-disjoint
validation** (AP-2 / NR-3). Every recording belongs to exactly one patient so that
downstream splitting can guarantee no patient spans train/validation/test.

## Required fields
| Field | Type | Meaning |
|-------|------|---------|
| `patient_id` | str | Deterministic identity (`patient-<hash16>`). |
| `raw_patient_field` | str | Original EDF patient header text (traceability). |

## Optional fields
| Field | Type | Meaning |
|-------|------|---------|
| `sex` | str \| None | `M`/`F`/`None` (EDF+ encodes `X` as unknown → `None`). |
| `birthdate_iso` | str \| None | Normalized birthdate when present. |
| `recording_ids` | tuple[str] | Recordings attributed to this patient. |

## Validation rules
- `patient_id` is derived from the EDF+ patient **code** subfield when present;
  otherwise from the raw patient field; otherwise from the file content hash.
- **Absent identity ⇒ a distinct patient.** Unknown patients are never merged
  (merging could create cross-patient leakage); a `MISSING_PATIENT_IDENTITY`
  warning is emitted so a human can supply identity if known.

## Quality rules
- No PII beyond coarse header-provided attributes is retained. Identity is a stable
  token, not an expansion of personal data.

## Version rules
- The identity-derivation rule is owned by the data-foundation version; changing it
  is a governance decision (NR-5) because it affects patient grouping.

## Lineage rules
- Derived from the Metadata Record; its `patient_id` is referenced by the Validated
  EEG Record, Dataset Entry, and Manifest entries.

## Traceability rules
- `raw_patient_field` always preserves the source text, so any derived `patient_id`
  can be explained and audited.
- `recording_ids` is kept **sorted and unique** for deterministic merges
  (`with_recording`).
