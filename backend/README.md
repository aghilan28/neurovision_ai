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


---

## Productization P1 — Real EEG Foundation (`eeg_foundation/`)

> Productization (not a new version): the first step toward closing the inherited
> Gap **G1** ("synthetic-only data"). Decision:
> [`../.gcc/decisions/ADR-0014`](../.gcc/decisions/ADR-0014-productization-p1-real-eeg-foundation.md).

- **`eeg_foundation/`** (Productization P1) — lets a **real EEG file** enter the
  platform: it is loaded, validated, parsed, has its metadata extracted, becomes a
  content-addressed **EEG asset**, is stored, and is tracked with shared audit +
  lineage — and *nothing more* (no DSP, features, models, inference, analytics, APIs,
  or deployment). Real files are read with **MNE-Python** (no mock/fake parsers)
  across a **closed format vocabulary**: `EDF, EDF+, BDF, BDF+, FIF, SET`, detected
  from file bytes. Validation returns **structured findings, never exceptions**
  (corrupted/unreadable/unsupported/missing-channels/invalid-rate/invalid-duration/
  metadata/annotation). Storage is **local + content-addressed** (checksum +
  fingerprint + integrity verify; no cloud/S3/db). The registry admits **no orphan
  assets**. Audit reuses the shared `ImmutableAuditLog`; lineage reuses the shared
  `ml.lineage` tracker with the EEG node parented on the **case** node.

The deliverable executes with complete traceability — a registered EEG asset's chain
verifies **Patient → Case → EEG Asset**. A valid file is `REGISTERED`; a
recognized-but-undecodable file is `QUARANTINED` (still tracked); an
unreadable/unsupported file is rejected with structured findings (no silent failure).

- **Boundary.** Imports `ml` + the shared `backend.clinical_cases.audit` primitive;
  never imports `frontend`; performs no modelling/inference/DSP.
- **Run:** `python -m scripts.verify_productization_p1`.

See [`eeg_foundation/README.md`](./eeg_foundation/README.md).


---

## Productization P2 — Signal Processing Foundation (`signal_processing/`)

> Productization (built strictly on P1): turns a **raw EEG asset** into a **validated
> clean EEG asset**. Decision:
> [`../.gcc/decisions/ADR-0015`](../.gcc/decisions/ADR-0015-productization-p2-signal-processing.md).

- **`signal_processing/`** (Productization P2) — reads the **immutable** raw EEG bytes
  from the P1 store and produces a cleaned signal: it **assesses quality** (channel +
  recording scores, grade, findings, recommendations), **detects artifacts** (eye-blink,
  EMG, movement, powerline, channel dropout, flat/saturated channels → structured
  records with severity/confidence/affected-channels/onset/duration), **filters**
  (deterministic scipy bandpass/highpass/lowpass/notch/reference) and **removes
  artifacts** (self-contained deterministic ICA, adaptive filtering, interpolation,
  channel repair, noise suppression), then **stores** the clean signal in a *separate*
  content-addressed store. No AI, model training, inference, classification, or clinical
  decisions.

The deliverable executes with complete traceability — a processed asset's chain
verifies **Patient → Case → EEG → Processed**. The **raw EEG is never modified**; the
processed asset is a separate, versioned, audited, lineage-tracked record, and
`SignalIntegrityValidator` asserts raw immutability + raw → processed traceability.

- **Boundary.** Imports `ml` + `backend.eeg_foundation` types + the shared
  `backend.clinical_cases.audit` primitive; never imports `frontend`; performs signal
  processing only.
- **Run:** `python -m scripts.verify_productization_p2`.

See [`signal_processing/README.md`](./signal_processing/README.md).


---

## Productization P3 — Feature Engineering Platform (`feature_engineering/`)

> Productization (built strictly on P1 + P2): turns a **processed EEG asset** into an
> **immutable validated feature asset**. Decision:
> [`../.gcc/decisions/ADR-0016`](../.gcc/decisions/ADR-0016-productization-p3-feature-engineering.md).

