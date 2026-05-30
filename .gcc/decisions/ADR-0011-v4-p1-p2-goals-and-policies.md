# ADR-0011 — V4-P1 Goal Intelligence Foundation + V4-P2 Policy & Constraint Engine

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** V4-P1 + V4-P2
> **Builds on:** ADR-0001 … ADR-0010
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-3/AP-6/NR-9/NR-10
> (determinism/reproducibility), AP-5/AP-8/NR-11 (traceability/audit), AP-7/NR-8
> (boundaries), AP-9/NR-5 (this record), AP-11 (mechanized governance), NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the V4-P1 Goal Intelligence Foundation and the V4-P2 Policy &
Constraint Engine are shaped as they are, so the rationale survives turnover
(NR-14).

---

## 1. Context

Version 3 made the platform understand its **operation** (events → timelines →
workflows → graph → analytics → recommendations). It still could not answer **why
work exists** or state explicit **boundaries** on what may happen. Version 4 begins
there — and *only* there: **Goals**, **Policies**, **Constraints**, **Governance**.
No planning, tasks, agents, execution, or simulation (those are later phases). The
platform must answer "*why does work exist?*" before "*how should work be
performed?*".

These two phases must **evolve** the existing foundations — not redesign prior
phases, not replace lineage/audit semantics, not create parallel governance, and
above all **not create autonomous execution, agents, or planning**.

## 2. Decisions

### D1 — Two new `backend` subsystems, vertical population only (AP-1)
`backend/goal_intelligence` (V4-P1) and `backend/policy_engine` (V4-P2) populate the
Application layer. They import `ml` + sibling `backend` subsystems; never `frontend`
(enforced by `tests/test_boundaries.py`). No layer is added or re-drawn.

### D2 — Goals are intent, never execution
A **Goal** is a first-class statement of *desired outcome*. It is not a
recommendation, task, plan, or execution, and **never performs actions**. The
governance gate's *risk* dimension fails any goal that carries an executable action
payload, and the goal service exposes no execute/run API. A goal moves through a
governed lifecycle (PROPOSED → DRAFT → UNDER_REVIEW → APPROVED → ACTIVE →
{SUSPENDED, COMPLETED} → ARCHIVED); forbidden transitions are blocked.

### D3 — Policies are the declarative safety system; no hidden logic
A **Policy** makes explicit what is ALLOWED / FORBIDDEN / REQUIRED / ESCALATED. A
`PolicyRule` is *data* — a fixed-operator predicate over an evaluation context, with
no executable code — so every policy and every evaluation is deterministic and
**explainable**. The evaluation engine maps a policy + its triggered constraints to
one of five outcomes (PERMITTED / DENIED / REQUIRES_REVIEW / ESCALATED /
CONDITIONAL_APPROVAL) via a fixed, transparent precedence, recording every applied
rule and triggered constraint as evidence.

### D4 — Constraints are explicit, versioned, and typed
The six constraint types (ALLOWED / FORBIDDEN / REQUIRED / ESCALATED / DEFERRED /
CONDITIONAL) are first-class, versioned, content-addressed records with declarative
applicability rules. FORBIDDEN denies; an unmet REQUIRED denies; the rest map to
their corresponding outcome. Constraints never contain hidden logic.

### D5 — Governance is real, and ACTIVE requires approval
No goal becomes ACTIVE without a policy-governed approval; no policy becomes ACTIVE
without governance approval. Both reuse the shared `ml.validation.ValidationReport`
for their architecture/quality/context/risk/governance gates — **no parallel
governance system**.

### D6 — Goal ↔ Policy integration via an injected decider (no coupling cycle)
The goal subsystem stays policy-agnostic: it accepts an injected `policy_decider`
callable. `policy_engine.integration` provides that decider, backed by real ACTIVE
policies (one per governed goal hook: goal_approval / goal_activation /
goal_suspension / goal_completion). A goal's governed transition therefore triggers
a real, deterministic, audited, lineage-tracked policy evaluation — **every active
goal is policy governed** — without `goal_intelligence` importing `policy_engine`.

### D7 — One shared lineage tracker + one shared audit; deterministic throughout
Both subsystems share the platform's single `ml.lineage.LineageTracker` and the
shared `ImmutableAuditLog` (parameterised with their own record types). A goal's
lineage parents are the analytics/recommendation nodes it derives from; a policy
evaluation's parents are the policy node and the governed goal node — so
`verify_chain` from a goal or an evaluation reaches the patient. No wall-clock; all
ids/versions are content-addressed, so identical inputs reproduce identical
artifacts.

## 3. Consequences

- The required deliverable executes with complete traceability: Patient → Case →
  Review → Finding → Knowledge → Decision → Event → Timeline → Workflow → Graph →
  Analytics → Recommendations → **Goal → Policy → Constraint → Governance**
  (`python -m scripts.verify_v4_p1_p2` → all 22 criteria PASS).
- Acyclic DAG preserved; the new subsystems import `ml` + intra-`backend` only,
  never `frontend`. V3 (and V0–V2) remain intact — goals/policies only *read* and
  *extend* the shared lineage/audit. 403 tests pass (was 363, +40).

## 4. Scope guard (explicitly NOT built — NR-13)

Planning engine, task engine, agent framework, execution engine, simulation engine,
autonomous actions, autonomous decisions, clinical automation, realtime actions, and
any Version 5 feature. Goals never execute; policies/constraints are declarative;
the engines decide and explain, they do not act.

## 5. Follow-ups / recorded debt (NR-2)

- A future phase may add planning/tasks **on top of** goals + policies (goals define
  *why*; a later layer defines *how*), still gated by this policy engine.
- Durable, checksummed persistence for the goal/policy registries (the inherited
  V2/V3 Gap G3) remains the natural next increment.
- A workstation surface for goals/policies can be added in `frontend` via the
  snapshot pattern (no domain import), when a presentation phase calls for it.
