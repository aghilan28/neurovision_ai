# Contract 1 — Raw EEG File

> Schema: [`datasets/schemas/raw_eeg_file.py`](../schemas/raw_eeg_file.py) → `RawEegFile`

## Purpose
Represents a physical EDF/EDF+ file at the moment it enters the system, **before**
any interpretation. It establishes the file's **content identity** (the SHA-256 of
its bytes) so the entire downstream lifecycle is anchored to exactly those bytes.

## Required fields
| Field | Type | Meaning |
|-------|------|---------|
| `file_id` | str | Content-derived id `edf-<sha256[:16]>`. Deterministic. |
| `content_sha256` | str | SHA-256 of the raw file bytes (the integrity anchor). |
| `file_name` | str | Basename as presented (provenance). |
| `file_size_bytes` | int | Size in bytes. |
| `detected_format` | `FileFormat` | Structural detection (EDF / EDF+C / EDF+D / UNKNOWN / UNSUPPORTED). |

## Optional fields
| Field | Type | Meaning |
|-------|------|---------|
| `source_path` | str \| None | Where the file came from. **Provenance only — not identity.** |

## Validation rules
- `detected_format` must be one of the supported formats (`EDF`, `EDF+C`, `EDF+D`)
  for the file to proceed; `UNSUPPORTED`/`UNKNOWN` ⇒ ingestion fails with a report
  (`UNSUPPORTED_FORMAT` / `UNKNOWN_FORMAT`) — V1 directive, enforced by NR-13.
- `content_sha256` must be a 64-char lowercase hex digest.
- `file_size_bytes` must equal the actual file size used to compute the hash.

## Quality rules
- The raw file carries no quality verdict itself; quality is assessed after
  metadata extraction (see Validated EEG Record). A zero-byte or sub-header-size
  file is surfaced as a readability/parse error, never silently accepted.

## Version rules
- Content-addressed: a single byte change produces a different `content_sha256`
  and therefore a different `file_id` (a *new* raw file, never an in-place edit).
- The id scheme is owned by the data-foundation version; changing it is a recorded
  governance decision (NR-5).

## Lineage rules
- The raw file is the **root node** of a record's lineage DAG
  (`artifact_type = "raw_eeg_file"`, `content_fingerprint = content_sha256`,
  no inputs).

## Traceability rules
- Every later artifact for this file references `file_id`; given `file_id` one can
  recover the exact bytes' hash and the full provenance chain (AP-5 / NR-11).
- Two files with identical bytes share one identity regardless of `source_path`
  (enables exact duplicate detection).