- **`feature_engineering/`** (Productization P3) — reads the **immutable** processed
  signal from the P2 store and generates five families of deterministic features:
  **frequency** (band powers δ/θ/α/β/γ, relative power, band ratios, spectral entropy),
  **temporal** (mean/variance/skew/kurtosis/RMS/ZCR/Hjorth/entropy, per-channel +
  per-recording), **connectivity** (coherence/PLV/cross-correlation matrices +
  synchronization), **spectral** (PSD/spectrogram/band-summary/frequency-histogram,
  structured — no images), and **topography** (channel-layout/regional/spatial-summary/
  topographic-stat, structured — no images). It assembles an **immutable** feature
  asset, validates it (completeness/integrity/consistency/determinism +
  registry/audit/lineage/version), and registers it. No model training, model registry,
  inference, predictions, classification, or clinical decisions.

The deliverable executes with complete traceability — a feature asset's chain verifies
**Patient → Case → EEG → Processed → Feature**. The feature asset is immutable (frozen +
content-fingerprinted); determinism is *validated* by re-extracting and comparing
fingerprints.

- **Boundary.** Imports `ml` + reads the P2 store + reuses the shared
  `backend.clinical_cases.audit` primitive; never imports `frontend`; performs feature
  generation only.
- **Run:** `python -m scripts.verify_productization_p3`.

See [`feature_engineering/README.md`](./feature_engineering/README.md).


---

## Productization P4 — Model Foundation Platform (`model_foundation/`)

> Productization (built strictly on P1 + P2 + P3): turns **feature assets** into
> **validated trained models**. Decision:
> [`../.gcc/decisions/ADR-0017`](../.gcc/decisions/ADR-0017-productization-p4-model-foundation.md).

- **`model_foundation/`** (Productization P4) — assembles a **patient-disjoint** dataset
  from registered feature assets (plus an external-dataset integration framework for
  **TUH EEG / CHB-MIT / Temple EEG** — manifest based, **no download, no internet**),
  **trains** deterministic pure-NumPy baseline architectures (**EEGNet / DeepConvNet /
  Temporal CNN / Transformer**), **evaluates** them (accuracy / precision / recall / F1 /
  confusion / calibration / uncertainty), **tracks experiments**, **validates** (9
  checks), and **registers** immutable models. No production inference, serving, APIs,
  user predictions, or frontend.

The deliverable executes with complete traceability — a model's chain verifies
**Patient → Case → EEG → Processed → Feature → Dataset → Training Run → Model**. Training
is seeded + reproducible (determinism is *validated*); models are immutable
(content-addressed parameter fingerprint, not raw weights); splits are patient-disjoint.

- **Boundary.** Imports `ml` + reuses the shared `backend.clinical_cases.audit`
  primitive; never imports `frontend`; performs model creation only (no serving).
- **Run:** `python -m scripts.verify_productization_p4`.

See [`model_foundation/README.md`](./model_foundation/README.md).


---

## Productization P5 — Clinical Inference Foundation (`inference_foundation/`)

> Productization (built strictly on P1–P4): turns **feature assets + trained models**
> into **validated prediction assets**. Decision:
> [`../.gcc/decisions/ADR-0018`](../.gcc/decisions/ADR-0018-productization-p5-clinical-inference.md).

- **`inference_foundation/`** (Productization P5) — **loads + verifies** a trained model
  (deterministic reconstruction via reproducibility; parameter-fingerprint + version
  verification), runs **deterministic execution**, and generates a **prediction**
  (class + probabilities + scores), a **confidence** assessment (score / interval /
  stability / reliability / level), a **calibration** assessment (ECE + Brier +
  reliability + quality), and a **structured explanation** (feature/band/channel
  importance + decision factors — no images/UI). It assembles an **immutable** prediction
  asset, validates it (9 checks), and registers it. No APIs, serving, deployment,
  frontend, or user accounts.

The deliverable executes with complete traceability — a prediction's chain verifies
**Patient → Case → EEG → Processed → Feature → Dataset → Training Run → Model → Prediction**.
Inference is deterministic (determinism is *validated* by re-inference); prediction
assets are immutable (content-addressed; no model weights / raw signal).

- **Boundary.** Imports `ml` + reuses P4 modules + the shared
  `backend.clinical_cases.audit` primitive; never imports `frontend`; performs inference
  only (no serving).
