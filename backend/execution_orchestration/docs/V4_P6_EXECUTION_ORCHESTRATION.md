# V4-P6 — Execution Orchestration Layer (design notes)

> **Phase:** V4-P6 · **Subsystem:** `backend/execution_orchestration/` · **ADR:** ADR-0013

## Purpose
Make **execution** a first-class governed entity: the *governed progression of
approved work*. Versioned, traceable, auditable, lineage-tracked, governed,
deterministic, recoverable — and **never autonomous**.

## Why "governed progression, not autonomous action"
The directive forbids autonomous action, self-directed operation, and agent freedom.
An Execution coordinates already-approved artifacts and progresses them through a
governed lifecycle; it does not bypass policy or governance and performs **no
autonomous planning**. Enforced structurally: the gate's *risk* dimension fails an
execution carrying an autonomy/self-direction payload, and ACTIVE requires
authorization.

## Identity
`execution+{hash16}` derived from `(source_task_id, assignment_id, execution_key)` —
the *coordinated work*, not the lifecycle state. Relationships use `execrel+{hash16}`.

## Coordination (references approved artifacts; never plans)
`ExecutionContext` binds the approved goal/plan/task/agent/assignment the execution
progresses. `create_execution` requires a **complete** context (task + agent +
assignment), an assignment **consistent** with the context, and a **progressable**
assignment (state `assigned`); otherwise `ExecutionCoordinationError`. Coordination
references existing approved artifacts — it never creates or plans new ones.

## Lifecycle + authorization
`PROPOSED → QUEUED → AUTHORIZED → ACTIVE → {PAUSED, BLOCKED, COMPLETED, TERMINATED}
→ ARCHIVED` (PAUSED/BLOCKED resume to ACTIVE). Four transitions are **policy-
governed** (hooks execution_authorization / execution_activation /
execution_completion / execution_termination). An execution **cannot become ACTIVE
without authorization** (gate's *governance* dimension + the authorization decision);
AUTHORIZED/ACTIVE set `authorization_state = authorized`.

## Monitoring (observe only)
`monitoring.observe(execution)` derives a read-only `ExecutionStatus`: a
deterministic [0,1] progress index from the lifecycle **state** (not wall-clock),
plus observed blocking conditions / risks / escalations / outcome. **Monitoring
observes; it never modifies execution.**

## Traceability
An execution's lineage parents the **approved assignment** node, which parents the
agent + task nodes — so `verify_chain(execution)` spans `Patient → … → Task → Agent
assignment → Execution`. Agent ↔ Execution: every execution references an approved
assignment.

## Determinism (NR-9/NR-10)
No wall-clock. Identities, versions, and audit heads are content-addressed, so
identical inputs reproduce identical executions.

## Validation (nine dimensions)
identity · lifecycle · authorization · assignment · registry · governance · audit ·
lineage · version — all via the shared `ml.validation.ValidationReport`.

## Scope guard (NR-13)
No autonomous action, no autonomous planning, no simulation/scenario engines, no V5.
