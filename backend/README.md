# `backend/` — Application Layer

> **Layer:** Application Layer
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** Boundary contract defined.
> **Status (V1-P7):** **Offline implementation present** — `offline_inference/` (see "V1 Offline Implementation" below). Clinical/API/deployment remain V2+.
> **Governing docs:** AP-4 (preserve uncertainty), AP-5/AP-8 (traceability/auditability), AP-7 (boundaries), NR-4, NR-11, [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md)

The **orchestration and service** layer. It composes the domain modules
(`ml`, `evaluation`, `datasets`, `preprocessing`) into application services and
exposes them via APIs to the presentation layer — **preserving uncertainty and
provenance** end-to-end.

---

## Purpose
Provide application services and APIs that orchestrate domain logic and deliver
**traceable, uncertainty-bearing** results to the frontend.

## Responsibilities
- Orchestrate domain modules into use cases (e.g. "process recording → detect →
  attach uncertainty → record provenance").
- Expose **API contracts** to `frontend/` (the frontend talks only to the backend).
- **Preserve** uncertainty produced by `ml/` without flattening it (AP-4, NR-4).
- Maintain the **audit trail / provenance** for every clinical output (AP-5/AP-8, NR-11).
- Enforce that clinical outputs are traceable to input + preprocessing version +
  model version + uncertainty.

## Allowed dependencies
- ✅ `ml/`, `evaluation/`, `datasets/`, `preprocessing/`.
- ✅ Pinned third-party service/web/storage libraries.

## Forbidden dependencies
- ❌ `frontend/` — the dependency is one-way: **frontend depends on backend, never
  the reverse** (NR-8).
- ❌ `deployment/`, `monitoring/` as code imports — backend emits telemetry; it
  does not import the infrastructure that observes it.
- ❌ Dropping/altering uncertainty (NR-4) or producing untraceable outputs (NR-11).

## Future responsibilities
- **V2:** clinical-workflow services, API contracts, audit-trail implementation.
- **V3:** near-real-time ingestion/inference orchestration.
- **V4:** hospital-grade service hardening (security, reliability) for deployment.

## Version ownership
- **Introduced/owned from V2.** Contract defined in **V0-P2** (this README).

## Examples
- A service that accepts a recording reference, runs the `ml` inference path, and
  returns detections **with** their uncertainty and provenance.
- An API endpoint returning a prioritized review queue for clinicians (V2).
- An audit-record writer that logs the lineage of every served result.

## Boundary rules
- May import all domain modules (`ml`, `evaluation`, `datasets`, `preprocessing`);
  must **not** import `frontend/` (see the acyclic
  [dependency graph](../docs/architecture/DEPENDENCY_GRAPH.md)).
- Communicates with `frontend/` **only via defined API contracts**, never by
  sharing internal code.
- Must **preserve** uncertainty and provenance; it may not collapse a prediction
  set to a bare label.
- Does not implement DSP (`preprocessing/`), modeling (`ml/`), or metric
  computation (`evaluation/`) itself — it orchestrates them.


---

## V1 Offline Implementation (V1-P7)

> A **governed scope extension**: the directive introduces an *offline* application
> layer in V1. The architecture is **populated, not re-layered** (AP-1). Decision:
> [`../.gcc/decisions/ADR-0002`](../.gcc/decisions/ADR-0002-v1-p7-p8-offline-inference-and-research-app.md).

`backend/offline_inference/` is the **Offline Inference Platform** — a deterministic
15-stage orchestration of every V1 subsystem (raw EEG → registered intelligence
output), with an inference registry, checksummed artifacts, content-addressed
lineage, 7-check validation, six reports, and a recoverable job system.

- **Offline only.** No APIs, networking, real-time, multi-user, or clinical
  deployment (V2+).
- **Boundary.** Imports `ml`/`evaluation`/`datasets`/`preprocessing` and composes
  them; **never** imports `frontend` (enforced by `tests/test_boundaries.py`).
- **Run:** `python -m scripts.run_offline_inference --render-app` ·
  `python -m scripts.verify_v1`.

See [`offline_inference/README.md`](./offline_inference/README.md).


---

## V2 Clinical Workflow (V2-P1 + V2-P2)

> Version 2 models the **clinical workflow** (not deployment/FHIR/EMR/real-time).
> Decision: [`../.gcc/decisions/ADR-0003`](../.gcc/decisions/ADR-0003-v2-p1-p2-clinical-case-and-review.md).

The backend gains two clinical subsystems built on the certified V1 platform:

- **`clinical_cases/`** (V2-P1) — the **Case** as the first-class object:
  Patient → Case → Study, with content-addressed identities, an 8-state lifecycle,
  an immutable tamper-evident audit log, a registry, shared lineage, 7-check
  validation, and reports. Links a V1 inference run as a Study.
- **`clinical_review/`** (V2-P2) — structured human **Review**: 8-state workflow,
  sessions, assignment, tracking, registry, audit, lineage, 7-check validation, and
  reports. Shares the case's lineage tracker.

Together they execute the required deliverable with complete traceability:
Patient → Case → Study → Inference Artifacts → Review Session → Review Lifecycle →
Audit Trail → Lineage Trail.

- **Boundary.** Both import `ml` + the sibling clinical subsystem and integrate with
  `offline_inference`; neither imports `frontend`.
- **Run:** `python -m scripts.run_clinical_workflow` · `python -m scripts.verify_v2`.

See [`clinical_cases/README.md`](./clinical_cases/README.md) and
[`clinical_review/README.md`](./clinical_review/README.md).


---

## V2 Findings & Knowledge (V2-P3 + V2-P4)

> Adds clinical *meaning* on top of the case/review workflow. Decision:
> [`../.gcc/decisions/ADR-0004`](../.gcc/decisions/ADR-0004-v2-p3-p4-findings-and-knowledge.md).

- **`clinical_findings/`** (V2-P3) — the **Finding**: a structured clinical
  observation **linked to evidence** (never a prediction/diagnosis/recommendation),
  with a separate **Interpretation** entity, an 8-state lifecycle, mandatory
  evidence, immutable audit, shared lineage, 7-check validation, and reports.
- **`clinical_knowledge/`** (V2-P4) — structured **Knowledge**: terminology,
  concepts, taxonomy, a practical ontology, and typed relationships (data, not
  hidden code; not a diagnosis engine), with audit, lineage, registry, 7-check
  validation, and reports.

Together they complete the deliverable chain with full traceability:
Patient → Case → Study → Review → Evidence → Finding → Interpretation → Knowledge
Context → Audit Trail → Lineage Trail.

- **Boundary.** Both import `ml` + the sibling clinical subsystems and integrate via
  the shared lineage tracker; neither imports `frontend`.
- **Run:** `python -m scripts.run_clinical_knowledge_workflow` ·
  `python -m scripts.verify_v2_p3_p4`.

See [`clinical_findings/README.md`](./clinical_findings/README.md) and
[`clinical_knowledge/README.md`](./clinical_knowledge/README.md).



---

## V3 Operational Intelligence (V3-P1 … V3-P6)

> Version 3 makes the platform understand its own **operation**: events, time,
> workflows, structure, intelligence, and recommendations. Every subsystem is
> *derived* from the governed artifacts below it, shares the single
> `ml.lineage.LineageTracker` and the shared `ImmutableAuditLog` (no parallel
> lineage/audit), and is deterministic (logical clock, never wall-clock). Decisions:
> [`../.gcc/decisions/ADR-0007`](../.gcc/decisions/ADR-0007-v3-p1-p2-events-and-temporal.md),
> [`ADR-0008`](../.gcc/decisions/ADR-0008-v3-p3-p4-workflow-and-graph.md),
> [`ADR-0009`](../.gcc/decisions/ADR-0009-v3-p5-p6-analytics-and-recommendations.md).

- **`operational_events/`** (V3-P1) — **events** as first-class facts, observed from
  the V2 audit logs (events observe; they do not own).
- **`temporal_intelligence/`** (V3-P2) — timelines, histories, evolution, and
  temporal analytics derived from events (durations in logical steps).
- **`workflow_intelligence/`** (V3-P3) — the **workflow** as a first-class entity:
  transitions, dependencies, bottlenecks, efficiency.
- **`operational_graph/`** (V3-P4) — the platform-wide **operational graph** (a
  structured model; no graph-only truth, no UI).
- **`operational_analytics/`** (V3-P5) — **derived operational intelligence**:
  metrics, health, performance, quality, trends, and risk **scores**. Analytics is
  derived and never a source of truth. *Intelligence only — no recommendations.*
- **`operational_recommendations/`** (V3-P6) — **explainable operational
  recommendations**: guidance, prioritization, optimization suggestions, and
  escalation candidates. Evidence-linked + analytics-linked; **suggestions only**
  (never executed, never auto-escalated); operational, never clinical.

Together they execute the V3 deliverable chain with complete traceability:
Patient → Case → Review → Finding → Knowledge → Decision → Event → Timeline →
Workflow → Graph → **Operational Analytics → Operational Risks → Operational
Recommendations**.

- **Boundary.** All import `ml` + sibling V3/V2 subsystems they derive from; none
  imports `frontend` (enforced by `tests/test_boundaries.py`).
- **Run:** `python -m scripts.verify_v3_p5_p6` (and `verify_v3_p1_p2`,
  `verify_v3_p3_p4`).

See [`operational_analytics/README.md`](./operational_analytics/README.md) and
[`operational_recommendations/README.md`](./operational_recommendations/README.md).


---

## V4 Goals & Policies (V4-P1 + V4-P2)

> Version 4 begins by asking **"why does work exist?"** (Goals) and stating explicit
> **boundaries** on what may happen (Policies/Constraints) — **before** any planning
> or execution. Decision:
> [`../.gcc/decisions/ADR-0011`](../.gcc/decisions/ADR-0011-v4-p1-p2-goals-and-policies.md).

The backend gains two foundational V4 subsystems built on the certified V3 platform:

- **`goal_intelligence/`** (V4-P1) — the **Goal** as a first-class entity: *intent*,
  a desired outcome, **never execution**. Hierarchical taxonomy (strategic apex), an
  eight-state governed lifecycle (PROPOSED→…→ACTIVE→…→ARCHIVED), versioned
  relationships, governance, registry, audit, shared lineage, 8-check validation,
  and reports. A goal cannot become ACTIVE without policy-governed approval.
- **`policy_engine/`** (V4-P2) — the **safety system**: explicit, declarative,
  **explainable** policies and constraints (ALLOWED/FORBIDDEN/REQUIRED/ESCALATED/
  DEFERRED/CONDITIONAL) with a deterministic evaluation engine (PERMITTED/DENIED/
  REQUIRES_REVIEW/ESCALATED/CONDITIONAL_APPROVAL), governance, registry, audit,
  shared lineage, 8-check validation, and reports.

Together they execute the V4 deliverable chain with complete traceability:
Patient → Case → Review → Finding → Knowledge → Decision → Event → Timeline →
Workflow → Graph → Analytics → Recommendations → **Goal → Policy → Constraint →
Governance**.

- **Goal ↔ Policy integration.** `goal_intelligence` stays policy-agnostic (it
  accepts an injected decider); `policy_engine.integration` supplies a decider backed
  by real ACTIVE policies — so **every active goal is policy governed**, deterministic,
  audited, and lineage-tracked, without a coupling cycle.
- **Boundary.** Both import `ml` + sibling `backend` subsystems; neither imports
  `frontend`. No autonomous execution/agents/planning (those are later phases).
- **Run:** `python -m scripts.verify_v4_p1_p2`.

See [`goal_intelligence/README.md`](./goal_intelligence/README.md) and
[`policy_engine/README.md`](./policy_engine/README.md).



---

## V4 Plans & Tasks (V4-P3 + V4-P4)

> Version 4 continues by asking **"how can an approved goal be achieved?"** (Plans)
> and breaking that into **governed units of future work** (Tasks) — **before** any
> agent, assignment, or execution. Decision:
> [`../.gcc/decisions/ADR-0012`](../.gcc/decisions/ADR-0012-v4-p3-p4-planning-and-tasks.md).

The backend gains two more foundational V4 subsystems built on the goal + policy
foundation:

- **`planning_foundation/`** (V4-P3) — the **Plan** as the bridge between a Goal and
  Tasks: *how a goal may be achieved*. An **intent structure**, never execution.
  Hierarchical taxonomy (strategic apex), an eight-state governed lifecycle
  (PROPOSED→…→READY→…→ARCHIVED), versioned dependencies (cycle-checked), governance,
  registry, audit, shared lineage, 8-check validation, and reports. Every plan
  **derives from an approved goal**; a plan cannot become READY without
  policy-governed approval.
- **`task_intelligence/`** (V4-P4) — the **Task** as the atomic unit of *future*
  execution: it **describes work; it does not perform work**. Same governed shape
  with a `BLOCKED` operational dependency state. Every task **derives from a ready
  plan**; a task cannot become READY without policy-governed approval.

Together they execute the V4 deliverable chain with complete traceability:
Patient → Case → Review → Finding → Knowledge → Decision → Event → Timeline →
Workflow → Graph → Analytics → Recommendations → Goal → Policy → Constraint →
**Plan → Task → Governance**.

- **Goal ↔ Plan ↔ Task integration.** `planning_foundation` and `task_intelligence`
  stay policy-agnostic (each accepts an injected decider); `policy_engine.integration`
  supplies `plan_policy_decider`/`task_policy_decider` backed by real ACTIVE policies
  — so **every ready plan and task is policy governed**, deterministic, audited, and
  lineage-tracked, with no coupling cycle.
- **Boundary.** Both import `ml` + sibling `backend` subsystems; neither imports
  `frontend`. No agents/execution/monitoring/simulation (those are later phases).
- **Run:** `python -m scripts.verify_v4_p3_p4`.

See [`planning_foundation/README.md`](./planning_foundation/README.md) and
[`task_intelligence/README.md`](./task_intelligence/README.md).



---

## V4 Agents & Execution (V4-P5 + V4-P6)

> Version 4 continues by answering **"who can perform work?"** (Agents) and modeling
> the **governed progression of approved work** (Execution) — **without** autonomous
> agents or autonomous action. Decision:
> [`../.gcc/decisions/ADR-0013`](../.gcc/decisions/ADR-0013-v4-p5-p6-agents-and-execution.md).

The backend gains two more foundational V4 subsystems built on the goal / policy /
plan / task foundation:

- **`agent_coordination/`** (V4-P5) — the **Agent** as a first-class governed
  participant (human / system / service / future-AI), with declared **capabilities**
  (mode + risk; high-risk requires approval) and **assignments**. Agents describe
  capability and hold **no autonomous authority**. Hierarchical taxonomy (participant
  apex), an eight-state governed lifecycle (PROPOSED→…→AVAILABLE→…→ARCHIVED),
  governance, registry, audit, shared lineage, 9-check validation, and reports. An
  agent cannot become AVAILABLE without policy-governed approval; every assignment
  must satisfy the target's capability requirements and **never implies execution**.
- **`execution_orchestration/`** (V4-P6) — **Execution** as the *governed
  progression of approved work*. Coordinates already-approved goal/plan/task/agent/
  assignment artifacts through a nine-state governed lifecycle (PROPOSED→QUEUED→
  AUTHORIZED→ACTIVE→{PAUSED,BLOCKED,COMPLETED,TERMINATED}→ARCHIVED); **cannot become
  ACTIVE without authorization**; references an approved agent assignment; **monitoring
  observes but never modifies**. Governance, registry, audit, shared lineage, 9-check
  validation, and reports.

Together they complete the V4 deliverable chain with complete traceability:
Patient → Case → Review → Finding → Knowledge → Decision → Event → Timeline →
Workflow → Graph → Analytics → Recommendations → Goal → Policy → Constraint → Plan →
Task → **Agent → Execution → Governance**.

- **Task ↔ Agent ↔ Execution integration.** `agent_coordination` and
  `execution_orchestration` stay policy-agnostic (each accepts an injected decider);
  `policy_engine.integration` supplies `agent_policy_decider`/`execution_policy_decider`
  backed by real ACTIVE policies — so **every available agent and active execution is
  policy governed**, deterministic, audited, and lineage-tracked, with no coupling
  cycle.
- **Boundary.** Both import `ml` + sibling `backend` subsystems; neither imports
  `frontend`. No autonomous/self-modifying agents, no autonomous action, no simulation
  (those are out of scope).
- **Run:** `python -m scripts.verify_v4_p5_p6`.

See [`agent_coordination/README.md`](./agent_coordination/README.md) and
[`execution_orchestration/README.md`](./execution_orchestration/README.md).