- **Run:** `python -m scripts.verify_productization_p5`.

See [`inference_foundation/README.md`](./inference_foundation/README.md).



---

## Productization P6 — Application Backend Platform (`application_backend/`)

> Productization (built strictly on P1–P5): exposes the platform's capabilities through
> governed **application backend services** — the objective is *backend access*, nothing
> else. Decision:
> [`../.gcc/decisions/ADR-0019`](../.gcc/decisions/ADR-0019-productization-p6-application-backend.md).

- **`application_backend/`** (Productization P6) — composes the **reused** `CaseService`
  + EEG / signal / feature / model / inference services over **one** shared
  `ml.lineage.LineageTracker` and the shared `ImmutableAuditLog`, and adds local
  **authentication** (PBKDF2 password hashing, session create/validate/revoke; no social
  login/OAuth), **user management** (roles/status/metadata, audit history, lineage), an
  **EEG workflow** that *orchestrates* P1–P5 (upload → validate → process → features →
  predict → confidence → explanation, duplicating no business logic), a **versioned
  (`v1`) in-process API** (upload, list/retrieve EEG, start analysis, retrieve
  prediction/confidence/explanation, list history, list reports), **request + integrity
  validation**, in-process **storage**, a single **registry** (no orphan records),
  shared audit + lineage, and deterministic **reports**. No frontend, deployment,
  monitoring, or cloud infrastructure.

The deliverable executes through backend services only — a user authenticates, uploads a
real EEG file, triggers analysis, and retrieves a prediction + confidence + explanation;
the workflow's join lineage node yields one `verify_chain` proving
**User → Upload → EEG → Processed → Feature → Model → Prediction** (the P1–P5 chain
preserved intact). Everything except authentication secrets is content-addressed and
deterministic; secrets come from a secure-default (injectable) entropy source and never
enter a content hash, record, or report.

- **Boundary.** Imports `ml` + sibling `backend` subsystems; never imports `frontend`.
  In-process only (no HTTP/networking/serving).
- **Run:** `python -m scripts.verify_productization_p6`.

See [`application_backend/README.md`](./application_backend/README.md).



---

## DRP-1 — Real Dataset Integration (`dataset_integration/`)

> Deployment Remediation (post-audit): closes the Independent Production Reality Audit's #1
> blocker — *no real datasets integrated*. Decision:
> [`../.gcc/decisions/ADR-0024`](../.gcc/decisions/ADR-0024-drp1-real-dataset-integration.md).

- **`dataset_integration/`** (DRP-1) — a governed external-EEG-dataset lifecycle:
  **inventory → registration → validation → governance metadata → readiness → lineage →
  audit**, for the mandatory corpora (**TUH EEG, CHB-MIT, Temple/TUSZ, Siena Scalp, Bonn**)
  and any future dataset, **from local manifests only (never downloaded)**. It manages
  datasets; it trains no models and modifies no other subsystem. Reuses the model-foundation
  connector framework (cross-references its `DatasetRecord` id for supported sources), the
  shared `ml.lineage` tracker, the shared `ImmutableAuditLog`, and `ml.validation` (no
  parallel systems). Lineage chain **Source → Dataset → Version**; deterministic and audited.
- **Boundary.** Imports `ml` + sibling `backend`; never imports `frontend`.
- **Run:** `python -m scripts.verify_drp1_dataset_integration`.

See [`dataset_integration/README.md`](./dataset_integration/README.md). Verified: all 15
DRP-1 criteria pass; all five mandatory corpora **READY**; full suite **851 passed**.


## DRP-2 — Production Model Program (`production_models/`)

> Deployment Remediation (post-audit): closes the audit's *no validated models* gap by
> turning reference-grade models into **production-candidate models** with objective
> evaluation / benchmark / readiness evidence. Decision:
> [`../.gcc/decisions/ADR-0025`](../.gcc/decisions/ADR-0025-drp2-production-models.md).

