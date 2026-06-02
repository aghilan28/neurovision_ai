# QUALITY PHILOSOPHY

> **Document type:** Quality Assurance Foundation (V0-P5) · **Tier 2 (process authority)**
> **Status:** Authoritative
> **Owner:** Founder (Quality Owner role)
> **Update procedure:** Governance-class change (ADR — [`../governance/Decision_Governance.md`](../governance/Decision_Governance.md)); follows [`../governance/Change_Management.md`](../governance/Change_Management.md) → *Governance change*.
> **Enforces / inherits:** Principles **AP-1…AP-12**; Rules **NR-1…NR-15**; priority order in [`../PROJECT_OBJECTIVES.md`](../PROJECT_OBJECTIVES.md) §9
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This is the root of the **Quality Assurance Foundation** (`docs/quality/`). It
defines what *quality* means for NeuroVision AI, why it exists, and how it relates
to the platform's other commitments. Every other quality document — gates,
validation, testing, metrics, failure handling — derives from the philosophy here.

> **Premise:** in a clinical platform, **quality is a safety property, not a
> polish step.** Good architecture without validation fails; good architecture
> without memory fails. Quality is the system that makes correctness *survive*
> across V1 → V4.

---

## 1. What Quality Means

In NeuroVision AI, **quality is the degree to which the platform reliably keeps
its promises** — the constitution's principles (AP-1…AP-12) and laws (NR-1…NR-15)
— *and can prove it.* Concretely, a quality artifact is one that is:

