# V2-P2 — Clinical Review Workflow (design & contracts)

> **Phase:** V2-P2 · **Status:** Implemented
> **Decision record:** [`../../../.gcc/decisions/ADR-0003`](../../../.gcc/decisions/ADR-0003-v2-p1-p2-clinical-case-and-review.md)

---

## 1. Review identity & versioning

A review identity is minted via the case identity system (`mint_identity("review",
{case_id, review_key})`) — derived from the case, deterministic, content-addressed.
`ReviewVersion` chains like `CaseVersion` (`hash(state_signature, previous)`),
guaranteeing a unique version per mutation even across reopen cycles.

## 2. Lifecycle

8 states (CREATED, ASSIGNED, IN_PROGRESS, PENDING_CONFIRMATION, COMPLETED,
REOPENED, CLOSED, ARCHIVED) with governed send-back/reopen edges; ARCHIVED is
terminal. Forbidden transitions raise `ReviewLifecycleError`.

## 3. Sessions

`ReviewSession` is an immutable value; each recorded activity returns a new value
(via `replace`) so its evolution is explicit and auditable. A session records who
reviewed which case/study, which **registered** artifacts/reports were viewed, the
actions taken, and the outcome + notes. Session ids are content-addressed; each
session gets a `review_session` lineage node parented to the review head.

## 4. Assignment

Assignments are immutable values with assignee/priority/status/reason and a
preserved history (reassignment closes the prior assignment and opens a new
active one). `escalate` is a **forward hook**: it bumps an escalation level for
future routing but performs no operational action in V2 (no notifications, no
auto-reassignment).

## 5. Tracking

Derived deterministically from the Review + its audit log (single source of truth):
progress fraction, milestones reached, session counts, transition duration,
revisions, reopen/completion events.

## 6. Audit & lineage

The review audit log is the **same** tamper-evident `ImmutableAuditLog` as the
case subsystem, bound to `ReviewAuditRecord` (NR-6: one implementation). Event
kinds: review_created, assignment_created, reassigned, session_started,
artifact_access, review_action, session_ended, status_change, version_changed.

The review shares the Case's `LineageTracker`. Review/session nodes are parented to
the Case node and the V1 inference node, so `verify_chain(review.lineage_id)` proves
Review → Session → Case → Study → Inference → … → Training traceability.

## 7. Registry, validation, reports

`ReviewRegistry` holds the latest record per review (silent overwrite rejected).
`ReviewValidator` runs 7 checks: session, registry, audit, lineage, assignment,
status, version integrity. Six reports: summary, audit, lineage, assignment,
validation, progress.

## 8. Integration with V1 (faithful uncertainty, NR-4)

Sessions reference the registered V1 outputs (e.g. `summary_report`,
`coverage_report`) and the case study's checksummed artifact refs; a session may
only view **registered** artifacts. The review never recomputes or flattens the V1
uncertainty — it reviews the registered, calibrated, conformal, coverage-validated
outputs as produced.