- **`production_models/`** (DRP-2) — a governed program that, for each architecture,
  **builds a dataset → trains (deterministic, reproducibility verified) → tracks the
  experiment → evaluates → benchmarks → compares → scores readiness → validates → registers
  → audits → traces**. Five architectures behind one contract: `eegnet`, `deepconvnet`,
  `temporal_cnn`, `transformer_eeg` (wrappers that **reuse** the `model_foundation` reference
  models, never removed) and a new deterministic `hybrid_eeg`. It develops + validates models;
  it serves nothing and modifies no other subsystem.
- **Reuse, no parallel systems.** Reuses `model_foundation.build_feature_dataset` + base
  evaluator + reference models, the shared `DatasetRegistry` + `ModelRegistry`, the shared
  `ml.lineage` tracker, the shared `ImmutableAuditLog`, and `ml.validation`. Only the new
  production-candidate artifacts (models with benchmark + readiness, experiments, benchmarks,
  evaluations, readiness assessments) live in `ProductionModelRegistry`.
- **Determinism (NR-9/NR-10).** Deterministic metrics (accuracy/precision/recall/F1/ROC-AUC/
  PR-AUC/ECE/Brier) enter every id + signature; performance measures (latency/memory/training/
  inference time) are reported but **informational** (never hashed).
- **Traceability.** `verify_chain` from a readiness assessment proves **Patient → Case → EEG →
  Processed → Feature → Dataset → Training Run → Training Experiment → Model → Benchmark →
  Readiness Assessment**.
- **Boundary.** Imports `ml` + sibling `backend`; never imports `frontend`.
- **Run:** `python -m scripts.verify_drp2_production_models`.

See [`production_models/README.md`](./production_models/README.md). Verified: all 15 DRP-2
criteria pass; all five architectures **READY**; full suite **872 passed**.


## DRP-3 — Production Serving Platform (`serving_platform/`)

> Deployment Remediation (post-audit): closes the audit's *no serving layer* blocker with an
> inference service boundary, a model serving lifecycle, and an in-process public execution
> interface. Decision:
> [`../.gcc/decisions/ADR-0026`](../.gcc/decisions/ADR-0026-drp3-serving-platform.md).

- **`serving_platform/`** (DRP-3) — a governed serving platform that **receives a prediction
  request → selects a model (resolve / version) → executes inference → generates + delivers a
  response → tracks the lifecycle → scores readiness → traces lineage → audits the execution**.
  It serves models; it never trains them and modifies no other subsystem.
- **Reuse, no parallel systems.** Execution delegates to the reused `InferenceFoundationService`
  (no duplicated prediction logic); the response carries its prediction + confidence +
  calibration + explanation (NR-4). Serves `model_foundation` model records via the shared
  `ModelRegistry`; shares the single `ml.lineage` tracker + the shared `ImmutableAuditLog`. The
  new `ServingRegistry` stores only serving artifacts (requests/executions/responses/readiness).
- **Lifecycle (DRP3-F).** `request_created → request_validated → model_selected →
  inference_executed → response_generated → response_delivered → execution_completed`.
- **Graceful failure.** Invalid requests / missing models → a structured `Error` contract,
  audited, never a crash; the registry stays orphan-free.
- **Traceability.** `verify_chain` from a served response proves **Dataset → Feature → Model →
  Inference → Serving Request → Serving Execution → Serving Response**.
- **Boundary.** Imports `ml` + sibling `backend`; never imports `frontend`. No HTTP/networking.
- **Run:** `python -m scripts.verify_drp3_serving_platform`.

See [`serving_platform/README.md`](./serving_platform/README.md). Verified: all 15 DRP-3
criteria pass; all architectures served **READY**; full suite **891 passed**.


## DRP-4 — Persistence Platform (`persistence_platform/`)

> Deployment Remediation (post-audit): closes the audit's *no persistence layer* blocker —
> durable storage, persistent registries, and durable audit / lineage / execution history that
> survives a cold restart. Decision:
> [`../.gcc/decisions/ADR-0027`](../.gcc/decisions/ADR-0027-drp4-persistence-platform.md).

- **`persistence_platform/`** (DRP-4) — a governed platform that **persists registries + audit
  history + lineage history + execution history → recovers state on a cold restart →
  validates the recovery → scores persistence readiness**. It persists + recovers state; it
  modifies no business logic.
