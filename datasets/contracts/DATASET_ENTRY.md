# Contract 4 — Dataset Entry

> Schema: [`datasets/schemas/dataset_entry.py`](../schemas/dataset_entry.py) → `DatasetEntry`

## Purpose
Represents the **membership** of one validated record in one dataset. It binds
`dataset_id + file_id + patient_id` together with the content checksum so dataset
membership is itself content-addressed and auditable.

## Required fields
| Field | Type | Meaning |
|-------|------|---------|
| `dataset_id` | str | Owning dataset. |
| `file_id` | str | Member record. |
| `patient_id` | str | Member's patient (for patient-disjoint accounting). |
| `recording_id` | str | Member's recording. |
| `content_sha256` | str | Content checksum captured at membership time. |
| `validation_status` | `ValidationStatus` | Status when added. |
| `quality_state` | `QualityState` | Quality posture when added. |

## Optional fields
| Field | Type | Meaning |
|-------|------|---------|
| `status` | `RecordStatus` | Defaults to `REGISTERED`. |
| `note` | str \| None | Free-text rationale for inclusion (governance-friendly). |

## Validation rules
- A record should be `VALIDATED` (not `QUARANTINED`) to be added to a dataset
  intended for downstream use; adding a flagged/quarantined record requires an
  explicit `note` (recorded rationale, NR-5 spirit).
- `content_sha256` must match the member's Raw EEG File checksum.

## Quality rules
- `quality_state` is copied from the record; it is advisory and never causes silent
  exclusion — exclusion is an explicit curation decision.

## Version rules
- Entries are immutable snapshots of membership; changing membership means a new
  Dataset Manifest / Dataset Version, never an in-place edit.

## Lineage rules
- Connects a record's lineage subtree into a dataset's lineage; the dataset's
  Manifest aggregates entries deterministically.

## Traceability rules
- Because the entry stores `content_sha256`, an audit can later confirm the exact
  bytes that were a member, independent of the live file (AP-5 / NR-11).
