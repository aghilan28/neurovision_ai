# VERSION EVOLUTION MODEL

> **Document type:** Project Constitution Layer (V0-P1)
> **Status:** Authoritative
> **Owner:** Founder
> **Update procedure:** Governance-class change (ADR); version-model changes require a recorded, reviewed decision (NR-5/NR-12).
> **Derived from:** [`PROJECT_VISION.md`](./PROJECT_VISION.md), [`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md), [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md)
> **Canonical terminology:** [`GLOSSARY.md`](./GLOSSARY.md)

NeuroVision AI evolves through **five deliberate versions**. Each version is a
**maturity state**, not a feature dump. A version exists to make the next version
achievable **without a rewrite**. This document defines, for each version: its
mission, purpose, capabilities, architecture state, validation goals, success
criteria, exit criteria, technical-debt budget, forbidden shortcuts,
dependencies, and required maturity, documentation, testing, and governance.

The model is sequential and **non-skippable**. Section 8 explains why skipping a
version is forbidden.

---

## 0. The Road At A Glance

| Version | Name | Mission (one line) | Core new capability |
|---------|------|--------------------|---------------------|
| **V0** | Repository Foundation | Build the permanent foundation. | Constitution, architecture, governance. |
| **V1** | Offline EEG Platform | Prove rigorous offline interpretation. | Deterministic preprocessing + patient-disjoint, uncertainty-aware detection. |
| **V2** | Clinical Workflow Platform | Make outputs clinically usable. | Reviewable, prioritized, traceable workflow. |
| **V3** | Near Real-Time Platform | Detect in time to matter. | Near-live ingestion + incremental inference. |
| **V4** | Hospital-Ready Foundation | Be deployable and trustworthy in a hospital. | Deployable, governable, auditable operation. |

**Dependency direction:** V0 → V1 → V2 → V3 → V4. Each arrow means *"the later
version is built on, and may not exist without, the earlier version's satisfied
exit criteria."*

```
 V0  ──►  V1  ──►  V2  ──►  V3  ──►  V4
 found.   offline  clinical near-RT  hospital
          rigor    workflow monitor  ready
   │        │         │        │        │
   └─ architecture is EXTENDED across all versions, never rewritten ─┘
```

---

## 1. Version 0 — Repository Foundation

**Mission.** Create the permanent foundation upon which every future version
depends.

**Purpose.** Eliminate the most expensive class of errors — the ones that
multiply through V1–V4 — by fixing intent, structure, and governance *before any
EEG code is written.* A mistake in V0 becomes technical debt in V1–V4; therefore
V0 optimizes purely for survivability and integrity.

**Capabilities (this version is documentation + structure, not code).**
- **V0-P1 — Project Constitution Layer:** vision, objectives, scope, version
  model, architectural principles, non-negotiable rules, glossary.
- **V0-P2 — Repository Architecture Foundation:** the permanent directory tree,
  per-directory governance READMEs, and the dependency/boundary/import/layer/
  system-context architecture documents.
- **V0-P3 — Governance Layer:** the Governance & Context Control (`.gcc/`)
  mechanisms that make boundaries and decisions machine-checkable, and the Lore
  Protocol that preserves context.

**Architecture state.** The full layered architecture (Presentation,
Application, ML, DSP, Infrastructure, Governance, Context — see
[`architecture/LAYERED_ARCHITECTURE.md`](./architecture/LAYERED_ARCHITECTURE.md))
is **defined and documented**, with empty module directories whose boundaries are
already specified. No runtime code exists yet — and that is correct.

**Validation goals.** Internal consistency of all documents; an acyclic,
fully-specified dependency graph; zero undefined terminology; complete directory
ownership and boundary documentation; demonstrable that a future AI agent can
understand project direction from the repository alone.

**Success criteria.** All V0-P1/P2/P3 deliverables exist with complete,
non-placeholder content and pass the validation checklist in
[`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md) §7.

**Exit criteria (must all hold before V1 begins).**
1. Constitution Layer complete and internally consistent (V0-P1).
2. Repository Architecture Foundation complete; dependency graph acyclic and
   matching the import rules (V0-P2).
3. Governance Layer (`.gcc/`) established and able to record decisions and detect
   boundary violations (V0-P3).
4. No undefined terms; no architectural contradictions.

**Technical-debt budget.** **Zero.** V0 is the one version that may carry no
debt, because all later debt compounds from it.

