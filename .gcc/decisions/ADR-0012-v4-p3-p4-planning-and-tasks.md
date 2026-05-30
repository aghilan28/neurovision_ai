# ADR-0012 — V4-P3 Planning Foundation + V4-P4 Task Intelligence Layer

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** V4-P3 + V4-P4
> **Builds on:** ADR-0001 … ADR-0011
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-3/AP-6/NR-9/NR-10
> (determinism/reproducibility), AP-5/AP-8/NR-11 (traceability/audit), AP-7/NR-8
> (boundaries), AP-9/NR-5 (this record), AP-11 (mechanized governance), NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the V4-P3 Planning Foundation and the V4-P4 Task Intelligence Layer are
shaped as they are, so the rationale survives turnover (NR-14).

---

## 1. Context

V4-P1/P2 gave the platform **intent** (Goals) and the **safety system** (Policies &
Constraints). It could answer *why work exists* and *what is allowed*, but not *how
an approved goal can be achieved* nor *what the atomic units of that work are*.
V4-P3/P4 add exactly those two layers — **Plans** and **Tasks** — and nothing else.

These two phases must **evolve** the existing foundations — not redesign prior
phases, not replace goal/policy semantics, not bypass governance, and above all
**not create agents, execution, monitoring, or simulation** (those are later
phases). The platform must answer "*how can an approved goal be achieved?*" (Plan)
and break that into governed units of *future* work (Task) — before it ever asks
"*who performs the work?*".

## 2. Decisions

### D1 — Two new `backend` subsystems, vertical population only (AP-1)
`backend/planning_foundation` (V4-P3) and `backend/task_intelligence` (V4-P4)
populate the Application layer, mirroring the V4-P1 goal subsystem's shape. They
import `ml` + sibling `backend` subsystems; never `frontend` (enforced by
`tests/test_boundaries.py`). No layer is added or re-drawn.

### D2 — Plans are intent structures; Tasks describe work — neither executes
A **Plan** defines *how a goal may be achieved* (an intent structure), and a **Task**
is the atomic unit of *future* execution that *describes* work. Neither performs
work, runs an agent, or takes autonomous action. The governance gates' *risk*
dimension fails any plan/task whose metadata tags carry an execution payload
(execute / run / agent / job / process / autonomous / invoke), and the services
expose no execute/run API.

### D3 — Governed lifecycles with READY as the admission gate
Plans: PROPOSED → DRAFT → UNDER_REVIEW → APPROVED → READY → {SUSPENDED, COMPLETED} →
ARCHIVED. Tasks: PROPOSED → DRAFT → UNDER_REVIEW → APPROVED → READY → {BLOCKED,
COMPLETED} → ARCHIVED. Forbidden transitions raise an error and are never silently
allowed. **READY means "ready for work to be derived / dispatched", never
"executing".** Task **BLOCKED** is a non-governed *operational dependency* state
(a READY task whose dependencies are unmet), not an execution state.

### D4 — Derivation invariants: Plan ⇐ approved Goal, Task ⇐ ready Plan
Every plan derives from a goal in `{approved, active, completed}` (else
`PlanDerivationError`); every task derives from a plan in `{ready, completed}` (else
`TaskDerivationError`). The source artifact's lineage node is the new artifact's
lineage parent, so a plan traces to its goal and a task to its plan — and through
them to the patient.

### D5 — Versioned dependencies, kept acyclic
Plan/Task dependencies are first-class, versioned, content-addressed edges
(`depends_on / supports / blocks / requires / derived_from / influences`). The
`dependencies` analyzer detects cycles among `depends_on`/`requires` edges; the
validator's *dependency integrity* dimension fails a graph containing a cycle. All
ordering is deterministic (sorted) for reproducibility.

### D6 — Plan/Task ↔ Policy integration via injected deciders (no coupling cycle)
The planning and task subsystems stay policy-agnostic: each accepts an injected
`policy_decider`. `policy_engine.integration` provides `plan_policy_decider` and
`task_policy_decider`, backed by real ACTIVE policies (one per governed hook:
plan_approval/plan_readiness/plan_suspension/plan_completion;
task_approval/task_readiness/task_completion). A governed transition therefore
triggers a real, deterministic, audited, lineage-tracked policy evaluation — **every
ready plan and task is policy governed** — without `planning_foundation` or
`task_intelligence` importing `policy_engine`. The shared installer/decider helpers
are refactored once and reused by goal/plan/task.

### D7 — One shared lineage tracker + one shared audit; deterministic throughout
Both subsystems share the platform's single `ml.lineage.LineageTracker` and the
shared `ImmutableAuditLog` (parameterised with their own record types). No
wall-clock; all ids/versions are content-addressed, so identical inputs reproduce
identical artifacts. Each carries its own 8-dimension validator
(identity/lifecycle/registry/dependency/governance/audit/lineage/version).

## 3. Consequences

- The required deliverable executes with complete traceability: Patient → Case →
  Review → Finding → Knowledge → Decision → Event → Timeline → Workflow → Graph →
  Analytics → Recommendations → Goal → Policy → Constraint → **Plan → Task →
  Governance** (`python -m scripts.verify_v4_p3_p4` → all 23 criteria PASS).
- Acyclic DAG preserved; the new subsystems import `ml` + intra-`backend` only,
  never `frontend`. V4-P1/P2 (and V0–V3) remain intact — plans/tasks only *read* and
  *extend* the shared lineage/audit. 446 tests pass (was 403, +43).

## 4. Scope guard (explicitly NOT built — NR-13)

Agent registry, agent capabilities, agent assignment, execution engine, execution
monitoring, simulation engine, autonomous actions, autonomous decisions, and any
Version 5 feature. Plans are intent structures; tasks describe work; neither acts.

## 5. Follow-ups / recorded debt (NR-2)

- A future phase may add assignment/execution **on top of** ready tasks (tasks
  define *what work*; a later layer defines *who/how it runs*), still gated by this
  policy engine.
- Durable, checksummed persistence for the plan/task registries (the inherited
  V2/V3 Gap G3) remains the natural next increment.
- A workstation surface for plans/tasks can be added in `frontend` via the snapshot
  pattern (no domain import), when a presentation phase calls for it.
