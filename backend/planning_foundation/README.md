# `backend/planning_foundation/` — Planning Foundation (V4-P3)

> **Layer:** Application (`backend/`) — a V4 subsystem
> **Status:** Implemented (V4-P3)
> **Governing docs:** AP-3/AP-6 (determinism/reproducibility), AP-5/AP-8 (traceability/
> audit), AP-7/NR-8 (boundaries), AP-9/AP-11 (governance), NR-9/NR-10/NR-13; ADR-0012

Introduces **Plans as first-class platform entities** — the bridge between an
approved **Goal** (V4-P1) and **Tasks** (V4-P4). A Plan defines *how a goal may be
achieved*. Version 4 answers **"how can an approved goal be achieved?"** before it
asks "who should perform the work?".

---

## A Plan is an intent structure — never execution
A Plan defines an approach; it is **not** execution, task completion, agent
behavior, or autonomous action. The governance gate's *risk* dimension rejects any
plan whose metadata tags carry an execution payload (`execute`, `run`, `agent`,
`job`, `process`, `autonomous`), and the service exposes no execute/run API.

## Every plan derives from an approved goal
`PlanService.create_plan` requires a source goal in `{approved, active, completed}`
(else `PlanDerivationError`). The goal's lineage node becomes the plan's lineage
parent, so a plan traces back through the goal — and the operational intelligence
the goal derived from — to the **patient**.

## Domain model
`PlanIdentity` (`plan+{hash16}`), `PlanRecord` (the mutable aggregate),
`PlanMetadata`, `PlanCategory` + `PlanPriority` (taxonomy), `PlanVersion`,
`PlanLifecycleState`, `PlanDependency` (= `PlanRelationship`), `PlanGovernanceRecord`,
`PlanAuditRecord`, `PlanLineageRecord`, `PlanRegistryRecord`. Each entity declares its
schema, validation, version, audit, and lineage rules (`schemas/contracts.py`).

## Hierarchical taxonomy (`taxonomy/`)
A closed, versioned hierarchy with `strategic` as the apex, refined by `operational`
→ {`workflow`, `quality`, `knowledge`, `analytics`} and `governance` → {`risk`}.
Priorities: `low|medium|high|critical`. Relation types: `depends_on`, `supports`,
`blocks`, `requires`, `derived_from`, `influences`.

## Lifecycle (`lifecycle/`)
`PROPOSED → DRAFT → UNDER_REVIEW → APPROVED → READY → {SUSPENDED, COMPLETED} →
ARCHIVED` (ARCHIVED terminal; SUSPENDED↔READY; UNDER_REVIEW→DRAFT revise). Forbidden
transitions raise `PlanLifecycleError`. The APPROVED / READY / SUSPENDED / COMPLETED
transitions are **policy-governed**; a plan cannot become **READY** without
governance approval.

## Dependencies (`dependencies/`)
Versioned dependency edges with cycle detection over `depends_on`/`requires` (a
cycle is a planning defect the validator's *dependency integrity* dimension rejects);
plus a deterministic `topological_order`.

## Governance, registry, audit, lineage, validation
- **Governance gate** (`governance/`): architecture / quality / context / risk /
  governance — reuses the shared `ml.validation.ValidationReport`.
- **Registry** (`registry/`): no plan exists outside it; silent overwrite forbidden;
  also tracks versioned dependencies.
- **Audit / lineage**: the shared `ImmutableAuditLog` + `ml.lineage.LineageTracker`;
  `verify_chain` reaches the patient.
- **Validation** (`validation/`): the eight integrity dimensions — identity,
  lifecycle, registry, dependency, governance, audit, lineage, version.

## Goal ↔ Plan integration
`PlanService(policy_decider=...)` accepts an injected decider. The V4-P2 policy
engine provides `backend.policy_engine.plan_policy_decider` (with
`install_default_plan_policies`), so **every ready plan is policy governed** without
`planning_foundation` importing `policy_engine`.

## Quick start
```python
from backend.planning_foundation import PlanService, PlanMetadata, PlanCategory, PlanLifecycleState
ps = PlanService(lineage_tracker=shared_tracker, policy_decider=plan_decider)
plan = ps.create_plan(category=PlanCategory.WORKFLOW, plan_key="cut-latency",
                      metadata=PlanMetadata(title="Cut Latency", approach="reorder review queue",
                                            expected_outcome="lower latency"),
                      source_goal_id=goal.goal_id, source_goal_lineage_id=goal.lineage_id,
                      source_goal_state=goal.state.value)
for st in (PlanLifecycleState.DRAFT, PlanLifecycleState.UNDER_REVIEW,
           PlanLifecycleState.APPROVED, PlanLifecycleState.READY):
    ps.transition(plan, st)
assert ps.validate(plan).ok
```

Run the tests: `pytest tests/test_planning_foundation.py`.
See [`docs/V4_P3_PLANNING_FOUNDATION.md`](./docs/V4_P3_PLANNING_FOUNDATION.md).

## Scope guard (NOT built — NR-13)
No agents, execution, monitoring, simulation, or autonomous action. Plans are intent
structures; they never act.
