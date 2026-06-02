# Contract 8 — Dataset Version

> Schema: [`datasets/schemas/dataset_version.py`](../schemas/dataset_version.py) → `DatasetVersion`
> Chain: [`datasets/versioning/version_chain.py`](../versioning/version_chain.py) → `VersionedDataset`

## Purpose
An **immutable, fingerprinted snapshot** of a dataset and its relationship to a
parent version. Versions form an **append-only chain**: each names its
`parent_version` and the `manifest_fingerprint` it certifies, plus a change
summary. This is how the platform guarantees no silent modifications and supports
dataset audits and reproducibility tracking.

## Required fields
| Field | Type | Meaning |
|-------|------|---------|
| `dataset_id` | str | The dataset. |
| `version` | str | This version's label (unique within the chain). |
| `manifest_fingerprint` | str | The content fingerprint this version certifies. |
| `data_foundation_version` | str | Foundation version at certification time. |

## Optional fields
| Field | Type | Meaning |
|-------|------|---------|
| `parent_version` | str \| None | Previous version (`None` for the first). |
| `record_count` / `patient_count` | int | Snapshot sizes. |
| `change_summary` | str | What changed vs. the parent (governance-friendly). |
| `created_at` | str \| None | Provenance only. |
| `extra` | dict | Reserved. |

## Validation rules
- `version` must be unique in the chain.
- A manifest whose fingerprint equals the latest version's is a **no-op** and is
  rejected (unless explicitly allowed) — versions reflect real change.
- The committed manifest's `dataset_id` must match the chain.

## Quality rules
- Version certification does not assess signal quality; it certifies *membership
  content*. Quality verdicts live on records/entries.

## Version rules
- Append-only and immutable: corrections are made by committing a **new** version
  with a recorded `change_summary`, never by editing an existing one.
- Change tracking: each commit returns a `ManifestDiff` (added/removed files &
  patients) so every modification is explicit.

## Lineage rules
- A version node depends on its manifest (and transitively on member records),
  forming the top of the dataset's data-layer lineage.

## Traceability rules
- `verify_dataset_version(version, manifest)` re-checks that a manifest reproduces
  the certified fingerprint; `audit_manifest(..., version=...)` additionally checks
  content against the registry — the operational form of reproducibility tracking
  (AP-6 / NR-10).