**Forbidden shortcuts.** Writing EEG/model/API code; placeholder/templated docs;
skipping the glossary; leaving any directory without an ownership/boundary
contract; deferring governance to "later."

**Dependencies.** None (this is the root).

**Required maturity.** Architectural and documentary completeness.
**Required documentation.** All Constitution + Architecture documents (this set).
**Required testing.** Documentation/consistency validation (no code tests yet).
**Required governance.** The GCC layer itself is a V0 deliverable (V0-P3).

---

## 2. Version 1 — Offline EEG Platform

**Mission.** Prove that NeuroVision AI can interpret EEG **rigorously and
reproducibly** in the offline (retrospective) setting.

**Purpose.** Establish trustworthy detection of seizures and the IIC under the
hardest validation regime *before* taking on the additional difficulty of
real-time operation. V1 is where the platform earns scientific credibility.

**Capabilities.**
- Deterministic, versioned **preprocessing** pipeline (filtering, montage
  handling, windowing, normalization).
- **Datasets** access/curation for patient-level, leakage-safe data handling.
- Baseline **ML** detection/classification of SZ and IIC patterns (LPD, GPD,
  LRDA, GRDA, Other).
- **Calibrated uncertainty** (e.g. Conformal Prediction) on outputs, with
  abstain/escalate.
- **Evaluation** harness enforcing patient-disjoint (LOSO-style) splits.

**Architecture state.** Presentation layer remains minimal/absent; the DSP, ML,
Datasets, and Evaluation modules become real, populating the lower layers of the
V0 architecture **within their already-defined boundaries.**

**Validation goals.** Patient-disjoint detection metrics; measured calibration
and (for conformal methods) empirical coverage; initial domain-shift
characterization on held-out sites/montages; full reproducibility of every
reported result.

**Success criteria.** Defensible patient-disjoint metrics for SZ and IIC with
honest, calibrated uncertainty, every one regenerable from pinned inputs/code.

**Exit criteria (must hold before V2).**
1. Preprocessing is deterministic and versioned.
2. All reported metrics are patient-disjoint; zero leakage.
3. Uncertainty is calibrated and coverage is measured.
4. Every result is reproducible.
5. No architectural principle violated; no module boundary crossed.

**Technical-debt budget.** Very low. Any unavoidable debt must be **recorded in
the governance layer with a repayment plan** before V2 begins; undocumented debt
is forbidden.

**Forbidden shortcuts.** Non-patient-disjoint evaluation; nondeterministic
preprocessing; uncalibrated/absent uncertainty; importing across forbidden
boundaries to "save time"; reporting in-distribution-only metrics as if general.

**Dependencies.** V0 exit criteria satisfied.

**Required maturity.** Reproducible, validated offline pipeline.
**Required documentation.** Preprocessing spec, model cards, evaluation protocol,
reproducibility instructions — all referencing the constitution.
**Required testing.** Unit tests for preprocessing determinism; evaluation tests
asserting patient-disjoint splits; reproducibility checks.
**Required governance.** Decision records for model/method choices; boundary
checks enforced by GCC; any debt logged with a repayment plan.

---

## 3. Version 2 — Clinical Workflow Platform

**Mission.** Make V1's rigorous outputs **usable inside a real clinical review
workflow.**

**Purpose.** A correct model that a clinician cannot use is clinically worthless.
V2 turns detections into a reviewable, prioritized, traceable experience for
neurophysiologists — without weakening any V1 guarantee.

**Capabilities.**
- **Backend (application layer):** services that expose detections + uncertainty
  with full traceability.
- **Frontend (presentation layer):** review-oriented interface that communicates
  uncertainty faithfully and supports triage/prioritization.
- **Auditability:** every displayed result traceable to inputs, preprocessing
  version, model version, and uncertainty.

**Architecture state.** Application and Presentation layers become real. The
strict import rules are now actively exercised: the frontend communicates with
the backend **via API only**, never importing ML/DSP/datasets
(see [`architecture/IMPORT_RULES.md`](./architecture/IMPORT_RULES.md)).

**Validation goals.** End-to-end traceability verified; uncertainty rendered
without distortion; workflow validated against clinician review needs; all V1
metrics preserved.

**Success criteria.** A clinician can review prioritized detections with honest
uncertainty, and every shown result is fully auditable.

