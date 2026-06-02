# PROJECT OBJECTIVES

> **Document type:** Project Constitution Layer (V0-P1)
> **Status:** Authoritative
> **Owner:** Founder
> **Update procedure:** Governance-class change (ADR); constitution changes require a recorded, reviewed decision (NR-5).
> **Derived from:** [`PROJECT_VISION.md`](./PROJECT_VISION.md)
> **Constrains:** [`VERSION_EVOLUTION_MODEL.md`](./VERSION_EVOLUTION_MODEL.md), all implementation versions
> **Canonical terminology:** [`GLOSSARY.md`](./GLOSSARY.md)

This document translates the vision into **objectives that can be checked**. The
vision says *why*; this document says *what success and failure look like, and
how we will know.* Every objective is traceable upward to the vision and downward
to a version in the evolution model.

Objectives are organized as: **Primary**, **Secondary**, **Long-Term**, and
**Version-Specific**, followed by **Success Metrics**, **Failure Metrics**,
**Acceptance Criteria**, **Strategic Constraints**, and the **relationships**
between research, engineering, clinical utility, deployment readiness, and
governance.

---

## 1. Primary Objectives

These define the platform. If any one is abandoned, the project has lost its
identity.

| ID | Objective | Why it is primary |
|----|-----------|-------------------|
| **P1** | Detect and characterize ICU seizures and the **Ictal-Interictal Continuum (IIC)** — SZ, LPD, GPD, LRDA, GRDA — from cEEG. | This is the clinical purpose of the platform. |
| **P2** | Attach **calibrated uncertainty** (e.g. Conformal Prediction) to every clinically meaningful output, including the ability to abstain/escalate. | Trust in critical care requires honest confidence, not point predictions. |
| **P3** | Guarantee **patient-disjoint validation** (LOSO-style) for every reported result. | Without it, all metrics are suspect; this is the #1 cause of EEG-AI translation failure. |
| **P4** | Guarantee **deterministic, versioned, reproducible** preprocessing and evaluation. | A result that cannot be regenerated cannot be trusted, audited, or defended. |
| **P5** | Maintain a **stable architecture that evolves V0 → V4 without rewrites**, governed by enforced module boundaries. | Survivability and maintainability are the dominant lifetime costs. |
| **P6** | Build **Governance & Context Control (GCC)** so that boundaries, decisions, and audit trails are mechanized, not aspirational. | A clinical platform must prove *why* it behaves as it does. |

---

## 2. Secondary Objectives

These strengthen the primary objectives. They are important but subordinate; they
are never pursued at the expense of a primary objective.

| ID | Objective |
|----|-----------|
| **S1** | Robustness under **domain shift** (new site, montage, amplifier, population) measured explicitly, not assumed. |
| **S2** | Artifact-awareness — recognize and handle muscle/movement/electrode/electrical artifact rather than mislabel it. |
| **S3** | Faithful **propagation of uncertainty** through every layer: ML produces it, application preserves it, presentation communicates it. |
| **S4** | A repository that is **self-explanatory** to a new human or AI agent without the original research corpus (the Lore Protocol). |
| **S5** | **Auditability**: every output traceable to its inputs, preprocessing version, model version, and uncertainty. |
| **S6** | Clinically meaningful evaluation aligned with **ACNS** terminology and inter-rater realities of the IIC. |
| **S7** | Operational observability (monitoring) sufficient to detect performance degradation in deployment. |

---

## 3. Long-Term Objectives

These mature over multiple versions and culminate in V4.

| ID | Objective | Realized by |
|----|-----------|-------------|
| **L1** | Become a **Hospital-Ready Foundation**: deployable, governable, auditable, reliable under load. | V4 |
| **L2** | Move from retrospective to **near real-time** monitoring without sacrificing validation integrity. | V3 |
| **L3** | Integrate into a **clinical review workflow** that clinicians actually use. | V2 |
| **L4** | Sustain a **decade of maintainability**: new evidence and models absorbed via extension, never rewrite. | V0 → V4 |
| **L5** | Establish a **reusable governance pattern** (GCC + Lore Protocol) that protects intent across team and agent turnover. | V0-P3 → V4 |

---

## 4. Version-Specific Objectives

Each objective below is owned by exactly one version. A version is not "done"
until its objectives are met and its exit criteria
(see [`VERSION_EVOLUTION_MODEL.md`](./VERSION_EVOLUTION_MODEL.md)) are satisfied.

