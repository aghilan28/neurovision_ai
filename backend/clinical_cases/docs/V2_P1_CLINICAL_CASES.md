# V2-P1 — Clinical Case Foundation (design & contracts)

> **Phase:** V2-P1 · **Status:** Implemented
> **Decision record:** [`../../../.gcc/decisions/ADR-0003`](../../../.gcc/decisions/ADR-0003-v2-p1-p2-clinical-case-and-review.md)

---

## 1. Identity model

Identities are `"{kind}+{hash16}"` content hashes of `(kind, identity_version,
deidentified component keys)`:

| kind | components | parent | minted in |
|------|-----------|--------|-----------|
| patient | patient_key | — | V2-P1 |
| case | patient_id, case_key | patient | V2-P1 |
| study | case_id, study_key | case | V2-P1 |
| review | case_id, review_key | case | V2-P2 |
| finding | review_id, finding_key | review | **future (blocked)** |
| decision | review_id, decision_key | review | **future (blocked)** |

Properties: **stable · deterministic · collision-resistant · versioned · traceable**
(non-root identities embed `derived_from` = parent id). Identities are **never**
filename/folder-derived, so a Case is portable across any future storage layout.
`*_key` components must be **deidentified** (the system hashes them; it interprets
no PHI).

## 2. Versioning (per-case hash chain)

A `CaseVersion` chains the current state signature with the previous version:
`version_n = hash(state_signature, version_{n-1})`. This guarantees a **unique**
version on every governed mutation — even when a case returns to a logically
identical state (e.g. after a reopen) — and makes the registry's "no silent
overwrite" guard precise. `version_integrity` recomputes and compares.

## 3. Lifecycle

8 states with a mostly-forward DAG + two governed reopen edges; `ARCHIVED` is
terminal. The machine is the single source of truth for legal transitions; every
accepted transition emits a `TransitionRecord` for the audit log.

## 4. Audit (immutable, tamper-evident)

`ImmutableAuditLog` is append-only and hash-chained:
`event_hash = hash(seq, kind, payload, prev_hash, created_at)`, each event linking
to the previous. `verify()` recomputes the whole chain; any modification or
reordering is detected. Event kinds: case_created, study_attached, state_change,
lineage_changed, version_changed.

## 5. Lineage (shared with V1)

Patient/Case/Study lineage nodes are built on `ml.lineage` and recorded in the
**same** `LineageTracker` as V1 inference nodes. The case head advances on every
mutation, with parents chaining to the previous head and (on attach) the study +
imported V1 inference nodes — so `verify_chain(case.lineage_id)` proves complete
traceability across V1 + V2.

## 6. Registry & validation

`CaseRegistry` holds the latest record per case; a new *version* is an update,
re-registering the *same* version with different content is a forbidden silent
overwrite. `CaseValidator` runs 7 checks: identity, registry, lifecycle, lineage,
audit, artifact, version integrity.

## 7. Reports

Case summary, audit, lineage, lifecycle, validation — all reproducible, version-
tagged dicts.

## 8. Recovery

A Case is a permanent record: the registry record + the (verifiable) audit log +
the (verifiable) lineage chain fully describe it, independent of any filename or
folder — so it is recoverable and survives architecture evolution.