- **Durable storage.** A deterministic, content-addressed, **tamper-evident** filesystem store
  (canonical JSON + sha256 checksum + content fingerprint); files survive process restarts.
  No cloud / database / deployment.
- **Reuse, no parallel systems.** The shared `ImmutableAuditLog` is serialized + **replay-
  recovered** (reproduces the head); the shared `ml.lineage` tracker is serialized + **rebuilt**
  (`verify_chain` holds); the DRP-1/DRP-2/DRP-3 registries are persisted via `to_dict()`.
- **Cold-restart recovery.** A fresh service at the same storage root reads a manifest,
  checksum-verifies every object, rebuilds everything, re-verifies the chains, and records a
  `recovery_event` lineage node.
- **Traceability.** `verify_chain` from a recovery event proves **Dataset → Model → Inference →
  Serving → Persistence Record → Recovery Event**.
- **Boundary.** Imports `ml` + sibling `backend`; never imports `frontend`.
- **Run:** `python -m scripts.verify_drp4_persistence_platform`.

See [`persistence_platform/README.md`](./persistence_platform/README.md). Verified: all 15
DRP-4 criteria pass; persistence **READY**, recovery **recovered**; full suite **908 passed**.


## DRP-5 — Security Hardening & Access Control Platform (`security_platform/`)

> Deployment Remediation (post-audit): closes the audit's *insufficient security readiness*
> blocker — authentication, authorization, access control, credential protection, security
> auditing. Decision:
> [`../.gcc/decisions/ADR-0028`](../.gcc/decisions/ADR-0028-drp5-security-platform.md).

- **`security_platform/`** (DRP-5) — a governed platform that **authenticates users →
  authorizes requests (RBAC, default-deny) → evaluates policies → controls access (least
  privilege) → audits security events → traces security lineage → scores security readiness**.
  It secures the platform; it changes no business logic.
- **Credential protection.** Reuses the platform's PBKDF2 + injectable entropy
  (`application_backend.auth`); stores a salted hash + salt (never plaintext) and only a session
  token **fingerprint**. Invalid credentials / expired sessions are denied gracefully.
- **RBAC + policies.** Declarative `(role, resource_type, action) -> effect`; **default-deny**;
  a PERMITTED decision cites ≥ 1 matched policy. Least privilege over dataset / model / serving /
  persistence / administrative resources.
- **Reuse, no parallel systems.** Shares the single `ml.lineage` tracker + the shared
  `ImmutableAuditLog`.
- **Traceability.** `verify_chain` proves **User → Credential → Authentication → Authorization →
  Access Decision → Resource Access** (and reaches the patient via the accessed resource).
- **Boundary.** Imports `ml` + sibling `backend`; never imports `frontend`. No plaintext
  credential storage; secrets never enter a hash/report/audit/lineage trail.
- **Run:** `python -m scripts.verify_drp5_security_platform`.

See [`security_platform/README.md`](./security_platform/README.md). Verified: all 15 DRP-5
criteria pass; authentication/authorization/access-control all green, **READY**; full suite
**927 passed**.


## DRP-6 — Clinical Validation & Evidence Platform (`clinical_validation/`)

> Deployment Remediation (post-audit): closes the audit's *insufficient clinical validation
> evidence* blocker — benchmark / performance / reliability / calibration evidence + objective
> comparison + validation readiness. Decision:
> [`../.gcc/decisions/ADR-0029`](../.gcc/decisions/ADR-0029-drp6-clinical-validation.md).

- **`clinical_validation/`** (DRP-6) — a governed platform that, for every production model,
  **benchmarks → evaluates performance → measures reliability → measures calibration →
  generates evidence → compares models → traces validation lineage → scores validation
  readiness**. It validates + generates evidence; it never retrains models or changes business
  logic.
- **Reuse, no replacement systems.** Develops/benchmarks/evaluates/compares via the reused
  DRP-2 `ProductionModelService`; adds sensitivity/specificity (from the DRP-2 confusion matrix),
  calibration curves, and reliability studies. Shares the single `ml.lineage` tracker + the
  shared `ImmutableAuditLog`.
- **Determinism.** Clinical metrics enter every id/signature; performance timings are reported
  but never hashed.
