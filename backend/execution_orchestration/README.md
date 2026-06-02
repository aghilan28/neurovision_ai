# `backend/execution_orchestration/` — Execution Orchestration Layer (V4-P6)

> **Layer:** Application (`backend/`) — a V4 subsystem
> **Status:** Implemented (V4-P6)
> **Governing docs:** AP-3/AP-6 (determinism/reproducibility), AP-5/AP-8 (traceability/
> audit), AP-7/NR-8 (boundaries), AP-9/AP-11 (governance), NR-9/NR-10/NR-13; ADR-0013

Introduces **Execution as a governed first-class entity** — the *governed
progression of approved work*. An execution coordinates already-approved artifacts
and progresses them deterministically through a governed lifecycle.

---

## Execution is governed progression — never autonomous
An Execution is **not** autonomous action, self-directed operation, or agent
freedom. It **does not bypass policy or governance**, coordinates already-approved
artifacts, and performs **no autonomous planning**. The governance gate's *risk*
dimension rejects any execution carrying an autonomy/self-direction payload, and the
service exposes no autonomous-action API.

## Domain model
`ExecutionIdentity` (`execution+{hash16}`), `ExecutionRecord` (the mutable
aggregate), `ExecutionMetadata`, `ExecutionContext`, `ExecutionAssignment`,
`ExecutionStatus`, `ExecutionVersion`, `ExecutionLifecycleState`,
`ExecutionGovernanceRecord`, `ExecutionAuditRecord`, `ExecutionLineageRecord`,
`ExecutionRegistryRecord`, `ExecutionRelationship`.

## Coordination (`coordination/`) — references approved artifacts, never plans
`ExecutionContext` binds the approved goal / plan / task / agent / assignment.
`create_execution` requires a **complete** context, an assignment **consistent** with
it, and a **progressable** assignment (state `assigned`) — else
`ExecutionCoordinationError`. Coordination references existing approved artifacts; it
never creates or plans new ones (no autonomous planning).

## Lifecycle + authorization (`lifecycle/`, `governance/`)
`PROPOSED → QUEUED → AUTHORIZED → ACTIVE → {PAUSED, BLOCKED, COMPLETED, TERMINATED} →
ARCHIVED` (PAUSED/BLOCKED resume to ACTIVE). Forbidden transitions raise
`ExecutionLifecycleError`. AUTHORIZED / ACTIVE / COMPLETED / TERMINATED are
**policy-governed**; an execution **cannot become ACTIVE without authorization**.

## Monitoring (`monitoring/`) — observe only, never modify
`observe(execution)` returns a read-only `ExecutionStatus` with a deterministic,
state-derived [0,1] progress index plus observed blocking conditions / risks /
escalations / outcome. **Monitoring observes; it never modifies the execution.**

## Governance, registry, audit, lineage, validation
- **Governance gate** (`governance/`): architecture / quality / context / risk /
  governance — reuses the shared `ml.validation.ValidationReport`.
- **Registry** (`registry/`): no execution exists outside it; silent overwrite
  forbidden; also tracks versioned relationships.
- **Audit / lineage**: the shared `ImmutableAuditLog` + `ml.lineage.LineageTracker`;
  an execution node parents the assignment node, so `verify_chain` reaches the patient.
- **Validation** (`validation/`): the nine integrity dimensions — identity,
  lifecycle, authorization, assignment, registry, governance, audit, lineage, version.

## Agent ↔ Execution integration
Every execution references an **approved agent assignment** (`ExecutionAssignment` +
`ExecutionContext.assignment_id`). `ExecutionService(policy_decider=...)` accepts an
injected decider; the V4-P2 policy engine provides
`backend.policy_engine.execution_policy_decider` (with
`install_default_execution_policies`), so **every active execution is policy
governed** without `execution_orchestration` importing `policy_engine`.

## Quick start
```python
from backend.execution_orchestration import (
    ExecutionService, ExecutionMetadata, ExecutionContext, ExecutionAssignment,
    ExecutionLifecycleState)
esvc = ExecutionService(lineage_tracker=shared_tracker, policy_decider=exec_decider)
ctx = ExecutionContext(goal_id=g, plan_id=p, task_id=t, agent_id=a, assignment_id=asn.assignment_id)
easn = ExecutionAssignment(assignment_id=asn.assignment_id, agent_id=a, task_id=t,
                           assignment_state=asn.state)
ex = esvc.create_execution(execution_key="run", metadata=ExecutionMetadata(title="Run",
                           objective="progress the approved task"), context=ctx,
                           assignment=easn, assignment_lineage_id=asn.lineage_id)
for st in (ExecutionLifecycleState.QUEUED, ExecutionLifecycleState.AUTHORIZED,
           ExecutionLifecycleState.ACTIVE, ExecutionLifecycleState.COMPLETED):
    esvc.transition(ex, st)
assert esvc.validate(ex).ok
```

Run the tests: `pytest tests/test_execution_orchestration.py`.
See [`docs/V4_P6_EXECUTION_ORCHESTRATION.md`](./docs/V4_P6_EXECUTION_ORCHESTRATION.md).

## Scope guard (NOT built — NR-13)
No autonomous action, no autonomous planning, no simulation/scenario engines, no V5
features. Execution is the governed progression of approved work.
