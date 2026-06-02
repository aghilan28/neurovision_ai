# ARCHITECTURAL PRINCIPLES

> **Document type:** Project Constitution Layer (V0-P1)
> **Status:** Authoritative / Immutable principles
> **Owner:** Founder (Architecture Owner role)
> **Update procedure:** Governance-class change (ADR); principle changes require a recorded, reviewed decision (NR-5).
> **Derived from:** [`PROJECT_VISION.md`](./PROJECT_VISION.md), [`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md)
> **Enforced by:** [`NON_NEGOTIABLE_RULES.md`](./NON_NEGOTIABLE_RULES.md), the Governance & Context Control layer (`.gcc/`), and the architecture docs in [`architecture/`](./architecture/)
> **Canonical terminology:** [`GLOSSARY.md`](./GLOSSARY.md)

These are the **immutable principles** that turn the vision into structure. A
principle is a long-lived design commitment; it differs from a *rule* (a project
law in [`NON_NEGOTIABLE_RULES.md`](./NON_NEGOTIABLE_RULES.md)) in that a principle
describes *how we build*, while a rule describes *what may never happen.*

Each principle is specified with: **Description**, **Purpose**, **Reason**,
**Enforcement strategy**, and **Violation examples.** Principles may only change
through a recorded, reviewed governance decision; changing one requires
re-checking every dependent document.

---

## AP-1 · No Architecture Rewrites

**Description.** The layered architecture defined in V0 is **extended, never
restarted.** New capability is added by populating and extending existing modules
within their boundaries, not by replacing the architecture.

**Purpose.** Preserve accumulated validation, trust, and institutional knowledge
across V0 → V4.

**Reason.** Rewrites are the most common way EEG-AI projects destroy hard-won
validation and credibility; each rewrite resets trust to zero and invites new
leakage and drift.

**Enforcement strategy.** Architecture changes require a recorded governance
decision; the GCC layer tracks the architecture baseline; PR review rejects
"start over" changes; the version model forbids rewrites as a cross-version
invariant.

**Violation examples.** Replacing the module layout to chase a new framework;
re-implementing preprocessing in a parallel structure instead of extending it;
"v2 of the codebase" that discards V0–V1 boundaries.

---

## AP-2 · Patient-Disjoint Validation

**Description.** All evaluation splits are **patient-disjoint**: no patient's data
appears in more than one of train/validation/test. **LOSO-style** evaluation is
the default regime.

**Purpose.** Produce metrics that reflect performance on **unseen patients**,
which is the only performance that matters clinically.

**Reason.** Segment- or recording-level splits leak patient identity and inflate
metrics; this is the single most common cause of EEG-AI translation failure
(Vision §3).

**Enforcement strategy.** The `evaluation/` module enforces patient-disjoint
splits by construction; tests assert disjointness; reported metrics that are not
patient-disjoint are treated as a failure metric
([`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md) §6); GCC records the split
provenance of every result.

**Violation examples.** Random segment shuffling before splitting; the same
patient in train and test; "k-fold by recording"; tuning hyperparameters on the
test patients.

---

## AP-3 · Deterministic Preprocessing

**Description.** Preprocessing (filtering, montage handling, windowing,
normalization) is **deterministic and versioned**: identical inputs and a pinned
preprocessing version always yield identical outputs.

**Purpose.** Make every downstream result reproducible and auditable.

**Reason.** Nondeterministic or undocumented preprocessing makes results
impossible to regenerate, compare, or defend — a core translation failure.

**Enforcement strategy.** The `preprocessing/` module is pure and dependency-free
(imports nobody — see [`architecture/IMPORT_RULES.md`](./architecture/IMPORT_RULES.md));
seeds and parameters are pinned and versioned; determinism is unit-tested; the
preprocessing version is recorded with every output.

**Violation examples.** Unseeded random augmentation in the production path;
filter parameters that vary by run; hidden global state; preprocessing that
depends on wall-clock time or unordered data.

---

## AP-4 · Uncertainty-Aware Inference

**Description.** Every clinically meaningful output carries **calibrated
uncertainty** (e.g. Conformal Prediction), and the system may **abstain or
escalate** instead of forcing a low-confidence decision.

