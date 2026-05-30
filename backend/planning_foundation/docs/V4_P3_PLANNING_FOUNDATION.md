# V4-P3 — Planning Foundation (design notes)

> **Phase:** V4-P3 · **Subsystem:** `backend/planning_foundation/` · **ADR:** ADR-0012

## Purpose
Make **plans** first-class: the bridge between an approved Goal and Tasks. A Plan
defines *how a goal may be achieved* — an intent structure that is versioned,
traceable, auditable, lineage-tracked, governed, deterministic, recoverable, and
**never execution**.

## Why "intent structure, not execution"
The directive forbids agents/execution in V4-P3. A Plan therefore carries metadata
(title, description, approach, expected outcome) and governance — but no action
payload. This is enforced structurally: the governance gate's *risk* dimension fails
a plan whose tags include an execution marker, and the service has no execute/run
method.

## Identity
`plan+{hash16}` derived from `(category, source_goal_id, plan_key)` — the
*definition*, not the lifecycle state — so re-declaring the same plan yields the same
id with a new content version (auditable), never an orphan. Dependencies use
`planrel+{hash16}`.

## Goal ⇒ Plan derivation
`create_plan` requires `source_goal_id`, its `source_goal_lineage_id`, and
`source_goal_state ∈ {approved, active, completed}` (the goal service owns goal
approval). The goal's lineage node is the plan's lineage parent, so
`verify_chain(plan)` spans `Patient → … → Goal → Plan`.

## Lifecycle + governance
The eight-state machine encodes a mostly-forward DAG with SUSPENDED↔READY and a
revise edge UNDER_REVIEW→DRAFT. Four transitions are **policy-governed** (hooks
plan_approval / plan_readiness / plan_suspension / plan_completion). The service
consults the injected `policy_decider`; a denial records a governance rejection and
raises `PlanGovernanceError`, blocking the move. A plan cannot reach **READY**
without approval.

## Dependencies
Versioned edges Plan → {plan, goal, policy, constraint} with relations depends_on /
supports / blocks / requires / derived_from / influences. The `dependencies`
analyzer detects cycles among ordering edges (`depends_on`/`requires`); the
validator's *dependency integrity* dimension fails a cyclic graph.

## Determinism (NR-9/NR-10)
No wall-clock. Identities, versions (`hash(state_signature, previous)`), and audit
heads are content-addressed, so identical inputs reproduce identical plans.

## Validation (eight dimensions)
identity · lifecycle · registry · dependency · governance · audit · lineage ·
version — all via the shared `ml.validation.ValidationReport`.

## Scope guard (NR-13)
No agents, execution, monitoring, simulation, autonomous decisions, or V5 features.
