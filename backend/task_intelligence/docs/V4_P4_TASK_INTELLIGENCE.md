# V4-P4 — Task Intelligence Layer (design notes)

> **Phase:** V4-P4 · **Subsystem:** `backend/task_intelligence/` · **ADR:** ADR-0012

## Purpose
Make **tasks** first-class: the atomic units of *future* execution, derived from a
ready Plan. A Task *describes* work — versioned, traceable, auditable, lineage-
tracked, governed, deterministic, recoverable — and **never executes**.

## Why "describes work, does not execute"
The directive forbids agents/execution/jobs/processes in V4-P4. A Task carries
metadata (title, description, work_definition, acceptance) and governance — but no
action payload. Enforced structurally: the governance gate's *risk* dimension fails
a task whose tags include an execution marker, and the service has no execute/run
method.

## Identity
`task+{hash16}` derived from `(category, source_plan_id, task_key)` — the
*definition*, not the lifecycle state. Dependencies use `taskrel+{hash16}`.

## Plan ⇒ Task derivation
`create_task` requires `source_plan_id`, its `source_plan_lineage_id`, and
`source_plan_state ∈ {ready, completed}` (the plan service owns plan readiness). The
plan's lineage node is the task's lineage parent, so `verify_chain(task)` spans
`Patient → … → Goal → Plan → Task`. The task also records its `source_goal_id` for
goal-reference reporting.

## Lifecycle + governance
The eight-state machine adds **BLOCKED** as a non-governed *operational* state (a
READY task whose dependencies are unmet) with BLOCKED↔READY. Three transitions are
**policy-governed** (hooks task_approval / task_readiness / task_completion); a task
cannot reach **READY** without approval. The service consults the injected
`policy_decider`; a denial raises `TaskGovernanceError`, blocking the move.

## Dependencies
Versioned edges Task → {task, plan, goal, policy} with relations depends_on / blocks
/ supports / requires / derived_from / influences. The analyzer detects cycles among
ordering edges; the validator's *dependency integrity* dimension fails a cyclic
graph.

## Determinism (NR-9/NR-10)
No wall-clock. Identities, versions, and audit heads are content-addressed, so
identical inputs reproduce identical tasks.

## Validation (eight dimensions)
identity · lifecycle · registry · dependency · governance · audit · lineage ·
version — all via the shared `ml.validation.ValidationReport`.

## Scope guard (NR-13)
No agent registry/capabilities/assignment, execution engine, execution monitoring,
simulation, autonomous actions/decisions, or V5 features.
