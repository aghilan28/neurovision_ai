# `backend/task_intelligence/` — Task Intelligence Layer (V4-P4)

> **Layer:** Application (`backend/`) — a V4 subsystem
> **Status:** Implemented (V4-P4)
> **Governing docs:** AP-3/AP-6 (determinism/reproducibility), AP-5/AP-8 (traceability/
> audit), AP-7/NR-8 (boundaries), AP-9/AP-11 (governance), NR-9/NR-10/NR-13; ADR-0012

Introduces **Tasks as first-class governed work entities** — the atomic units of
*future* execution, derived from a ready **Plan** (V4-P3). A Task **describes work;
it does not perform work**.

---

## A Task describes work — it never executes
A Task is the atomic unit of future execution; it is **not** an agent, an execution,
a job, or a process. The governance gate's *risk* dimension rejects any task whose
metadata tags carry an execution payload (`execute`, `run`, `agent`, `job`,
`process`, `autonomous`, `invoke`), and the service exposes no execute/run API.

## Every task derives from a ready plan
`TaskService.create_task` requires a source plan in `{ready, completed}` (else
`TaskDerivationError`). The plan's lineage node becomes the task's lineage parent, so
a task traces back through plan → goal → operational intelligence → the **patient**.

## Domain model
`TaskIdentity` (`task+{hash16}`), `TaskRecord` (the mutable aggregate),
`TaskMetadata`, `TaskCategory` + `TaskPriority` (taxonomy), `TaskVersion`,
`TaskLifecycleState`, `TaskDependency` (= `TaskRelationship`), `TaskGovernanceRecord`,
`TaskAuditRecord`, `TaskLineageRecord`, `TaskRegistryRecord`. Each entity declares its
schema, validation, version, audit, and lineage rules (`schemas/contracts.py`).

## Hierarchical taxonomy (`taxonomy/`)
A closed, versioned hierarchy with `operational` as the apex, refined by `workflow`,
`governance` → {`risk`}, `quality` → {`validation`}, `knowledge`, `analytics`.
Priorities: `low|medium|high|critical`. Relation types: `depends_on`, `blocks`,
`supports`, `requires`, `derived_from`, `influences`.

## Lifecycle (`lifecycle/`)
`PROPOSED → DRAFT → UNDER_REVIEW → APPROVED → READY → {BLOCKED, COMPLETED} →
ARCHIVED` (ARCHIVED terminal; BLOCKED↔READY; UNDER_REVIEW→DRAFT revise). Forbidden
transitions raise `TaskLifecycleError`. The APPROVED / READY / COMPLETED transitions
are **policy-governed**; a task cannot become **READY** without governance approval.
**BLOCKED** is a non-governed *operational dependency* state — never an execution
state.

## Dependencies (`dependencies/`)
Versioned dependency edges with cycle detection over `depends_on`/`requires`; plus a
deterministic `topological_order`.

## Governance, registry, audit, lineage, validation
- **Governance gate** (`governance/`): architecture / quality / context / risk /
  governance — reuses the shared `ml.validation.ValidationReport`.
- **Registry** (`registry/`): no task exists outside it; silent overwrite forbidden;
  also tracks versioned dependencies.
- **Audit / lineage**: the shared `ImmutableAuditLog` + `ml.lineage.LineageTracker`;
  `verify_chain` reaches the patient.
- **Validation** (`validation/`): the eight integrity dimensions — identity,
  lifecycle, registry, dependency, governance, audit, lineage, version.

## Plan ↔ Task integration
`TaskService(policy_decider=...)` accepts an injected decider. The V4-P2 policy
engine provides `backend.policy_engine.task_policy_decider` (with
`install_default_task_policies`), so **every ready task is policy governed** without
`task_intelligence` importing `policy_engine`.

## Quick start
```python
from backend.task_intelligence import TaskService, TaskMetadata, TaskCategory, TaskLifecycleState
ts = TaskService(lineage_tracker=shared_tracker, policy_decider=task_decider)
task = ts.create_task(category=TaskCategory.WORKFLOW, task_key="reorder",
                      metadata=TaskMetadata(title="Reorder", work_definition="reorder review queue"),
                      source_plan_id=plan.plan_id, source_plan_lineage_id=plan.lineage_id,
                      source_plan_state=plan.state.value, source_goal_id=plan.source_goal_id)
for st in (TaskLifecycleState.DRAFT, TaskLifecycleState.UNDER_REVIEW,
           TaskLifecycleState.APPROVED, TaskLifecycleState.READY):
    ts.transition(task, st)
assert ts.validate(task).ok
```

Run the tests: `pytest tests/test_task_intelligence.py`.
See [`docs/V4_P4_TASK_INTELLIGENCE.md`](./docs/V4_P4_TASK_INTELLIGENCE.md).

## Scope guard (NOT built — NR-13)
No agent registry/capabilities/assignment, execution engine, execution monitoring,
simulation, or autonomous action. Tasks describe work; they never act.