- **Traceability.** `verify_chain` proves **Dataset → Model → Benchmark → Evaluation → Evidence
  → Readiness Assessment**, reaching the patient.
- **Boundary.** Imports `ml` + sibling `backend`; never imports `frontend`.
- **Run:** `python -m scripts.verify_drp6_clinical_validation`.

See [`clinical_validation/README.md`](./clinical_validation/README.md). Verified: all 15 DRP-6
criteria pass; every model benchmarked, evidenced, **READY**; full suite **942 passed**. The
metrics are evidence about untuned reference baselines on synthetic data (Gap G1), not a
clinical-efficacy claim.


## Track 1 — Real Data Acquisition & Integration (`dataset_acquisition/`)

> Product Completion Program: closes the Production Reality Audit V2 blocker *NO REAL
> DATASETS* — turns the DRP-1 dataset **framework** into a **Real Dataset Platform**. Decision:
> [`../.gcc/decisions/ADR-0030`](../.gcc/decisions/ADR-0030-track1-real-data-acquisition.md).

- **`dataset_acquisition/`** (Track 1) — **acquires** real public EEG corpora locally,
  **validates** them from the **actual files** (not manifests), extracts **real metadata +
  labels**, builds inventories, tracks lineage + audit, and scores **training readiness**
  (NOT_READY / PARTIALLY_READY / **READY_FOR_TRAINING**). It acquires/validates/registers/
  verifies/prepares datasets for training; it trains no models and modifies no other subsystem.
- **Reuse, no parallel systems.** Reads real recordings via the `eeg_foundation` MNE reader
  (and its content-addressed `recording+{hash16}` id); shares the single `ml.lineage` tracker +
  the shared `ImmutableAuditLog` + `ml.validation` + `ml.provenance`.
- **Acquisition policy.** Only OPEN, no-account corpora are auto-downloaded (CHB-MIT, PhysioNet).
  TUH EEG + Temple/TUSZ require a signed data-use agreement → reported, never fetched. Real
  recordings live in a **gitignored** data root (`data/real`, `$NV_DATASET_ROOT`); never committed.
- **Traceability.** `verify_chain` proves **Dataset Source → Dataset → Patient → Recording →
  Label → Registry**, reaching the source.
- **Determinism.** Ids/fingerprints are content-addressed from real file checksums + labels;
  download timings are never hashed — same files reproduce the same outcome bit-for-bit.
- **Boundary.** Imports `ml` + sibling `backend`; never imports `frontend`.
- **Run:** `python -m scripts.acquire_real_dataset` (acquire + report) and
  `python -m scripts.verify_track1_real_data` (the 15 criteria).

See [`dataset_acquisition/README.md`](./dataset_acquisition/README.md). Verified: all 15 Track 1
criteria pass against a **real, locally-acquired CHB-MIT subset** (2 genuine 1-hour recordings,
256 Hz, 23 channels; real seizure labels incl. the documented chb01_03 seizure at 2996–3036 s)
scored **READY_FOR_TRAINING**; full suite **967 passed**. Real recordings — not synthetic
fixtures — and **no synthetic labels** for that dataset.


## Track 2 — Real Model Training & Benchmark (`real_model_training/`)

> Product Completion Program: closes the audit blocker *NO MEANINGFUL TRAINED MODELS* —
> turns the **real datasets** from Track 1 into **real trained models**. Decision:
> [`../.gcc/decisions/ADR-0031`](../.gcc/decisions/ADR-0031-track2-real-model-training.md).

- **`real_model_training/`** (Track 2) — windows the **real** Track-1 recordings into labelled
  samples, **trains the platform's five architectures** (EEGNet / DeepConvNet / Temporal CNN /
  Transformer EEG / Hybrid EEG) on that real data, **evaluates** (accuracy / precision / recall /
  F1 / ROC-AUC / PR-AUC / sensitivity / specificity / confusion / calibration / reliability),
  **benchmarks**, **compares**, and scores **serving readiness** (NOT_READY / PARTIALLY_READY /
  **READY_FOR_SERVING**). It trains/evaluates/benchmarks/compares/scores; it does not serve,
  persist, secure, deploy, or modify Track 1.
