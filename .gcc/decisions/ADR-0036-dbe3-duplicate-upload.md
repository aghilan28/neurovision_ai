# ADR-0036 — DBE-3: Duplicate Upload Reliability Fix

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Deployment Blocker Elimination Program — DBE-3
> **Builds on:** ADR-0001 … ADR-0035 (Productization + DRP + Tracks 1-4 + DBE-1 + DBE-2)
> **Resolves:** Final Hostile QA Audit CRITICAL defect — *DUPLICATE EEG UPLOADS PRODUCE SERVER ERRORS (500)*
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-5/AP-8/NR-11 (traceability),
> AP-7/NR-8 (boundaries), AP-9/NR-5 (this record), NR-13 (scope), NR-2 (honesty)

## 1. Context & root cause (reproduced)

The Final Hostile QA Audit found that re-uploading the same EEG returned **HTTP 500**. Root
cause (reproduced at the registry level): the `upload_id` is content-shape-addressed
(deterministic, so a re-upload mints the *same* id), but the upload was re-registered with an
`ApplicationRegistryRecord` whose `content_signature()` embeds `audit_state = self.audit.head`
— and the audit head **advances** between requests. Same registry key `(upload_id, version)`,
**different** signature → `RegistryError("already registered with different content")` →
unhandled → HTTP 500. Same-content-different-filename also 500'd for the same reason.

DBE-3 resolves **only** this defect. Scope is strictly upload reliability — no changes to
datasets, models, inference, persistence architecture, security, operations, deployment,
Docker, or token handling.

## 2. Decisions

### D1 — Authoritative content identity (DBE3-B)
A new `uploads/duplicates.py` adds `content_hash(bytes)` — a real **sha-256 of the raw uploaded
bytes** via `ml.provenance` (reusing the platform hashing; no parallel identity system). This
is the authoritative duplicate key; it is distinct from the pre-existing length-only
`content_fingerprint` (which could not distinguish content).

### D2 — Closed duplicate classification (DBE3-C)
A closed `DuplicateClass` vocabulary: `NEW_UPLOAD`, `EXACT_DUPLICATE` (same content + same
identity), `CONTENT_DUPLICATE` (same content, different filename/identity), `CONFLICTING_UPLOAD`
(same identity, different content), `INVALID_UPLOAD` (failed validation). A pure, deterministic
`DuplicateDetector` classifies against an in-memory content/identity index.

### D3 — Safe handling: detect-before-register short-circuit (DBE3-D/E)
`ApplicationPlatformService.upload_and_analyze` classifies the upload **before any
registration**. A processed `EXACT_/CONTENT_DUPLICATE` returns the **existing** `AnalysisOutcome`
(via `dataclasses.replace` with `is_duplicate=True`) — no re-registration, no re-analysis, no
exception, only one `upload_duplicate` audit marker. As defense-in-depth, `_register` is now
**idempotent** (re-registering a known entity id is a no-op), so no registration path can ever
raise `RegistryError` → 500. Registry stays orphan-free; audit + lineage stay intact.

### D4 — Deterministic API contract (DBE3-F)
`POST /v1/uploads` now returns a deterministic status: **201** new, **200** duplicate (reused
result, `duplicate=true` + `duplicate_classification`), **409** conflicting, **422** invalid.
**No duplicate path returns 500.**

### D5 — A local `from dataclasses import replace` removed
The pre-existing local import inside `upload_and_analyze` made `replace` a function-local name;
the new duplicate short-circuit uses `replace` earlier, which would `UnboundLocalError`. The
import is hoisted to module scope (behaviour-preserving).

## 3. Consequences

- `python -m scripts.verify_dbe3_duplicate_upload` → **ALL 15 CRITERIA PASS**: the bug is
  reproduced at the registry level, the root cause is documented, duplicate detection +
  classification work, the live endpoint returns 201/200/200/200 for new+three duplicates (no
  500), and registry/audit/lineage/readiness integrity hold.
- New suite `tests/test_duplicate_upload.py` (15 tests) incl. the exact regression (2nd identical
  upload ≠ 500), repeated duplicates, content-duplicate, invalid, and integrity invariants.
- `ruff` clean; `tests/test_boundaries.py` green; full suite remains green; no new dependencies.

## 4. Scope guard (explicitly NOT done — NR-13)

Did not fix persistence wiring or invalid-token 500; did not modify Docker/deployment assets,
datasets, models, inference, security/operations logic, or Track 1-4. Those remain open audit
findings for their own phases.

## 5. Honesty statement (NR-2)

DBE-3 makes duplicate EEG uploads **deterministic and crash-free** — verified by reproducing
the original `RegistryError`/500 failure mode and then proving the live endpoint returns
200/409/422 (never 500) for duplicate/conflicting/invalid uploads, with registry, audit, and
lineage integrity preserved. It changes only the upload-reliability path. The other
audit-identified blockers (unwired persistence → state lost on restart; invalid-token 500)
remain **open** and out of scope here.
