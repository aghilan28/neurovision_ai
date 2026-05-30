# V4-P1 — Goal Intelligence Foundation (design notes)

> **Phase:** V4-P1 · **Subsystem:** `backend/goal_intelligence/` · **ADR:** ADR-0011

## Purpose
Make **intent** first-class. A Goal states a desired outcome and becomes the
foundation for later phases — but in V4-P1 it is *only* intent: versioned,
traceable, auditable, lineage-tracked, governed, deterministic, recoverable, and
**never execution**.

## Why "intent, not execution"
The directive forbids planning/tasks/agents/execution in V4. A Goal therefore
carries metadata (title, description, desired outcome, measure) and governance —
but no action payload. This is enforced structurally: the governance gate's *risk*
dimension fails a goal whose tags include an execution marker, and the service has
no execute/run method.

## Identity
`goal+{hash16}` derived from `(category, definition_key)` — the *definition*, not the
lifecycle state — so re-declaring the same goal yields the same id with a new content
version (auditable), never an orphan. Relationships use `goalrel+{hash16}`.

## Lifecycle + governance
The eight-state machine encodes a mostly-forward DAG with SUSPENDED↔ACTIVE and a
revise edge UNDER_REVIEW→DRAFT. Four transitions are **policy-governed** (mapped to
hooks goal_approval / goal_activation / goal_suspension / goal_completion). The
service consults the injected `policy_decider` for those; a denial records a
governance rejection on the goal and raises `GoalGovernanceError`, blocking the move.

## Relationships
Versioned, lineage-tracked edges Goal → {goal, workflow, analytics, recommendation,
risk, governance} with relations depends_on / supports / conflicts_with /
derived_from / influences / blocked_by. `depends_on`/`blocked_by` on another goal
also records a dependency on the aggregate.

## Traceability
A goal's lineage parents are the upstream analytics/recommendation nodes it derives
from (passed as `derived_from`), plus its dependency goals' nodes. Because those
nodes already trace to the patient, `verify_chain(goal.lineage_id)` spans
`Patient → … → Analytics → Recommendations → Goal`.

## Determinism (NR-9/NR-10)
No wall-clock. Identities, versions (`hash(state_signature, previous)`), and audit
heads are content-addressed, so identical inputs reproduce identical goals.

## Validation (eight dimensions)
identity · lifecycle · registry · relationship · governance · audit · lineage ·
version — all via the shared `ml.validation.ValidationReport`.

## Scope guard (NR-13)
No planning, tasks, agents, execution, simulation, autonomous decisions, or V5
features.
