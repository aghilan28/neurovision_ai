# DR-0004 · Content-addressed identity + order-independent fingerprints

- **Status:** Accepted · **Phase:** V1-P1 · **Date:** caller-supplied

## Context
Traceability (NR-11) and reproducibility (NR-10) require stable identity and a way
to detect "no silent dataset modifications" (V1 directive).

## Decision
- File identity is the SHA-256 of the file bytes; `file_id = edf-<sha[:16]>`,
  `recording_id = rec-<sha[:16]>`. Identical bytes ⇒ identical identity.
- A dataset's identity is a **manifest content fingerprint**: SHA-256 over the
  *sorted* membership (`content_sha256` + `file_id`) plus `dataset_id` and
  `data_foundation_version`. It is **order-independent** and **excludes** the
  version label and volatile fields (timestamps).
- Timestamps are caller-supplied provenance and never enter a fingerprint.

## Alternatives considered
1. **Sequential/UUID ids** — not reproducible; identical content would get
   different ids across runs. Rejected.
2. **Fingerprint including the version label** — would make two version labels with
   identical membership differ, defeating no-op detection. Rejected.

## Consequences
- Exact duplicate detection; deterministic dataset identity; auditable membership.
- Re-running ingestion yesterday vs. today yields identical identities.

## Rules / principles invoked
AP-3, AP-5 (provenance), AP-6, NR-9, NR-10, NR-11.