- **Reuse, no new architecture.** Drives the existing `production_models` + `model_foundation`
  engines (`train_production` → `evaluate` → `benchmark_model` → `build_model_evaluation` →
  `compare_models`) on a `DatasetBundle` assembled from real windows; reuses the Track-1
  `RealDatasetService`, the single `ml.lineage` tracker, the shared `ImmutableAuditLog`,
  `ml.validation`, and `ml.provenance`.
- **Real data only.** Each window's label comes from the **real** seizure intervals; no
  synthetic training. (The five reused architectures are feature-projection models, so each
  window is reduced to a deterministic per-channel band-power + temporal feature vector before
  training — the binding constraint of reusing the existing models, documented in ADR-0031.)
- **Traceability.** `verify_chain` proves **Dataset → Recording → Feature Asset → Training Run →
  Model → Evaluation → Benchmark → Readiness Assessment**, reaching the Track-1 dataset source.
- **Determinism.** Content-addressed ids; reproducibility verified (train twice, compare
  fingerprints); deterministic metrics hashed, wall-clock timings informational + excluded from
  signatures and from the deterministic reports.
- **Boundary.** Imports `ml` + sibling `backend`; never imports `frontend`.
- **Run:** `python -m scripts.verify_track2_real_models` (the 15 criteria).

See [`real_model_training/README.md`](./real_model_training/README.md). Verified: all 15 Track 2
criteria pass against the **real, locally-acquired CHB-MIT corpus** (50 real windows from two
genuine 1-hour 256 Hz / 23-channel recordings; real seizure labels) — all five architectures
trained → evaluated → benchmarked → compared → **READY_FOR_SERVING** (recommended: `hybrid_eeg`);
full suite **989 passed**. Real EEG recordings — not synthetic fixtures.


## Track 3 — Real Product Application (`application_platform/`)

> Product Completion Program: closes the audit blocker *NO REAL PRODUCT APPLICATION* —
> turns the model platform into a **usable product** with a real HTTP API. Decision:
> [`../.gcc/decisions/ADR-0032`](../.gcc/decisions/ADR-0032-track3-real-product-application.md).

- **`application_platform/`** (Track 3) — a real **FastAPI** HTTP API + governed user
  workflows: upload a real EEG file → validate → metadata → features → select model →
  inference → **prediction + confidence + calibration + model + evidence** → **report
  (JSON/HTML/PDF)** → application readiness (NOT_READY / PARTIALLY_READY / **READY_FOR_USERS**).
  It serves users; it retrains no models and modifies no datasets, Track 1, Track 2,
  persistence, security, or deployment.
- **Reuse, no duplicate logic.** Wraps `application_backend` (which already orchestrates the
  reused P1-P5 upload → prediction workflow over the shared `ml.lineage` tracker + shared
  `ImmutableAuditLog`); reuses the Track-1 recordings + Track-2 architectures. The HTTP API
  is a thin typed/versioned (`/v1`) dispatcher with no business logic.
- **Endpoints:** `GET /health`, `GET /v1/dataset/status`, `GET /v1/model/status`,
  `POST /v1/auth/register`, `POST /v1/auth/login`, `POST /v1/uploads`,
  `GET /v1/analyses/{id}/prediction`, `GET /v1/analyses/{id}/reports?type=&format=json|html|pdf`,
  `GET /v1/readiness`. The OpenAPI schema documents the surface.
- **Bounded analysis.** Real recordings are hours long; the product analyses a deterministic
  leading segment (default 20 s) for interactivity — the full upload is preserved (ADR-0032).
- **Traceability.** `verify_chain` proves **Dataset → Recording → Model → Prediction Request →
  Prediction Result → Report**, reaching the recording + the model.
- **Boundary.** Imports `ml` + sibling `backend` + the external FastAPI stack; never `frontend`.
- **Run:** `python -m scripts.verify_track3_application` (the 15 criteria).

See [`application_platform/README.md`](./application_platform/README.md). Verified: all 15
Track 3 criteria pass against the **real, locally-acquired CHB-MIT corpus** through the real
FastAPI API (register → login → upload a genuine 23-channel/256 Hz EDF → prediction → JSON/
HTML/PDF report → **READY_FOR_USERS**, traceable + audited); full suite **1009 passed**. New
deps: `fastapi`, `uvicorn`, `httpx` (used only by the Track-3 API + tests).