### Version 0 — Repository Foundation
- **V0-O1:** Establish the Project Constitution Layer (vision, objectives, scope,
  version model, principles, rules, glossary). *(V0-P1 — this phase.)*
- **V0-O2:** Establish the permanent repository structure and per-directory
  governance contracts. *(V0-P2 — this phase.)*
- **V0-O3:** Establish the Governance & Context Control layer (`.gcc/`). *(V0-P3.)*
- **V0-O4:** Establish the Lore Protocol so context survives contributor turnover.

### Version 1 — Offline EEG Platform
- **V1-O1:** Deterministic, versioned preprocessing pipeline for cEEG.
- **V1-O2:** Baseline detection/classification of SZ + IIC patterns.
- **V1-O3:** Patient-disjoint (LOSO-style) evaluation harness producing
  defensible metrics.
- **V1-O4:** Calibrated uncertainty on outputs (e.g. Conformal Prediction).
- **V1-O5:** Full reproducibility of every reported result.

### Version 2 — Clinical Workflow Platform
- **V2-O1:** Review-oriented presentation of detections with uncertainty.
- **V2-O2:** Triage/prioritization aligned with clinician workflow.
- **V2-O3:** End-to-end traceability of every displayed result (auditability).

### Version 3 — Near Real-Time Platform
- **V3-O1:** Near-live ingestion and incremental inference.
- **V3-O2:** Latency and reliability targets met under streaming load.
- **V3-O3:** Validation integrity preserved in the streaming setting.

### Version 4 — Hospital-Ready Foundation
- **V4-O1:** Deployable within hospital IT/security constraints.
- **V4-O2:** Complete governance, decision records, and audit trails.
- **V4-O3:** Demonstrated reliability under real-world domain shift and load.

---

## 5. Success Metrics

Metrics are **categories of evidence**, not numeric targets — concrete thresholds
are set per version in [`VERSION_EVOLUTION_MODEL.md`](./VERSION_EVOLUTION_MODEL.md)
when the relevant capability is built. (V0 builds no models, so V0 has no
predictive metrics; its success is structural.)

### 5.1 Clinical / Predictive (V1+)
- **Detection performance** for SZ and IIC patterns, reported **only** under
  patient-disjoint splits, with sensitivity/specificity and per-class breakdown.
- **Calibration quality:** measured calibration error and, for Conformal
  Prediction, **empirical coverage** matching the target error rate.
- **Robustness:** performance retained under held-out sites/montages
  (domain-shift evaluation), reported as a delta versus in-distribution.
- **Abstention behavior:** the system abstains/escalates on genuinely ambiguous
  cases rather than forcing low-confidence decisions.

### 5.2 Engineering / Structural (V0+)
- **Reproducibility:** any reported result regenerates bit-for-bit (or within a
  documented deterministic tolerance) from pinned inputs and code.
- **Boundary integrity:** zero import-rule violations
  (see [`architecture/IMPORT_RULES.md`](./architecture/IMPORT_RULES.md)).
- **Documentation completeness:** every directory has a governance README; every
  term used is defined in the glossary; every consequential decision is recorded.
- **Architecture stability:** number of architecture rewrites across V0→V4 = **0**.

### 5.3 Governance (V0-P3+)
- **Decision coverage:** every consequential change has a recorded rationale.
- **Audit completeness:** every clinical output (V2+) is traceable end-to-end.
- **Drift detection:** architecture/context drift is detectable by the GCC layer,
  not discovered by accident.

---

## 6. Failure Metrics

The project is **failing** — independent of any positive metric — if any of the
following are observed. Each maps to a failure scenario in
[`PROJECT_VISION.md`](./PROJECT_VISION.md) §10.

| Failure metric | Trigger condition |
|----------------|-------------------|
| **Leakage** | Any reported metric depends on a non-patient-disjoint split. |
| **Overconfidence** | A clinical output ships without calibrated uncertainty. |
| **Irreproducibility** | A reported result cannot be regenerated from pinned inputs/code. |
| **Architecture drift** | Implemented dependencies diverge from documented boundaries. |
| **Context drift** | A consequential decision exists with no recorded rationale. |
| **Rewrite** | Progress requires discarding the established architecture. |
| **Scope creep** | Work begins on out-of-scope capability (see [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md)). |
| **Silent debt** | A shortcut is taken without being recorded and scheduled for repayment. |

A single occurrence of any failure metric is a **stop-and-remediate** event, not
a backlog item.

---

## 7. Acceptance Criteria

