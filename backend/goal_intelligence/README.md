# `backend/goal_intelligence/` — Goal Intelligence Foundation (V4-P1)

> **Layer:** Application (`backend/`) — a V4 subsystem
> **Status:** Implemented (V4-P1)
> **Governing docs:** AP-3/AP-6 (determinism/reproducibility), AP-5/AP-8 (traceability/
> audit), AP-7/NR-8 (boundaries), AP-9/AP-11 (governance), NR-9/NR-10/NR-13; ADR-0011

Introduces **Goals as first-class platform entities**. Version 4 begins by answering
**"why does work exist?"** before "how should work be performed?". A Goal is the
foundation for later phases (plans, tasks, agents, execution) — but here it is
**intent only**.

---

## A Goal is intent — never execution
A Goal defines a **desired outcome**. It is **not** a recommendation, a task, a
plan, or execution, and it **never directly performs actions**. The governance
gate's *risk* dimension rejects any goal carrying an executable action payload, and
the service exposes no execute/run API.

## Domain model
`GoalIdentity` (`goal+{hash16}`), `GoalRecord` (the mutable aggregate),
`GoalMetadata`, `GoalCategory` + `GoalPriority` (taxonomy), `GoalVersion`,
`GoalLifecycleState`, `GoalConstraintReference`, `GoalGovernance`,
`GoalRelationship`, `GoalAuditRecord`, `GoalLineageRecord`, `GoalRegistryRecord`.
Each entity declares its schema, validation, version, audit, and lineage rules
(`schemas/contracts.py`).

## Hierarchical taxonomy (`taxonomy/`)
A closed, versioned hierarchy with `strategic` as the apex, refined by
`operational` → {`workflow`, `quality`, `knowledge`, `analytics`} and `governance`
→ {`risk`}. Priorities: `low|medium|high|critical`. Relation types: `depends_on`,
`supports`, `conflicts_with`, `derived_from`, `influences`, `blocked_by`. Easy to
extend (add a category + parent).

## Lifecycle (`lifecycle/`)
`PROPOSED → DRAFT → UNDER_REVIEW → APPROVED → ACTIVE → {SUSPENDED, COMPLETED} →
ARCHIVED` (ARCHIVED terminal; SUSPENDED↔ACTIVE; UNDER_REVIEW→DRAFT revise).
Forbidden transitions raise `GoalLifecycleError`. The APPROVED / ACTIVE / SUSPENDED
/ COMPLETED transitions are **policy-governed** (see integration).

## Governance, registry, audit, lineage, validation
- **Governance gate** (`governance/`): architecture / quality / context / risk /
  governance. A goal cannot become ACTIVE without governance approval.
- **Registry** (`registry/`): no goal exists outside it; silent overwrite forbidden;
  also tracks versioned relationships.
- **Audit** (`audit/`): the shared `ImmutableAuditLog` bound to `GoalAuditRecord`.
- **Lineage** (`lineage/`): the shared `ml.lineage.LineageTracker`; a goal's parents
  are the analytics/recommendation nodes it derives from, so `verify_chain` reaches
  the patient.
- **Validation** (`validation/`): the eight integrity dimensions — identity,
  lifecycle, registry, relationship, governance, audit, lineage, version.

## Goal ↔ Policy integration
`GoalService(policy_decider=...)` accepts an injected decider
`(hook, goal) -> (approved, decision, policy_id, authority)`. The V4-P2 policy engine
provides it (`backend.policy_engine.goal_policy_decider`), so **every active goal is
policy governed** without `goal_intelligence` importing `policy_engine`.

## Quick start
```python
from backend.goal_intelligence import GoalService, GoalMetadata, GoalCategory, GoalLifecycleState
gs = GoalService(lineage_tracker=shared_tracker, policy_decider=decider)
g = gs.create_goal(category=GoalCategory.WORKFLOW, definition_key="reduce-review-latency",
                   metadata=GoalMetadata(title="Reduce Review Latency", desired_outcome="lower latency"),
                   derived_from=[recommendation.lineage_id, analytics.lineage_id])
for st in (GoalLifecycleState.DRAFT, GoalLifecycleState.UNDER_REVIEW,
           GoalLifecycleState.APPROVED, GoalLifecycleState.ACTIVE):
    gs.transition(g, st)
assert gs.validate(g).ok
```

Run the tests: `pytest tests/test_goal_intelligence.py`.
See [`docs/V4_P1_GOAL_INTELLIGENCE.md`](./docs/V4_P1_GOAL_INTELLIGENCE.md).

## Scope guard (NOT built — NR-13)
No planning, tasks, agents, execution, simulation, or autonomous action. Goals are
intent; they never act.