## Track 4 — Operational Readiness & Deployment Qualification (`operations_platform/`)

> Product Completion Program: closes the audit blocker *NO DEPLOYMENT QUALIFICATION* —
> turns the usable product into a **deployable product**. Decision:
> [`../.gcc/decisions/ADR-0033`](../.gcc/decisions/ADR-0033-track4-operational-qualification.md).

- **`operations_platform/`** (Track 4) — **qualifies operations** over the **real** Track-3
  product (read-only): **health monitoring** (service/dataset/model/storage/API/workflow/
  prediction → HEALTHY/DEGRADED/UNHEALTHY), **operational monitoring** (request/prediction/
  upload volume + failures + validation errors; latency/resource informational),
  **diagnostics** (workflow/prediction/upload/API/failure + closed root-cause vocabulary),
  **deployment qualification** (dataset/model/API/workflow/report/persistence/security →
  QUALIFIED/CONDITIONALLY_QUALIFIED/NOT_QUALIFIED), and **deployment readiness** (NOT_READY /
  PARTIALLY_READY / **READY_FOR_DEPLOYMENT**). It qualifies operations; it alters no business
  logic — no retraining, no dataset/Track-1/2/3/prediction/security changes.
- **Reuse, observe-only.** Observes the Track-3 `ApplicationPlatformService` read-only; shares
  its `ml.lineage` tracker + the shared `ImmutableAuditLog`. No parallel systems, no new AI.
- **Traceability.** `verify_chain` proves **Dataset → Model → Prediction → Workflow → Health
  Event → Qualification Event** (the operational chain attaches to the product's workflow
  lineage and reaches the dataset + model).
- **Determinism.** Content-addressed ids over observed deterministic state; wall-clock measures
  informational + excluded from signatures and from the deterministic reports.
- **Boundary.** Imports `ml` + sibling `backend`; never `frontend`.
- **Run:** `python -m scripts.verify_track4_operations` (the 15 criteria).

See [`operations_platform/README.md`](./operations_platform/README.md). Verified: all 15 Track 4
criteria pass against the **real** Track-3 product over the real CHB-MIT corpus — health
HEALTHY (7/7), QUALIFIED (7/7), **READY_FOR_DEPLOYMENT** (score 1.0), traceable + audited;
full suite **1027 passed**. No new dependencies.


## DBE-1 — ASGI Entrypoint & Server Startup (`application_platform/server/`)

> Deployment Blocker Elimination: closes the Final Hostile QA Audit's CRITICAL blocker
> *NO RUNNABLE HTTP SERVER ENTRYPOINT*. Decision:
> [`../.gcc/decisions/ADR-0034`](../.gcc/decisions/ADR-0034-dbe1-asgi-entrypoint.md).

- **`application_platform/server/`** (DBE-1) — turns the Track-3 FastAPI *application* into a
  runnable HTTP *service*: a single authoritative ASGI entrypoint
  **`backend.application_platform.server.app:app`**, a typed/validated `NV_*` startup config,
  an application factory using the **real** production `ApplicationPlatformService`, and an
  application lifespan (startup validation + graceful shutdown) with `/livez` + `/readyz`
  probes alongside the existing `/health`.
- **Start it (exact commands):**
  - `uvicorn backend.application_platform.server.app:app --host 0.0.0.0 --port 8000`
  - `python -m backend.application_platform.server.app`
- **Reuse, no new logic.** Builds the real service + the real Track-3 app via `create_app`;
  changes no datasets/models/inference/persistence/security/operations/Track-1-4/Docker.
- **Run:** `python -m scripts.verify_dbe1_asgi_entrypoint` (the 15 criteria).

See [`application_platform/server/README.md`](./application_platform/server/README.md).
Verified: all 15 DBE-1 criteria pass — a **real uvicorn process** served the live API and
shut down gracefully on SIGTERM, the `python -m` path served live HTTP, health/readiness
respond, security + operations initialize at startup; full suite **1042 passed**. No new deps.
