# Contract 7 — Dataset Manifest

> Schema: [`datasets/schemas/manifest.py`](../schemas/manifest.py) → `DatasetManifest` / `ManifestEntry`

## Purpose
The deterministic, content-addressed listing of **exactly which records** (by
content checksum) constitute a dataset at a point in time. Its
`content_fingerprint` is the mechanism that makes **"no silent dataset
modifications"** detectable (Project directive; AP-6 / NR-10).

## Required fields
| Field | Type | Meaning |
|-------|------|---------|
| `dataset_id` | str | The dataset described. |
| `version` | str | Version label this manifest is built for. |
| `entries` | tuple[`ManifestEntry`] | `(file_id, content_sha256, patient_id, recording_id)` per member. |
| `data_foundation_version` | str | Foundation version (participates in fingerprint). |

## Optional fields
| Field | Type | Meaning |
|-------|------|---------|
| `description` | str | Human-readable summary. |
| `created_at` | str \| None | Provenance only — **excluded from fingerprint**. |
| `extra` | dict | Reserved for site/split metadata (future). |

## Derived (computed) fields
- `content_fingerprint` — SHA-256 over the **sorted** entries + `dataset_id` +
  `data_foundation_version`. **Order-independent**, and **excludes** the version
  label and volatile fields, so two version labels with the same membership share a
  fingerprint.
- `record_count`, `patient_count`, `patient_ids`.

## Validation rules
- Entries are de-duplicated by `file_id` (the same content is listed once).
- Every `content_sha256` must correspond to a known record (checked by audit).

## Quality rules
- The manifest does not judge quality; it records membership. Quality filtering is
  an explicit curation step that happens *before* a manifest is built.

## Version rules
- Building a manifest with identical membership to the current version is a **no-op**
  and is rejected by the version chain unless explicitly allowed — preventing
  meaningless version churn.

## Lineage rules
- Aggregates the lineage of its member records; serves as the input to a Dataset
  Version node.

## Traceability rules
- Given a manifest, the full membership and its content hashes can be re-verified
  at any later time (`audit_manifest`), independent of the live files.