**Exit criteria (must hold before V3).**
1. End-to-end audit trail for every clinical output.
2. Uncertainty preserved and faithfully presented through all layers.
3. Frontend↔backend boundary respected (API-only).
4. No V1 guarantee (patient-disjoint, determinism, calibration) regressed.

**Technical-debt budget.** Low. UI/UX iteration debt is tolerable **only** if it
never compromises traceability, boundaries, or V1 guarantees; all such debt is
recorded.

**Forbidden shortcuts.** Frontend importing domain modules directly; dropping or
distorting uncertainty to simplify the UI; displaying results that cannot be
traced; bypassing the backend.

**Dependencies.** V1 exit criteria satisfied.

**Required maturity.** Usable, auditable clinical review workflow.
**Required documentation.** API contracts, workflow/UX rationale, audit-trail
specification.
**Required testing.** API contract tests; end-to-end traceability tests;
boundary tests proving the frontend imports no domain code.
**Required governance.** Decision records for workflow/API design; audit-trail
verification; boundary enforcement via GCC.

---

## 4. Version 3 — Near Real-Time Platform

**Mission.** Move from retrospective analysis to **near-live monitoring**, so
detection happens in time to matter clinically.

**Purpose.** The clinical value of seizure detection is time-sensitive. V3 takes
on streaming difficulty **only after** offline rigor (V1) and clinical usability
(V2) are proven, so real-time pressure cannot be used as an excuse to weaken
validation.

**Capabilities.**
- Near-live ingestion of ongoing recordings and incremental/streaming inference.
- Latency and reliability targets under streaming load.
- Operational **monitoring** of model and system behavior, including drift
  signals.

**Architecture state.** The Infrastructure layer (deployment, monitoring) matures
substantially. Streaming is added as an **extension** of the existing pipeline,
reusing the deterministic preprocessing and uncertainty machinery — not a parallel
re-implementation.

**Validation goals.** Validation integrity preserved in the streaming setting
(no leakage introduced by windowing/buffering); latency/reliability targets met;
domain-shift and degradation observable via monitoring.

**Success criteria.** Near-real-time detection with uncertainty, meeting latency/
reliability targets, with no loss of validation integrity versus V1/V2.

**Exit criteria (must hold before V4).**
1. Streaming preserves patient-disjoint validity and determinism guarantees.
2. Latency/reliability targets met and measured.
3. Monitoring detects performance degradation and drift.
4. No regression of V1/V2 guarantees.

**Technical-debt budget.** Low. Performance optimizations must not introduce
hidden nondeterminism or untraceable behavior; any optimization debt is recorded.

**Forbidden shortcuts.** Trading away determinism for latency without record;
streaming designs that leak across patients; "we'll add monitoring later";
duplicating preprocessing logic instead of reusing it.

**Dependencies.** V2 exit criteria satisfied.

**Required maturity.** Reliable near-real-time monitoring.
**Required documentation.** Streaming architecture, latency/reliability targets,
monitoring/alerting specification.
**Required testing.** Streaming-correctness tests; latency/load tests;
drift-detection tests; regression tests against V1/V2 guarantees.
**Required governance.** Decision records for streaming/latency trade-offs;
monitoring thresholds recorded; GCC boundary and drift checks active.

---

## 5. Version 4 — Hospital-Ready Foundation

**Mission.** Become a platform that is **deployable, governable, auditable, and
reliable** inside a hospital — the strategic destination of the project.

**Purpose.** Everything before V4 exists to make V4 reachable without a rewrite.
V4 is an **engineering and governance maturity state**, not a marketing milestone
and **not** a regulatory-clearance claim (see [`PROJECT_VISION.md`](./PROJECT_VISION.md) §7).

**Capabilities.**
- Deployment within hospital IT/security constraints.
- Complete governance: enforced boundaries, decision records, full audit trails.
- Demonstrated reliability under real-world domain shift and operational load.

**Architecture state.** All seven layers are mature and operating under enforced
governance. The architecture is the **same one defined in V0**, now fully
populated — extended over four versions, never rewritten.

**Validation goals.** End-to-end auditability; reliability under real-world shift
and load; governance completeness; security/operational readiness for hospital
deployment.

**Success criteria.** The platform is structurally ready to be entrusted with
continuous clinical use: deployable, governable, auditable, reliable, maintainable.

