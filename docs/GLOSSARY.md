# GLOSSARY

> **Document type:** Project Constitution Layer (V0-P1)
> **Status:** Authoritative / Canonical terminology source
> **Owner:** Founder
> **Update procedure:** Governance-class change (ADR); a new consequential term is added here in the same change (NR-14).
> **Applies to:** Every document and (in later versions) every code artifact
> **Related:** [`PROJECT_VISION.md`](./PROJECT_VISION.md), [`ARCHITECTURAL_PRINCIPLES.md`](./ARCHITECTURAL_PRINCIPLES.md), [`NON_NEGOTIABLE_RULES.md`](./NON_NEGOTIABLE_RULES.md)

This glossary is the **single source of truth for terminology** in NeuroVision
AI. If a term is used anywhere in the repository, its meaning is the one defined
here. Introducing a new consequential term **requires adding it here** (Rule
**NR-14**, the Lore Protocol). Terms are grouped for readability; within each
group they are ordered to aid first-time readers.

> **Note on clinical terms.** Clinical definitions below are provided for
> engineering context and shared vocabulary. They are **not** medical guidance
> and do not override the standardized definitions of the governing clinical
> bodies (e.g. ACNS). NeuroVision AI is decision-support, never a clinician.

---

## 1. Clinical & EEG Domain Terms

### EEG (Electroencephalography / Electroencephalogram)
Recording of the brain's electrical activity via electrodes on the scalp. The
primary input modality of the platform. Characterized by low signal-to-noise
ratio, artifact, and high inter-patient variability.

### cEEG (Continuous EEG)
Prolonged, often multi-day, EEG monitoring — standard of care for detecting
seizures in at-risk ICU patients. Produces very large data volumes that exceed
exhaustive human review, motivating decision support.

### ICU (Intensive Care Unit)
The critical-care setting that is NeuroVision AI's clinical context. Patients may
be comatose or sedated, so seizures are often **non-convulsive** and invisible
without EEG.

### NCS / NCSE (Non-Convulsive Seizure / Non-Convulsive Status Epilepticus)
Seizure activity without overt physical convulsion. Common and dangerous in the
ICU; detectable only via EEG. A core clinical motivation for the platform.

### Montage
The configuration of EEG electrodes and the reference/derivation scheme used to
display channels. Montages differ across sites and machines; **montage
heterogeneity** is a source of domain shift the platform must handle.

### Artifact
Non-cerebral signal contaminating the EEG (muscle, movement, electrode pop, eye,
electrical/line noise). Must be recognized rather than mislabeled as brain
activity (Objective **S2**).

### ACNS (American Clinical Neurophysiology Society)
The body whose **standardized critical-care EEG terminology** the platform
adopts for naming and characterizing rhythmic and periodic patterns. Using ACNS
terminology is in scope (**I12**) and supports clinical interpretability.

### IIC (Ictal-Interictal Continuum)
The clinically ambiguous spectrum of EEG patterns that are **neither clearly
seizure nor clearly normal**. The IIC (which includes LPD, GPD, LRDA, GRDA) is
where expert disagreement and clinical risk concentrate, and therefore where
decision support and **uncertainty quantification** matter most. Monitoring the
IIC is a primary in-scope capability (**I2**).

### SZ (Seizure)
An electrographic seizure pattern. One of the core classes the platform detects.

### LPD (Lateralized Periodic Discharges)
An ACNS-defined periodic pattern over one hemisphere, lying on the IIC. Formerly
referred to by older terminology (e.g. "PLEDs"); the project uses ACNS naming.

### GPD (Generalized Periodic Discharges)
An ACNS-defined periodic pattern occurring bilaterally/generally, on the IIC.

### LRDA (Lateralized Rhythmic Delta Activity)
An ACNS-defined rhythmic delta pattern over one hemisphere, on the IIC.

### GRDA (Generalized Rhythmic Delta Activity)
An ACNS-defined rhythmic delta pattern occurring generally, on the IIC.

### "Other" / Background
Catch-all for patterns outside the targeted SZ/IIC classes (including normal
background). Used to keep classification well-posed.

---

## 2. Validation & Evaluation Terms

