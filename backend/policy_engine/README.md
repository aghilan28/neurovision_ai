# `backend/policy_engine/` — Policy & Constraint Engine (V4-P2)

> **Layer:** Application (`backend/`) — a V4 subsystem
> **Status:** Implemented (V4-P2)
> **Governing docs:** AP-3/AP-6 (determinism/reproducibility), AP-5/AP-8 (traceability/
> audit), AP-7/NR-8 (boundaries), AP-9/AP-11 (governance), NR-9/NR-10/NR-13; ADR-0011

Creates explicit **governance boundaries**: the platform now understands what is
**ALLOWED / FORBIDDEN / REQUIRED / ESCALATED** before any planning or execution can
ever exist. Policies are the **safety system** of Version 4.

---

## Deterministic + explainable — no hidden logic
Every policy and constraint is versioned, traceable, auditable, lineage-tracked,
governed, deterministic, and **explainable**. A `PolicyRule` is *data* — a
fixed-operator predicate (`eq/ne/in/not_in/exists/not_exists/ge/le/truthy`) over an
evaluation context, with **no executable code**. Every evaluation records exactly
which rules and constraints fired and why.

## Domain model
`PolicyIdentity` (`policy+{hash16}`), `PolicyRecord` (mutable aggregate),
`PolicyRule`, `ConstraintRecord` (`constraint+{hash16}`), `ConstraintCategory`
(taxonomy), `PolicyEvaluation` (`policyeval+{hash16}`), `PolicyVersion`,
`PolicyAuditRecord`, `PolicyLineageRecord`, `PolicyRegistryRecord`.

## Taxonomy (`policies/`)
- **Policy categories:** permission, prohibition, obligation, escalation, risk,
  governance, quality, workflow.
- **Constraint types:** ALLOWED, FORBIDDEN, REQUIRED, ESCALATED, DEFERRED, CONDITIONAL.
- **Policy lifecycle:** draft → under_review → approved → active → {suspended,
  deprecated} (a policy only evaluates while ACTIVE).

## Constraint engine (`constraints/`)
Builds explicit, versioned, explainable constraints of each type, with declarative
applicability rules. `FORBIDDEN` and unmet `REQUIRED` constraints block.

## Evaluation engine (`evaluation/`) — five outcomes
Deterministic precedence over the constraint types that apply in the context:

| Triggered | Outcome |
|-----------|---------|
| FORBIDDEN | `DENIED` |
| REQUIRED (unmet) | `DENIED` |
| ESCALATED | `ESCALATED` |
| DEFERRED | `REQUIRES_REVIEW` |
| CONDITIONAL | `CONDITIONAL_APPROVAL` |
| otherwise / ALLOWED | `PERMITTED` |

The same policy + request + context always reproduces the same evaluation id and
outcome, with per-rule explanations as evidence.

## Governance, registry, audit, lineage, validation
- **Governance gate** (`governance/`): architecture / quality / context / risk /
  governance. No policy becomes ACTIVE without approval.
- **Registry** (`registry/`): policies (versioned), constraints, and evaluations;
  silent overwrite forbidden.
- **Audit / lineage**: the shared `ImmutableAuditLog` + `ml.lineage.LineageTracker`.
  A policy node parents its motivating artifacts; an evaluation node parents the
  policy node **and** the governed subject node — so `verify_chain` reaches the patient.
- **Validation** (`validation/`): eight dimensions — policy, constraint, evaluation,
  registry, governance, audit, lineage, version.

## Goal ↔ Policy integration (`integration.py`)
`install_default_goal_policies(ps)` creates + activates one governed policy per goal
hook (goal_approval / goal_activation / goal_suspension / goal_completion);
`goal_policy_decider(ps, hooks)` returns the decider the `GoalService` injects — so
**every active goal is policy governed**.

## Quick start
```python
from backend.policy_engine import PolicyService, install_default_goal_policies, goal_policy_decider
ps = PolicyService(lineage_tracker=shared_tracker)
hooks = install_default_goal_policies(ps)
decider = goal_policy_decider(ps, hooks)          # inject into GoalService
```

Run the tests: `pytest tests/test_policy_engine.py`.
See [`docs/V4_P2_POLICY_ENGINE.md`](./docs/V4_P2_POLICY_ENGINE.md).

## Scope guard (NOT built — NR-13)
No planning, tasks, agents, execution, simulation, or autonomous action. Policies
decide and explain; they never act.