**Exit criteria (continuous maturity, not a one-time gate).**
1. Deployable within hospital technical/security constraints.
2. Every output auditable end-to-end.
3. Reliability demonstrated under real-world domain shift and load.
4. Governance complete: every consequential decision recorded; boundaries
   enforced; drift detectable.

**Technical-debt budget.** Near-zero and fully visible. At hospital-readiness,
hidden debt is a safety risk; all debt must be recorded, prioritized, and
actively managed.

**Forbidden shortcuts.** Shipping un-auditable outputs; bypassing governance
under deployment pressure; vendor lock-in baked into the architecture; declaring
"hospital-ready" without demonstrated reliability under shift/load.

**Dependencies.** V3 exit criteria satisfied.

**Required maturity.** Full operational, governance, and reliability maturity.
**Required documentation.** Deployment/operations runbooks, security model,
complete governance and audit documentation.
**Required testing.** Full regression suite across V1–V3 guarantees;
reliability/load testing; security/operational validation; audit-trail
completeness tests.
**Required governance.** Comprehensive: decision records, enforced boundaries,
audit trails, drift detection — all operating continuously.

---

## 6. Cross-Version Invariants

These hold in **every** version from the moment the relevant capability exists.
They never weaken as the platform matures.

| Invariant | Introduced | Never violated after |
|-----------|-----------|----------------------|
| Patient-disjoint validation | V1 | ever |
| Deterministic, versioned preprocessing | V1 | ever |
| Calibrated uncertainty on clinical outputs | V1 | ever |
| Reproducibility of reported results | V1 | ever |
| Enforced module boundaries / import rules | V0 (defined), V1+ (exercised) | ever |
| Recorded decisions / governance | V0-P3 | ever |
| No architecture rewrite | V0 | ever |
| Stay within [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) | V0 | ever |

A later version that breaks an earlier version's invariant has **regressed**, and
is a failure regardless of new capability (see
[`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md) §6).

---

## 7. Technical-Debt Budget Philosophy

- **V0:** zero debt (the foundation must be clean).
- **V1–V3:** low debt, and **only recorded debt with a repayment plan.**
- **V4:** near-zero, fully visible, actively managed debt.

**Hidden/undocumented debt is forbidden in every version.** The cost of debt in a
clinical platform is paid by patients and clinicians, not just engineers. Debt
that is recorded is a manageable liability; debt that is hidden is a latent
failure (see [`NON_NEGOTIABLE_RULES.md`](./NON_NEGOTIABLE_RULES.md)).

---

## 8. Why Skipping Versions Is Forbidden

Each version exists to **de-risk the next**. Skipping a version does not save
time; it relocates risk to where it is most expensive to fix.

- **Skipping V0** → no shared intent, no boundaries, no governance. Every later
  decision is unanchored; architecture and context drift are guaranteed.
- **Skipping V1** → building a clinical workflow (V2) or real-time system (V3) on
  top of **unvalidated, possibly leaked, non-reproducible** detection. The whole
  edifice rests on sand; impressive demos collapse on unseen patients.
- **Skipping V2** → a real-time engine (V3) producing outputs that no clinician
  can review, trust, or audit. Technically live, clinically useless.
- **Skipping V3** → declaring "hospital-ready" (V4) without ever proving
  reliability under streaming load and real-world drift.
- **Skipping V4** → "production" with no deployment, governance, or audit
  maturity — exactly the failure mode the entire project is engineered to avoid.

**Rule:** a version may not begin until the **exit criteria of every prior
version are satisfied and recorded.** Parallel *exploration* is permitted; but a
later version's exit criteria cannot be claimed until its prerequisites are met.
This is enforced as a project law in
[`NON_NEGOTIABLE_RULES.md`](./NON_NEGOTIABLE_RULES.md) and checked by the
governance layer.

---

## 9. Relationship To Other Constitution Documents

- Upstream: [`PROJECT_VISION.md`](./PROJECT_VISION.md),
  [`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md),
  [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md).
- Realized structurally by:
  [`ARCHITECTURAL_PRINCIPLES.md`](./ARCHITECTURAL_PRINCIPLES.md),
  [`architecture/LAYERED_ARCHITECTURE.md`](./architecture/LAYERED_ARCHITECTURE.md),
  and the per-directory READMEs (which note **version ownership** of each module).
- Protected by: [`NON_NEGOTIABLE_RULES.md`](./NON_NEGOTIABLE_RULES.md).

Version-model changes are governance events and require a recorded, reviewed
decision.