**Purpose.** Let clinicians calibrate trust; make honest uncertainty a
first-class output.

**Reason.** Overconfident point predictions are the most dangerous error class in
critical care (Vision §4).

**Enforcement strategy.** The `ml/` layer must emit uncertainty; the `backend/`
must preserve it; the `frontend/` must present it faithfully (uncertainty flows
down the layers — see [`architecture/LAYERED_ARCHITECTURE.md`](./architecture/LAYERED_ARCHITECTURE.md));
calibration/coverage are measured in `evaluation/`.

**Violation examples.** Returning only a class label; dropping uncertainty at the
API boundary; a UI that hides or flattens uncertainty; uncalibrated softmax
presented as probability of correctness.

---

## AP-5 · Clinical Traceability

**Description.** Every clinical output is **traceable end-to-end**: to its input
data, preprocessing version, model version, and reported uncertainty.

**Purpose.** Enable audit, debugging, and clinical accountability ("why did it say
that?").

**Reason.** A clinical platform must be able to explain and reconstruct any output
it ever produced.

**Enforcement strategy.** Outputs carry provenance metadata; the audit trail is a
V2 exit criterion; GCC verifies traceability; the data flow is documented in
[`architecture/SYSTEM_CONTEXT.md`](./architecture/SYSTEM_CONTEXT.md).

**Violation examples.** A displayed detection with no link to its source segment;
results produced by an unrecorded model version; preprocessing that cannot be
identified after the fact.

---

## AP-6 · Reproducibility

**Description.** Any reported result can be **regenerated** from pinned inputs,
pinned code, and a versioned environment.

**Purpose.** Make results trustworthy, comparable, and defensible over years.

**Reason.** A result that cannot be regenerated effectively does not exist
(Vision §12).

**Enforcement strategy.** Determinism (AP-3) + pinned environments + recorded
provenance (AP-5); reproducibility checks in `tests/`; reproducibility is a V1
exit criterion.

**Violation examples.** Unpinned dependencies; results that change run-to-run with
no recorded reason; "we can't reproduce the old number" treated as acceptable.

---

## AP-7 · Modularity & Strict Boundaries

**Description.** The system is decomposed into modules with **single
responsibilities** and **explicit, enforced boundaries**. Dependencies flow in
one direction only (top layers depend on lower layers; never the reverse).

**Purpose.** Contain change, enable independent reasoning/testing, and prevent the
tangle that makes systems unmaintainable.

**Reason.** Maintainability is a clinical-safety property (Vision §6); enforced
boundaries are how modularity survives contact with deadlines.

**Enforcement strategy.** Per-directory README contracts;
[`architecture/MODULE_BOUNDARIES.md`](./architecture/MODULE_BOUNDARIES.md) and
[`architecture/IMPORT_RULES.md`](./architecture/IMPORT_RULES.md); an **acyclic**
[`architecture/DEPENDENCY_GRAPH.md`](./architecture/DEPENDENCY_GRAPH.md); GCC
import checks.

**Violation examples.** `frontend` importing `ml`; `preprocessing` importing
`backend`; a circular dependency; a "utils" module that everything depends on and
that depends on everything.

---

## AP-8 · Auditability

**Description.** The platform's **behavior and decisions** are auditable:
consequential changes have recorded rationale, and operational behavior is
observable.

**Purpose.** Make the system governable and defensible — by reviewers, clinicians,
and (eventually) regulators.

**Reason.** A system that cannot be audited cannot be safely deployed in a
hospital.

**Enforcement strategy.** Decision records in the governance layer (`.gcc/`);
observability in `monitoring/`; audit-trail completeness tests; auditability is a
V4 exit criterion.

**Violation examples.** A consequential change with no recorded rationale; a
production model with no observability; an output that cannot be explained after
the fact.

---

## AP-9 · Versioned Decisions

**Description.** Consequential architectural and methodological decisions are
**recorded, versioned, and dated**, with their rationale and the alternatives
considered.

**Purpose.** Prevent context drift and re-litigation; preserve the *why*.

**Reason.** Code shows *what*; only recorded decisions preserve *why* across team
and AI-agent turnover (the Lore Protocol).

**Enforcement strategy.** Decision records governed by `.gcc/`; the Lore Protocol
(see [`GLOSSARY.md`](./GLOSSARY.md)); review rejects consequential changes lacking
a recorded decision.

**Violation examples.** "We changed the model but nobody knows why"; an undocumented
boundary change; reversing a prior decision without acknowledging it existed.

---

## AP-10 · Domain-Shift Awareness

**Description.** **Domain shift** (new site, montage, amplifier, population) is
treated as an **expected operating condition**, measured explicitly — not an edge
case to be discovered in production.

**Purpose.** Build robustness and honesty about generalization into the platform.

**Reason.** EEG-AI commonly breaks under shift; ignoring shift produces systems
that work only where they were trained (Vision §3).

**Enforcement strategy.** Held-out-site/montage evaluation in `evaluation/`;
drift detection in `monitoring/`; shift robustness is a secondary objective (S1).

**Violation examples.** Reporting only in-distribution metrics as if general; no
held-out-site evaluation; no drift monitoring in deployment.

---

## AP-11 · Governance & Context Control By Construction

**Description.** Governance is **mechanized**, not aspirational. Boundaries,
import rules, decision records, and context are encoded so they are
**machine-checkable** via the Governance & Context Control (GCC) layer.

**Purpose.** Keep intent and implementation aligned automatically; prevent
architecture and context drift.

**Reason.** Rules that are merely written get broken; rules that are mechanized
hold (Vision §5).

**Enforcement strategy.** The `.gcc/` layer (V0-P3) implements import/boundary
checks and decision-record management; CI integrates GCC checks; the Lore Protocol
maintains durable context.

**Violation examples.** Boundary rules documented but never checked; a governance
process that depends entirely on memory; decisions kept in private chat instead of
the record.

---

## AP-12 · Survivability Over Speed

**Description.** When designs trade off, the platform chooses the option that
**survives a decade** over the option that ships fastest.

**Purpose.** Optimize for the dominant lifetime cost (understanding, changing,
trusting), not the smallest immediate cost.

**Reason.** This is a multi-year clinical platform; speed-driven shortcuts become
patient-facing risk (Vision §6, §12).

**Enforcement strategy.** Conflict-resolution priority order
([`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md) §9: Governance → Clinical
safety → Reproducibility → Clinical utility → Research novelty → Speed); debt is
recorded and repaid; review weighs longevity over expedience.

**Violation examples.** "We'll validate later"; merging a shortcut without
recording the debt; choosing a fragile design because it is faster to write.

---

## Principle Map

| Principle | Primary enforcing artifacts | Realizes objective |
|-----------|-----------------------------|--------------------|
| AP-1 No rewrites | Version model; GCC baseline | P5 |
| AP-2 Patient-disjoint | `evaluation/`; tests; GCC provenance | P3 |
| AP-3 Deterministic preprocessing | `preprocessing/`; import rules; tests | P4 |
| AP-4 Uncertainty-aware | `ml/`→`backend/`→`frontend/`; `evaluation/` | P2 |
| AP-5 Traceability | provenance metadata; `.gcc/`; system context | S5 |
| AP-6 Reproducibility | determinism + pinning + provenance; tests | P4 |
| AP-7 Modularity/boundaries | architecture docs; per-dir READMEs; GCC | P5 |
| AP-8 Auditability | `.gcc/`; `monitoring/`; tests | S5/L1 |
| AP-9 Versioned decisions | `.gcc/` decision records; Lore Protocol | P6 |
| AP-10 Domain-shift awareness | `evaluation/`; `monitoring/` | S1 |
| AP-11 Governance by construction | `.gcc/` (V0-P3); CI | P6 |
| AP-12 Survivability over speed | priority order; debt records | P5 |

---

## Relationship To Other Documents

- Principles **realize** [`PROJECT_VISION.md`](./PROJECT_VISION.md) and
  [`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md).
- Principles are **enforced as laws** in
  [`NON_NEGOTIABLE_RULES.md`](./NON_NEGOTIABLE_RULES.md).
- Principles are **operationalized** in
  [`architecture/`](./architecture/) and the per-directory READMEs.

Principle changes are governance events and require a recorded, reviewed decision.
