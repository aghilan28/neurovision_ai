# Duplicate Upload Behavior (DBE-3)

This guide documents how the NeuroVision upload API behaves when the **same** (or
content-identical) EEG file is uploaded more than once. The guarantee: **a user can never
crash NeuroVision (HTTP 500) by re-uploading an EEG file.** Behavior is deterministic and
documented.

## Root cause (the bug this fixes)

The Final Hostile QA Audit found that re-uploading the same EEG returned **HTTP 500**. Cause:
the `upload_id` is content-shape-addressed (deterministic, so a re-upload mints the *same*
id), but the upload was re-registered with a registry `content_signature` that embeds the
**audit head** — which advances between requests. Same registry key + different signature →
`RegistryError("already registered with different content")` → unhandled → 500.

## The fix

Before any registration, the service classifies each upload by an **authoritative content
hash** (a real sha-256 of the raw bytes, via `ml.provenance`) plus the existing `upload_id`
identity. A processed duplicate short-circuits and **returns the existing result** — no
re-registration, no re-analysis, no exception. As defense-in-depth, registry registration is
idempotent (re-registering a known id is a no-op).

## Classification (closed vocabulary)

| Classification | Meaning | API result |
|---|---|---|
| `NEW_UPLOAD` | content + identity both new | **201 Created**, new analysis |
| `EXACT_DUPLICATE` | identical bytes + same identity already processed | **200 OK**, returns the existing analysis (`duplicate: true`) |
| `CONTENT_DUPLICATE` | identical bytes under a different filename/identity | **200 OK**, returns the existing analysis (`duplicate: true`) |
| `CONFLICTING_UPLOAD` | same identity, **different** content | **409 Conflict**, no analysis (deterministic, no crash) |
| `INVALID_UPLOAD` | bytes failed EEG validation | **422 Unprocessable Entity** |

## API contract

`POST /v1/uploads` (bearer token required) returns:

* **201** — new upload: `{ "accepted": true, "duplicate": false,
  "duplicate_classification": "NEW_UPLOAD", "upload": {...}, "analysis_id": "...",
  "prediction": {...}, "readiness": {...} }`
* **200** — duplicate of a processed upload: identical body shape with `"duplicate": true`
  and `"duplicate_classification": "EXACT_DUPLICATE" | "CONTENT_DUPLICATE"`; the
  `analysis_id`/`prediction` are the **existing** ones (idempotent).
* **409** — conflicting upload: `{ "accepted": false,
  "duplicate_classification": "CONFLICTING_UPLOAD", "reason": "...", "upload": {...} }`.
* **422** — invalid EEG: `{ "accepted": false, "duplicate_classification": "INVALID_UPLOAD",
  ... }`.

**There is no path that returns 500 for a duplicate upload.**

## Operator guide

* Re-uploading the same file is safe and idempotent — you get the same `analysis_id` and
  prediction back with `200 OK` (no duplicate analysis, no duplicate registry/audit/lineage
  records, no orphans).
* Uploading the same file under a different name is recognized as a content duplicate and also
  returns the existing result.
* A `409` means a *different* recording was uploaded under an identity that already holds
  different content — resolve by uploading under a distinct file.

## Integrity guarantees (DBE3-E/G)

For a duplicate, the platform performs **no** new registration, lineage node, or audit append
beyond a single `upload_duplicate` audit event — so the registry stays orphan-free, the audit
chain stays verifiable, and lineage stays intact. Determinism is preserved: the same inputs
always yield the same classification + the same returned `analysis_id`.

## Scope

DBE-3 changes **only** the upload-reliability path (duplicate detection/classification/handling
+ idempotent registration + the upload endpoint's status mapping). It does not touch datasets,
models, inference, persistence architecture, security, operations, deployment, or token
handling.