### Patient-Disjoint Validation
An evaluation regime in which **no patient's data appears in more than one** of
the train/validation/test partitions. The **only** valid evaluation regime in
this project (Principle **AP-2**, Rule **NR-3**). Prevents the model from
memorizing patient identity and inflating metrics.

### LOSO (Leave-One-Subject-Out)
The canonical patient-disjoint evaluation strategy: each patient (subject) is, in
turn, held out entirely for testing while the rest are used for training. The
default expression of patient-disjoint validation in NeuroVision AI.

### Data Leakage
Any situation where information about the test set influences training —
classically, the same patient appearing in train and test. The leading cause of
EEG-AI translation failure; treated as a failure metric
([`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md) §6).

### Domain Shift
A change in the input data distribution between training and deployment — e.g. a
new **site**, **montage**, **amplifier**, or **patient population**. Treated as an
**expected operating condition**, measured via held-out-site/montage evaluation
(Principle **AP-10**, Rule **NR-15**).

### Calibration
The degree to which a model's stated confidence matches its real accuracy. A
well-calibrated "80% confident" is correct ~80% of the time. Measured in
`evaluation/`; required for clinical outputs (Principle **AP-4**).

### Coverage
For a prediction set (e.g. from Conformal Prediction), the empirical rate at which
the true label falls inside the set. A valid conformal method achieves coverage
matching its target error rate. Used to verify uncertainty guarantees.

### Reproducibility
The property that a reported result can be **regenerated** from pinned inputs,
pinned code, and a versioned environment (Principle **AP-6**, Rule **NR-10**).

### Determinism
The property that identical inputs and a pinned version always produce identical
outputs. Required of preprocessing (Principle **AP-3**, Rule **NR-9**); the basis
of reproducibility.

---

## 3. Machine Learning & Method Terms

### Uncertainty Quantification (UQ)
The discipline of attaching a principled, **calibrated** measure of confidence to
predictions, including the option to **abstain/escalate**. A primary objective
(**P2**) and core differentiator of the platform (Principle **AP-4**).

### Conformal Prediction
A distribution-free UQ framework that produces **prediction sets** with a
**statistical coverage guarantee** (a chosen error rate) under mild assumptions.
The platform's reference technique for calibrated uncertainty with guarantees.

### Mamba
A **state-space sequence model** architecture (a class of selective structured
state-space models) suited to long sequences with near-linear scaling. Cited as a
candidate model family for long EEG sequences; any model choice must still satisfy
patient-disjoint validation, uncertainty, determinism, and governance before it
enters the platform.

### Abstain / Escalate
The platform's permitted behavior of **declining to commit** to a low-confidence
prediction and routing the case to a human reviewer, instead of forcing an
answer. Enabled by UQ; consistent with decision-support (not autonomy).

### Inference
The act of running a trained model on new data to produce outputs. In NeuroVision
AI, inference outputs always carry uncertainty (Rule **NR-4**) and provenance
(Rule **NR-11**).

### Epoch / Window / Segment
A fixed-length slice of EEG used as a unit of analysis. (Note: "epoch" here means
a signal window, distinct from a training epoch in ML; disambiguate in context.)

---

## 4. Architecture & Engineering Terms

### Layer
A horizontal tier of the architecture with a defined responsibility and a fixed
position in the dependency order. NeuroVision AI defines seven layers —
Presentation, Application, ML, DSP, Infrastructure, Governance, Context — detailed
in [`architecture/LAYERED_ARCHITECTURE.md`](./architecture/LAYERED_ARCHITECTURE.md).

### Module
A directory-level unit with a single responsibility and explicit boundaries
(e.g. `preprocessing/`, `ml/`). Governed by a per-directory README contract and
the import rules (Principle **AP-7**).

### Module Boundary
The explicit contract defining a module's ownership, responsibilities, inputs,
outputs, dependencies, and forbidden actions. Documented in
[`architecture/MODULE_BOUNDARIES.md`](./architecture/MODULE_BOUNDARIES.md).

### Dependency Graph
The directed graph of allowed imports between modules. It is **acyclic** and
flows top→down (higher layers depend on lower; never the reverse). Defined in
[`architecture/DEPENDENCY_GRAPH.md`](./architecture/DEPENDENCY_GRAPH.md).

### Import Rule
A specific allowed/forbidden import relationship between modules (e.g. *frontend
may not import ml*). Enumerated in
[`architecture/IMPORT_RULES.md`](./architecture/IMPORT_RULES.md); enforced by GCC.

### Provenance
The recorded lineage of an output: which input, preprocessing version, model
version, and uncertainty produced it. The basis of clinical traceability
(Principle **AP-5**, Rule **NR-11**).

### Technical Debt
The implied future cost of a present shortcut. In this project, debt is permitted
only if **recorded** with a repayment plan; **hidden debt is forbidden** (Rule
**NR-2**).

---

## 5. Governance & Context Terms

### GCC (Governance & Context Control)
The platform's **machine-enforced governance layer**, housed in the `.gcc/`
directory and formally implemented in **Phase V0-P3**. GCC encodes architectural
rules, import/boundary constraints, decision records, and context controls in a
**machine-checkable** form so that governance is *by construction* rather than
aspirational (Principle **AP-11**). It is the mechanism that detects architecture
drift and context drift and that enforces the non-negotiable rules in CI.

### Governance Layer
The architectural layer (realized by `.gcc/`) responsible for enforcing
boundaries, recording decisions, and maintaining audit trails. One of the seven
layers; cross-cutting over the others.

### Context Layer
The architectural layer (realized by `docs/`, operating under the Lore Protocol)
responsible for preserving durable project intent, rationale, and terminology so
the repository remains self-explanatory.

### Lore Protocol
The **context-engineering discipline** by which durable project knowledge — the
"lore": decisions, constraints, rationale, terminology — is captured in versioned
documentation so that future humans and AI agents can reconstruct full intent
**without the original research corpus**. The Lore Protocol is the primary defense
against Context Drift (Rule **NR-14**) and is governed/maintained via the GCC
layer.

### Architecture Drift
The gradual divergence of the **implemented** system from the **documented/
intended** architecture (e.g. forbidden imports creeping in). Detected and
prevented by GCC and the import rules (Principle **AP-7**, Rule **NR-8**); a
named failure scenario ([`PROJECT_VISION.md`](./PROJECT_VISION.md) §10).

### Context Drift
The gradual **loss or distortion of project intent and rationale** over time as
people and AI agents change — settled questions get re-litigated, invariants get
broken unknowingly. Prevented by versioned decisions and the Lore Protocol
(Principle **AP-9**, Rule **NR-14**).

### Decision Record
A recorded, versioned, dated statement of a consequential decision, its
rationale, and the alternatives considered. Required for architectural/method
changes (Rule **NR-5**); stored under the governance layer.

### Audit Trail
The end-to-end record that makes outputs and decisions reconstructable after the
fact. Required for clinical outputs (Rule **NR-11**); a V2/V4 exit criterion.

### ADR (Architecture / Any Decision Record)
A recorded, versioned, dated statement of a consequential decision with its
context, problem, options, tradeoffs, chosen solution, consequences, risk, future
impact, and review date. The concrete form of a *Decision Record* (above); defined
by [`governance/Decision_Governance.md`](./governance/Decision_Governance.md) and
indexed in the Decision Registry. **Append-only** (superseded, never deleted).

### RFC (Request For Comments)
A structured proposal used to deliberate a non-trivial change **before** it becomes
a decision; an RFC's approval produces an ADR. Defined by
[`governance/RFC_Process.md`](./governance/RFC_Process.md).

### Change Class
The category that routes a change through its governance path: **Documentation,
Minor, Major, Architecture, Governance, Emergency**. Defined by
[`governance/Change_Management.md`](./governance/Change_Management.md).

### Risk Tier (A0–A3, AE)
The severity classification of a change that sets approval authority and review
depth: **A0** editorial, **A1** minor, **A2** major, **A3** architecture-critical,
**AE** emergency. Defined by
[`governance/Architecture_Governance.md`](./governance/Architecture_Governance.md) §13.1
and shared across the governance suite. (Distinct from a *risk's* Severity/
Probability in [`governance/Risk_Governance.md`](./governance/Risk_Governance.md).)

### AI-TRACE
The mandatory traceability block an AI agent emits with any consequential change
(agent, context read, scope, risk class, decisions, dependencies, assumptions,
invariants, self-validation, required reviewer). Defined by
[`governance/AI_Governance.md`](./governance/AI_Governance.md) §9; it is itself Lore.

### AI Operating System (GCC OS)
The set of **living** documents in `.gcc/` (master memory, state files, registries,
knowledge graph, and the Lore / context-recovery / onboarding / branch / changelog
protocols, plus templates and checklists) that let a human or AI agent recover
context and resume development across dormancy and turnover. Established in
**Phase V0-P4**; see [`../.gcc/README.md`](../.gcc/README.md).

---

## 5A. Quality & Context Terms (V0-P5 / V0-P6)

### Quality Gate
A mandatory, **blocking** checkpoint a change or release must pass on **evidence**
(not assertion). The eight gates (G1 Architecture, G2 Documentation, G3 AI Review,
G4 Testing, G5 Validation, G6 Release, G7 Context Integrity, G8 Governance) are
defined in [`quality/QUALITY_GATES.md`](./quality/QUALITY_GATES.md). Gates **wrap**
the governance checkpoints.

### Validation
The act of **producing the evidence that a claim is true** (a result, a metric, a
"done" status). Organized into a taxonomy (VC-ARCH…VC-CLIN) in
[`quality/VALIDATION_FRAMEWORK.md`](./quality/VALIDATION_FRAMEWORK.md). Distinct
from *verification* of code references (anti-hallucination); both are required.

### Release Certification
The recorded judgment that a release candidate is fit to tag/deploy, with one of
four outcomes — **Approved / Approved with Risk / Deferred / Blocked** — defined in
[`quality/RELEASE_CERTIFICATION.md`](./quality/RELEASE_CERTIFICATION.md).

### Repository Quality Index (RQI)
A 0–100 health gauge aggregating the quality metrics (M1–M12) across five pillars,
defined in [`quality/QUALITY_METRICS.md`](./quality/QUALITY_METRICS.md). A trend
signal only — it never overrides a hard-zero gate failure.

### Postmortem
A **blameless, durable** record of an incident/failure: what happened, root cause,
recovery, lessons, and the **prevention** that makes recurrence impossible/loud.
Defined in [`context/POSTMORTEM_FRAMEWORK.md`](./context/POSTMORTEM_FRAMEWORK.md);
stored in `.gcc/postmortems/`.

### Lesson (Learned)
**Transferable** knowledge (from a success, failure, or surprise) captured to
inform future work, in [`context/LESSONS_LEARNED_SYSTEM.md`](./context/LESSONS_LEARNED_SYSTEM.md)
(stored in `.gcc/learnings/`). Distinct from a *postmortem* (incident-specific) and
an *ADR* (a decision).

### Knowledge / Context / Memory (distinction)
**Knowledge** is raw understanding; **context** is knowledge organized around
*why*; **memory** is context **persisted** in the repository (the `.gcc/`
artifacts). The Context Preservation System ([`context/`](./context/)) turns
knowledge into durable, recoverable memory.

### Assumption Rot
The decay by which an unverified **assumption** is silently treated as fact until
no one remembers it was ever an assumption. Prevented by the assumption lifecycle
in [`context/ASSUMPTION_MEMORY_SYSTEM.md`](./context/ASSUMPTION_MEMORY_SYSTEM.md)
(mandatory verification plan; overdue verification is an audit finding).

---

## 5B. Environment & Certification Terms (V0-P7 / V0-P8)

### Reproducible Environment
An engineering environment that produces identical results from pinned inputs
(toolchain + lockfiles + container), so builds/results regenerate on any machine
(AP-3/AP-6). Defined in [`environment/ENVIRONMENT_PHILOSOPHY.md`](./environment/ENVIRONMENT_PHILOSOPHY.md).

### CI Workflow
A GitHub Actions workflow in `.github/workflows/` that **mechanizes** a quality gate
(documentation→G2, architecture→G1, governance→G8, context→G7, quality→G4/G5,
repository-health→aggregate). CI gates merges but never decides (humans approve, NR-7).
See [`environment/CI_CD_ARCHITECTURE.md`](./environment/CI_CD_ARCHITECTURE.md).

### Environment Validation Gate (EV-1…EV-6)
The checks that prove the environment itself is correct (bootstrap, dependency,
tool, CI, repository-health, recovery). Defined in
[`environment/ENVIRONMENT_VALIDATION.md`](./environment/ENVIRONMENT_VALIDATION.md).

### Certification (Version)
The formal, evidence-backed verdict that a version is complete. V0's outcome model
mirrors release certification: **CERTIFIED / CERTIFIED WITH CONDITIONS / DEFERRED /
BLOCKED**. The V0 record is [`certification/V0_COMPLETION_REPORT.md`](./certification/V0_COMPLETION_REPORT.md)
(ADR-0001). The Founder is the **Certification Authority**.

### Readiness Gate
The set of measurable conditions for entering the next version (e.g.
[`certification/V1_READINESS_GATE.md`](./certification/V1_READINESS_GATE.md)),
enforcing the no-version-skip rule (NR-12).

---

## 6. Project-Structure & Versioning Terms

### Version 0 (V0) — Repository Foundation
The foundational version that establishes the constitution, repository
architecture, and governance. Carries a **zero technical-debt budget**.

### Version 1 (V1) — Offline EEG Platform
Establishes rigorous, reproducible, patient-disjoint, uncertainty-aware **offline**
EEG interpretation.

### Version 2 (V2) — Clinical Workflow Platform
Makes outputs usable inside a real clinical **review workflow**, with full
traceability.

### Version 3 (V3) — Near Real-Time Platform
Adds **near-live** ingestion and incremental inference without sacrificing
validation integrity.

### Version 4 (V4) — Hospital-Ready Foundation
The **strategic destination**: a deployable, governable, auditable, reliable
platform structurally ready for continuous hospital use. A maturity state, **not**
a marketing or regulatory-clearance claim ([`PROJECT_VISION.md`](./PROJECT_VISION.md) §7).

### Phase (e.g. V0-P1, V0-P2, …)
A sub-stage within a version. **V0 comprises eight phases:** **P1** Project
Constitution Layer, **P2** Repository Architecture Foundation, **P3** Governance
Layer, **P4** AI Operating System Foundation, **P5** Quality Assurance Foundation,
**P6** Context Preservation System, **P7** Development Environment Foundation, and
**P8** Version 0 Certification.

### Exit Criteria
The conditions a version must satisfy before the next version may claim its own
exit criteria. Enforced by the version gate (Rule **NR-12**).

### Cross-Version Invariant
A guarantee (e.g. patient-disjoint validation) that, once introduced, may never be
weakened in any later version
([`VERSION_EVOLUTION_MODEL.md`](./VERSION_EVOLUTION_MODEL.md) §6).

---

## 7. Acronym Quick Reference

| Acronym | Expansion | See section |
|---------|-----------|-------------|
| ACNS | American Clinical Neurophysiology Society | §1 |
| ADR | Architecture / Any Decision Record | §5 |
| AI-TRACE | AI traceability block | §5 |
| BCI | Brain-Computer Interface (out of scope) | [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) O2 |
| cEEG | Continuous EEG | §1 |
| EEG | Electroencephalography/-gram | §1 |
| GCC | Governance & Context Control | §5 |
| GPD | Generalized Periodic Discharges | §1 |
| GRDA | Generalized Rhythmic Delta Activity | §1 |
| ICU | Intensive Care Unit | §1 |
| IIC | Ictal-Interictal Continuum | §1 |
| LOSO | Leave-One-Subject-Out | §2 |
| LPD | Lateralized Periodic Discharges | §1 |
| LRDA | Lateralized Rhythmic Delta Activity | §1 |
| NCS/NCSE | Non-Convulsive Seizure / Status Epilepticus | §1 |
| RFC | Request For Comments | §5 |
| RQI | Repository Quality Index | §5A |
| SZ | Seizure | §1 |
| UQ | Uncertainty Quantification | §3 |
| V0–V4 | Versions 0 through 4 | §6 |

---

## Maintaining This Glossary (Lore Protocol)

- A new consequential term **must** be added here when first introduced (Rule
  **NR-14**).
- Definitions change only via a recorded governance decision; a changed definition
  requires re-checking documents that use the term.
- This glossary is the **canonical** reference: where another document’s phrasing
  seems to conflict, the definition here governs, and the conflict is treated as a
  consistency defect to fix.
