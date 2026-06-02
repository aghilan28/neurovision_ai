# `backend/clinical_review/` — Clinical Review Workflow (V2-P2)

> **Layer:** Application (`backend/`) · **Status:** Implemented (V2-P2).
> **Decision record:** [`../../.gcc/decisions/ADR-0003`](../../.gcc/decisions/ADR-0003-v2-p1-p2-clinical-case-and-review.md)
> **Governing docs:** AP-4/NR-4 (faithful uncertainty in review), AP-5/AP-8/NR-11
> (traceability/audit), AP-7/NR-8 (boundaries)

Introduces structured human **review** as a first-class platform object. Where V1
produced outputs, V2 manages the human review of those outputs:

    Case → Study → Inference Artifacts → Review Session → Review Lifecycle →
    Audit Trail → Lineage Trail

A Review is **versioned, traceable, auditable, recoverable, governed**, linked to a
Case (V2-P1) and the V1 inference it reviews, and forward-linked to future
Findings/Decisions (later versions).

---

## Subsystems

| Subsystem | Role |
|-----------|------|
| `models/` | Review entities (ReviewIdentity, ReviewSession, ReviewAssignment, ReviewStatus, ReviewHistory, ReviewAuditRecord, ReviewLineageRecord, ReviewVersion, ReviewRegistryRecord, Review). |
| `schemas/` | Per-entity contracts: Schema · Version · Validation/Lineage/Audit rules. |
| `workflow/` | The 8-state review lifecycle machine; forbidden transitions blocked. |
| `sessions/` | Review sessions: reviewer, case/study, artifacts/reports viewed, actions, outcome, notes. |
| `assignment/` | Assignment framework (assignee/priority/status/history) + inert escalation hook. |
| `tracking/` | Progress, milestones, duration, revisions, reopen/completion events. |
| `audit/` | Immutable, hash-chained review audit log (reuses the case audit primitive). |
| `lineage/` | Review/session lineage on `ml.lineage`, parented to the Case + V1 inference nodes. |
| `registry/` | The review registry — no review exists outside it; silent overwrite rejected. |
| `validation/` | 7 integrity checks (session/registry/audit/lineage/assignment/status/version). |
| `reports/` | Summary/audit/lineage/assignment/validation/progress reports (reproducible). |
| `service.py` | `ReviewService` — the governed orchestration hub. |

## Lifecycle

```
CREATED → ASSIGNED → IN_PROGRESS → PENDING_CONFIRMATION → COMPLETED → CLOSED → ARCHIVED
        (+ governed edges: PENDING_CONFIRMATION→IN_PROGRESS, COMPLETED/CLOSED→REOPENED→IN_PROGRESS; ARCHIVED terminal)
```

Every mutation is validated → audited → lineage-extended → version-bumped →
registry-synced.

## Integration

A Review **shares the Case's `LineageTracker`**, so its chain reaches Review →
Session → Case → Study → Inference → Uncertainty → Evaluation → Training (verifiable
end to end). Sessions may only "view" **registered** artifacts/reports — viewing an
unregistered ref fails `session_integrity`.

## Boundary (NR-8)

Part of the `backend` Application layer; imports `ml` and the sibling
`backend.clinical_cases`; integrates with `backend.offline_inference`. It never
imports `frontend`. Scope is strictly V2-P2 — no findings/decisions/knowledge
layers, no FHIR/HL7/EMR/hospital integration, no decision support.

## Run

```python
from backend.clinical_review import ReviewService
rs = ReviewService(lineage_tracker=cs.lineage)   # SHARE the case tracker
review = rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id,
                          study_id=study.study_id, inference_lineage_id=study.inference_lineage_id,
                          artifact_refs=tuple(study.artifact_refs))
rs.assign(review, assignee="dr.rev", priority="urgent")
review, sess = rs.start_session(review)
review, sess = rs.record_session_activity(review, sess, artifacts_viewed=[...], actions=["reviewed"])
review, sess = rs.end_session(review, sess, outcome="confirmed")
rs.submit_for_confirmation(review); rs.complete(review); rs.close(review)
assert rs.validate(review).ok                    # 7 checks
```

See [`docs/V2_P2_CLINICAL_REVIEW.md`](./docs/V2_P2_CLINICAL_REVIEW.md).
