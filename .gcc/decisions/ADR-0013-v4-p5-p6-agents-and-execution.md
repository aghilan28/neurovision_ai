# ADR-0013 — V4-P5 Agent Coordination Framework + V4-P6 Execution Orchestration Layer

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** V4-P5 + V4-P6
> **Builds on:** ADR-0001 … ADR-0012
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-3/AP-6/NR-9/NR-10
> (determinism/reproducibility), AP-5/AP-8/NR-11 (traceability/audit), AP-7/NR-8
> (boundaries), AP-9/NR-5 (this record), AP-11 (mechanized governance), NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the V4-P5 Agent Coordination Framework and the V4-P6 Execution
Orchestration Layer are shaped as they are, so the rationale survives turnover
(NR-14).

---

## 1. Context

V4-P1…P4 gave the platform **intent** (Goals), the **safety system** (Policies &
Constraints), **how an approved goal is achieved** (Plans), and the **atomic units
of work** (Tasks). It still could not answer **"who can perform work?"** nor model
the **governed progression of approved work**. V4-P5 introduces **Agents**
(capabilities + assignments) and V4-P6 introduces **Execution** — and nothing else.

These two phases must **evolve** the existing foundations — not redesign prior
phases, not replace goal/policy/plan/task semantics, not bypass governance, and
above all **not create autonomous systems**: agents are not self-modifying or
unbounded executors, and execution is not autonomous action, self-directed
operation, or agent freedom.

## 2. Decisions

### D1 — Two new `backend` subsystems, vertical population only (AP-1)
`backend/agent_coordination` (V4-P5) and `backend/execution_orchestration` (V4-P6)
populate the Application layer, mirroring the V4 goal/plan/task subsystems' shape.
They import `ml` + sibling `backend` subsystems; never `frontend` (enforced by
`tests/test_boundaries.py`). No layer is added or re-drawn.

### D2 — Agents are governed participants that describe capability, not authority
An **Agent** (human / system / service / future-AI participant) declares
**capabilities** (mode allowed/restricted/required; risk low→critical) and may hold
**assignments**, but it holds **no autonomous authority**. The governance gate's
*risk* dimension fails any agent carrying an autonomy/execution payload, and a
high/critical-risk capability must be **capability-approved** before the agent can
become AVAILABLE. An agent moves PROPOSED → DRAFT → UNDER_REVIEW → APPROVED →
AVAILABLE → {SUSPENDED, RETIRED} → ARCHIVED; AVAILABLE is policy-governed.

### D3 — Assignments match capability and never imply execution (Task ↔ Agent)
An **assignment** (Agent → Task/Plan/Goal/Policy) records that an available agent is
associated with a unit of work in a state (assigned/pending/blocked/revoked/
completed). The service refuses to assign unless the agent is AVAILABLE and
**satisfies the target's required capabilities** (else `AgentCapabilityError`). An
assignment is a reference, **not** execution — there is no execute/run API.

### D4 — Execution is the governed progression of approved work, never autonomous
An **Execution** coordinates already-approved artifacts (goal/plan/task/agent/
assignment) and progresses them through PROPOSED → QUEUED → AUTHORIZED → ACTIVE →
{PAUSED, BLOCKED, COMPLETED, TERMINATED} → ARCHIVED. It **cannot become ACTIVE
without authorization** (policy-governed), references an **approved agent
assignment** whose state is progressable, and performs **no autonomous planning**
(coordination references existing artifacts; it never creates them). The gate's
*risk* dimension fails any execution carrying an autonomy/self-direction payload.

### D5 — Monitoring observes; it never modifies
`execution_orchestration.monitoring` derives a read-only `ExecutionStatus` (a
deterministic, state-derived [0,1] progress index plus observed blocking conditions/
risks/escalations/outcome). It is a projection — it never mutates execution truth.

### D6 — Agent/Execution ↔ Policy integration via injected deciders (no coupling cycle)
The agent and execution subsystems stay policy-agnostic: each accepts an injected
`policy_decider`. `policy_engine.integration` adds `agent_policy_decider` and
`execution_policy_decider`, backed by real ACTIVE policies (one per governed hook:
agent_approval/availability/suspension/retirement;
execution_authorization/activation/completion/termination). A governed transition
therefore triggers a real, deterministic, audited, lineage-tracked policy evaluation
— **every available agent and active execution is policy governed** — without
`agent_coordination` or `execution_orchestration` importing `policy_engine`. The
shared installer/decider helpers are reused by goal/plan/task/agent/execution.

### D7 — One shared lineage tracker + one shared audit; deterministic throughout
Both subsystems share the platform's single `ml.lineage.LineageTracker` and the
shared `ImmutableAuditLog` (parameterised with their own record types). An
assignment node parents the agent + task nodes; an execution node parents the
assignment node — so `verify_chain` from an agent assignment or an execution reaches
the patient. No wall-clock; all ids/versions are content-addressed, so identical
inputs reproduce identical artifacts. Each carries its own 9-dimension validator.

## 3. Consequences

- The required deliverable executes with complete traceability: Patient → Case →
  Review → Finding → Knowledge → Decision → Event → Timeline → Workflow → Graph →
  Analytics → Recommendations → Goal → Policy → Constraint → Plan → Task → **Agent →
  Execution → Governance** (`python -m scripts.verify_v4_p5_p6` → all 25 criteria PASS).
- Acyclic DAG preserved; the new subsystems import `ml` + intra-`backend` only,
  never `frontend`. V4-P1…P4 (and V0–V3) remain intact — agents/executions only
  *read* and *extend* the shared lineage/audit. 488 tests pass (was 446, +42).

## 4. Scope guard (explicitly NOT built — NR-13)

Self-modifying agents, autonomous goal creation, autonomous planning, autonomous
policy changes, simulation engine, scenario engine, and any Version 5 feature.
Agents describe capability and hold no autonomous authority; execution is the
governed progression of approved work and never acts autonomously.

## 5. Follow-ups / recorded debt (NR-2)

- A future phase may add real adapters that *enact* an authorized execution against
  an external worker (still gated by this layer's authorization), keeping the
  domain/`frontend` boundary intact.
- Durable, checksummed persistence for the agent/execution registries (the inherited
  V2/V3 Gap G3) remains the natural next increment.
- A workstation surface for agents/executions can be added in `frontend` via the
  snapshot pattern (no domain import), when a presentation phase calls for it.