1. **Correct** — does what it claims, verified by evidence, not assertion.
2. **Invariant-preserving** — never weakens a cross-version invariant
   ([`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md) §6).
3. **Reproducible** — its results can be regenerated (AP-6, NR-10).
4. **Traceable** — its lineage and rationale are recorded (AP-5/AP-9, NR-5/NR-11).
5. **Bounded** — it respects module boundaries and scope (AP-7, NR-8/NR-13).
6. **Honest** — it carries calibrated uncertainty where clinical (AP-4, NR-4) and
   never overclaims.
7. **Maintainable** — a future contributor (human or AI) can understand and change
   it safely.

Quality is **measured** ([`QUALITY_METRICS.md`](./QUALITY_METRICS.md)) and
**gated** ([`QUALITY_GATES.md`](./QUALITY_GATES.md)); it is never merely asserted.

## 2. What Quality Does NOT Mean

To prevent misapplied effort, quality here is explicitly **not**:

- **Not** maximizing a headline metric (e.g. accuracy) — especially not on a
  leaked split (that is an *anti*-quality outcome; NR-3).
- **Not** gold-plating or speculative generality beyond the current version's scope
  (NR-13) — over-engineering is a quality defect, not a virtue.
- **Not** speed or output volume — fast, voluminous, ungoverned output is a
  liability (AP-12, "survivability over speed").
- **Not** subjective taste — quality is defined by **measurable, enforceable**
  criteria, not opinion.
- **Not** a final-stage QA gate bolted on at the end — quality is built in
  continuously (§5).
- **Not** "looks done" — looking done without evidence is exactly the failure
  mode this foundation exists to stop.

## 3. Why Quality Exists

Quality exists because the platform must **survive multiple years, multiple AI
systems, multiple implementation cycles, context-window limits, and architecture
growth without losing correctness.** Specifically:

- **Clinical stakes are asymmetric.** A confident wrong output can mislead a
  clinician; the cost of an undetected defect is paid by patients, not just
  engineers.
- **AI is high-leverage and high-risk.** AI agents can produce large volumes of
  plausible-but-wrong work; quality is the system that catches it
  ([`AI_OUTPUT_VALIDATION.md`](./AI_OUTPUT_VALIDATION.md)).
- **Foundations compound.** A V0/V1 defect multiplies through V2–V4. Quality is
  cheapest at the foundation.
- **Trust must be provable.** A hospital-ready platform (V4) must *demonstrate*
  correctness, not claim it (AP-8 auditability).

## 4. Relationships: Quality and the Platform's Other Commitments

Quality is the connective tissue that keeps the other commitments true. None can
be sacrificed for another; quality enforces all of them together.

| Commitment | How quality serves it | Owning docs |
|------------|-----------------------|-------------|
| **Safety (clinical)** | Quality gates ensure uncertainty/abstention and traceability before any clinical output ships. | [`QUALITY_GATES.md`](./QUALITY_GATES.md), [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md) |
| **Maintainability** | Quality enforces boundaries, documentation freshness, and review depth. | [`ARCHITECTURE_VALIDATION.md`](./ARCHITECTURE_VALIDATION.md), [`DOCUMENTATION_VALIDATION.md`](./DOCUMENTATION_VALIDATION.md) |
| **Scalability** | Quality validates that streaming/load changes preserve invariants (V3+). | [`TEST_STRATEGY.md`](./TEST_STRATEGY.md), [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md) |
| **Clinical reliability** | Quality requires calibration/coverage + domain-shift evidence before claims. | [`TEST_STRATEGY.md`](./TEST_STRATEGY.md), [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md) |
| **Reproducibility** | Quality blocks any result that cannot be regenerated (NR-10). | [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md), [`RELEASE_CERTIFICATION.md`](./RELEASE_CERTIFICATION.md) |
| **Traceability** | Quality requires decisions/provenance to exist before merge/release. | [`QUALITY_GATES.md`](./QUALITY_GATES.md), [`../context/`](../context/) |

> **Tie-breaker (inherited):** when commitments conflict, the priority order is
> **Governance integrity → Clinical safety → Reproducibility → Clinical utility →
> Research novelty → Speed** ([`../PROJECT_OBJECTIVES.md`](../PROJECT_OBJECTIVES.md) §9).
> Quality never resolves a tie in favor of speed.

## 5. The Four Modes of Quality

Quality operates in four complementary modes. A healthy system uses all four; a
system that relies on only one (usually *detective*, after the fact) fails.

### 5.1 Preventive Quality (stop defects from being created)
Built **before** work: clear boundaries, deterministic preprocessing, prompt
standards, scope/version checks, design via RFC/ADR. *Cheapest and most valuable.*
Owners: [`../governance/AI_Governance.md`](../governance/AI_Governance.md),
[`ARCHITECTURE_VALIDATION.md`](./ARCHITECTURE_VALIDATION.md).

### 5.2 Detective Quality (catch defects that were created)
Mechanical and human checks: GCC import/boundary/acyclicity checks, tests,
documentation/architecture/context audits, review. Owners:
[`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md),
[`TEST_STRATEGY.md`](./TEST_STRATEGY.md), [`QUALITY_GATES.md`](./QUALITY_GATES.md).

### 5.3 Corrective Quality (fix defects correctly and durably)
Defined responses: stop-and-remediate, rollback, fix-forward, and **prevention**
(a new check so it cannot recur). Owner: [`FAILURE_HANDLING.md`](./FAILURE_HANDLING.md).

### 5.4 Continuous Quality (keep quality from decaying over time)
Recurring audits and metrics at every gate, each active quarter, and after
dormancy — so entropy and drift are caught early. Owners:
[`QUALITY_METRICS.md`](./QUALITY_METRICS.md), [`DOCUMENTATION_VALIDATION.md`](./DOCUMENTATION_VALIDATION.md),
[`ARCHITECTURE_VALIDATION.md`](./ARCHITECTURE_VALIDATION.md).

## 6. Quality Hierarchy (precedence when quality concerns compete)

When two quality concerns compete for attention, resolve in this order
(highest first). This mirrors the failure scenarios the project is engineered
against ([`../PROJECT_VISION.md`](../PROJECT_VISION.md) §10).

1. **Governance & traceability integrity** — a change with no recorded decision/
   trace is rejected regardless of how good it looks (NR-5/NR-7).
2. **Clinical safety** — calibrated uncertainty, abstention, no overconfident
   output (AP-4/NR-4).
3. **Validation integrity** — patient-disjoint, no leakage (AP-2/NR-3).
4. **Reproducibility & determinism** (AP-3/AP-6, NR-9/NR-10).
5. **Architectural integrity** — boundaries, acyclicity, no rewrite (AP-1/AP-7,
   NR-6/NR-8).
6. **Documentation/context integrity** — no entropy, no orphan/conflict, fresh
   (NR-14).
7. **Performance / convenience** — last; never bought at the cost of the above.

## 7. Roles (inherited)
Quality uses the same roles as governance ([`../governance/Architecture_Governance.md`](../governance/Architecture_Governance.md) §4):
**Founder** (Quality Owner; sole approver of gate exceptions), **Acting
Architect**, **Implementing Agent** (AI), **Reviewer**, and **GCC (automated)**.
An AI agent may *run* quality checks and *draft* evidence but **never approves its
own quality gate** (NR-7).

## 8. How This Foundation Is Organized
| Document | Role |
|----------|------|
| [`QUALITY_GATES.md`](./QUALITY_GATES.md) | The mandatory checkpoints every change/release passes. |
| [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md) | The taxonomy of validation + evidence required. |
| [`TEST_STRATEGY.md`](./TEST_STRATEGY.md) | The testing philosophy/strategy (elaborates Testing Governance). |
| [`ARCHITECTURE_VALIDATION.md`](./ARCHITECTURE_VALIDATION.md) | Architecture compliance + drift detection. |
| [`AI_OUTPUT_VALIDATION.md`](./AI_OUTPUT_VALIDATION.md) | Validating AI-generated artifacts; AI trust/confidence/risk models. |
| [`DOCUMENTATION_VALIDATION.md`](./DOCUMENTATION_VALIDATION.md) | Documentation correctness/freshness/score/retirement. |
| [`CODE_REVIEW_CHECKLISTS.md`](./CODE_REVIEW_CHECKLISTS.md) | Actionable per-domain review checklists. |
| [`RELEASE_CERTIFICATION.md`](./RELEASE_CERTIFICATION.md) | Release certification outcomes + evidence. |
| [`QUALITY_METRICS.md`](./QUALITY_METRICS.md) | Measurable indicators + scoring model. |
| [`FAILURE_HANDLING.md`](./FAILURE_HANDLING.md) | Repository-level failure framework. |

## 9. Relationship To Governance & Context
- **Quality vs. Governance:** governance defines *how we change things*; quality
  defines *what "good" is and gates it.* They are complementary: quality gates
  **wrap** governance checkpoints (review, release, architecture). Quality never
  contradicts a governance policy; on conflict, governance policy governs and the
  conflict is a consistency defect to fix.
- **Quality vs. Context (V0-P6):** context preservation
  ([`../context/`](../context/)) is what makes quality **survive over time** —
  decisions, risks, assumptions, learnings, and postmortems are the memory that
  quality audits depend on.

Changes to this document are governance-class and require an ADR.