### 7.1 Acceptance Criteria for V0-P1 (Project Constitution Layer) — this phase
- [ ] All seven constitution documents exist with complete, non-placeholder content.
- [ ] Every document is internally consistent and consistent with every other.
- [ ] No architectural contradictions exist between documents.
- [ ] Every term used is defined in [`GLOSSARY.md`](./GLOSSARY.md).
- [ ] Vision → Objectives → Scope → Versions → Principles → Rules form an
      unbroken, traceable chain.
- [ ] A future AI agent can understand project direction from these documents
      alone.

### 7.2 Acceptance Criteria for V0-P2 (Repository Architecture Foundation) — this phase
- [ ] The full permanent directory tree exists.
- [ ] Every directory has a README defining purpose, responsibilities, allowed
      and forbidden dependencies, future responsibilities, version ownership,
      examples, and boundary rules.
- [ ] The architecture docs (dependency graph, module boundaries, import rules,
      layered architecture, system context) exist and agree with each other and
      with every per-directory README.
- [ ] The dependency graph is **acyclic** and matches the import rules exactly.

### 7.3 General Acceptance Criteria (all versions)
- [ ] No primary objective regressed.
- [ ] No failure metric triggered.
- [ ] The version's own exit criteria (in the evolution model) are satisfied.
- [ ] Every consequential decision is recorded (governance).

---

## 8. Strategic Constraints

These constraints bound *how* objectives may be pursued. They are elaborated as
laws in [`NON_NEGOTIABLE_RULES.md`](./NON_NEGOTIABLE_RULES.md).

1. **Survivability over speed.** No objective justifies a shortcut that creates
   undocumented debt.
2. **No architecture rewrites.** Objectives are met by extending the V0
   architecture.
3. **Patient-disjoint always.** No predictive objective may be reported on a
   leaked split.
4. **Uncertainty always.** No clinical objective is "met" without calibrated
   uncertainty.
5. **Determinism always.** No objective is "met" if its result is not reproducible.
6. **Boundaries always.** No objective justifies violating a module boundary or
   import rule.
7. **No version skipping.** Objectives of a later version may not be pursued
   before the prerequisite version's exit criteria are met.
8. **Stay in scope.** Objectives are pursued only within
   [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md).

---

## 9. Relationships Between Concerns

The platform deliberately couples five concerns. None is allowed to advance by
sacrificing another. This section makes those relationships explicit.

```
            RESEARCH ──────────────► ENGINEERING
               │                          │
               │ supplies methods,        │ supplies reproducible,
               │ hypotheses, evidence     │ governed implementation
               ▼                          ▼
        CLINICAL UTILITY ◄──────── DEPLOYMENT READINESS
               ▲                          ▲
               └────────── GOVERNANCE ────┘
              (binds, records, and audits all four)
```

- **Research → Engineering:** Research proposes methods (models, UQ techniques,
  evaluation designs). Engineering accepts them **only** if they can be made
  deterministic, patient-disjoint-validated, and governed. Research that cannot
  be reproduced does not enter the platform.
- **Engineering → Clinical Utility:** Engineering exists to deliver clinical
  value, not benchmark numbers. A capability that does not help a clinician is
  not an objective.
- **Clinical Utility ↔ Deployment Readiness:** A capability is only clinically
  useful if it can actually run where clinicians work; deployment readiness is
  only meaningful if what is deployed is clinically useful. They advance
  together (with deployment maturing toward V4).
- **Governance over all four:** Governance (GCC + Lore Protocol) records the
  rationale, enforces the boundaries, and provides the audit trail that lets the
  other four concerns advance **without losing trust or intent**. Governance is
  not a separate workstream; it is the connective tissue.

**Conflict-resolution rule:** when two concerns conflict, the order of priority
is **Governance integrity → Clinical safety → Reproducibility → Clinical utility
→ Research novelty → Speed.** Speed is always last.

---

## 10. Relationship To Other Constitution Documents

- Upstream: [`PROJECT_VISION.md`](./PROJECT_VISION.md) (the *why*).
- Sibling: [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) (what is in/out of bounds).
- Downstream: [`VERSION_EVOLUTION_MODEL.md`](./VERSION_EVOLUTION_MODEL.md)
  (per-version objectives, thresholds, exit criteria),
  [`ARCHITECTURAL_PRINCIPLES.md`](./ARCHITECTURAL_PRINCIPLES.md) and
  [`NON_NEGOTIABLE_RULES.md`](./NON_NEGOTIABLE_RULES.md) (how objectives are
  protected structurally and legally).

This document may only change through a recorded, reviewed governance decision.
