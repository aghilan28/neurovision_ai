# NON-NEGOTIABLE RULES

> **Document type:** Project Constitution Layer (V0-P1)
> **Status:** Authoritative / Project law
> **Owner:** Founder
> **Update procedure:** Governance-class change (ADR); rule changes require a recorded, reviewed decision (NR-5).
> **Enforces:** [`ARCHITECTURAL_PRINCIPLES.md`](./ARCHITECTURAL_PRINCIPLES.md), [`PROJECT_VISION.md`](./PROJECT_VISION.md), [`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md), [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md)
> **Mechanized by:** the Governance & Context Control layer (`.gcc/`, V0-P3)
> **Canonical terminology:** [`GLOSSARY.md`](./GLOSSARY.md)

These are the **laws of the project.** A *principle*
([`ARCHITECTURAL_PRINCIPLES.md`](./ARCHITECTURAL_PRINCIPLES.md)) describes *how we
build*; a **rule** here describes *what may never happen.* Violating a rule is a
**stop-and-remediate** event, not a backlog item.

Each rule is specified with: **Rule**, **Rationale**, **Risk prevented**, and
**Enforcement mechanism.** Rules may only change through a recorded, reviewed
governance decision.

> **Severity convention.** Every rule is **MANDATORY**. There are no
> "soft" rules in this document. If a rule cannot be honored, work stops and a
> governance decision is opened — the rule is not quietly bypassed.

---

## NR-1 · Never Optimize For Speed Over Architecture

**Rule.** No deadline, demo, or convenience justifies a change that weakens the
architecture, boundaries, or validation guarantees.

**Rationale.** This is a multi-year clinical platform; the dominant cost is its
decade-long life, not this week's milestone (Principle **AP-12**).

**Risk prevented.** Speed-driven shortcuts that become patient-facing risk and
unmaintainable debt — the "ship fast, validate later" failure
([`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) R4).

**Enforcement mechanism.** Conflict-resolution priority order
([`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md) §9, speed last); PR review
rejects architecture-weakening shortcuts; GCC blocks boundary-violating merges.

---

## NR-2 · Never Accept Hidden Technical Debt

**Rule.** All technical debt must be **recorded** (what, why, risk, repayment
plan) in the governance layer. Undocumented debt is forbidden in every version.

**Rationale.** Recorded debt is a managed liability; hidden debt is a latent
failure whose cost is paid by clinicians and patients
([`VERSION_EVOLUTION_MODEL.md`](./VERSION_EVOLUTION_MODEL.md) §7).

**Risk prevented.** The "silent-debt failure"
([`PROJECT_VISION.md`](./PROJECT_VISION.md) §10).

**Enforcement mechanism.** Debt records in `.gcc/`; review requires a debt entry
for any acknowledged shortcut; the V0 debt budget is **zero**.

---

## NR-3 · Never Bypass Validation

**Rule.** No result may be reported, displayed, or relied upon unless it comes
from **patient-disjoint** evaluation. Validation is never skipped "to save time."

**Rationale.** Leaked splits are the #1 cause of EEG-AI translation failure
(Principle **AP-2**).

**Risk prevented.** Inflated metrics that collapse on unseen patients — the
"leakage failure."

**Enforcement mechanism.** `evaluation/` enforces patient-disjoint splits by
construction; tests assert disjointness; non-patient-disjoint metrics are a
failure metric ([`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md) §6); GCC records
split provenance.

---

## NR-4 · Never Ship A Clinical Output Without Calibrated Uncertainty

**Rule.** Every clinically meaningful output must carry **calibrated uncertainty**
and support **abstain/escalate**. Bare labels/scores are not acceptable clinical
outputs.

**Rationale.** Overconfident errors are the most dangerous class in critical care
(Principle **AP-4**).

**Risk prevented.** The "overconfidence failure" — a clinician misled by a
confident wrong answer.

**Enforcement mechanism.** `ml/` must emit uncertainty; `backend/` must preserve
it; `frontend/` must present it faithfully; calibration/coverage measured in
`evaluation/`; GCC checks the output contract.

---

## NR-5 · Never Change Architecture Without Documentation

**Rule.** No architectural or boundary change without a **recorded, versioned
decision** (rationale + alternatives) made before/with the change.

**Rationale.** Code preserves *what*; only recorded decisions preserve *why*
(Principles **AP-9**, **AP-11**; the Lore Protocol).

**Risk prevented.** Context drift and re-litigation — the "context-drift failure."

**Enforcement mechanism.** Decision records in `.gcc/`; review rejects
consequential architectural changes lacking a decision record.

---

## NR-6 · Never Allow A Repository-Wide Architecture Rewrite

**Rule.** The architecture defined in V0 is **extended, never restarted.** "Start
over" changes are prohibited.

**Rationale.** Rewrites destroy accumulated validation and trust (Principle
**AP-1**).

**Risk prevented.** The "rewrite failure"; resetting clinical trust to zero.

**Enforcement mechanism.** Version model cross-version invariant; GCC tracks the
architecture baseline; review rejects rewrites; a genuine architecture change
needs an explicit, recorded governance decision (and is never a casual refactor).

---

## NR-7 · Never Allow Unreviewed Code Into The Platform (Including AI-Generated Code)

**Rule.** No code — **human- or AI-generated** — enters the platform without human
review against the constitution and the boundaries.

**Rationale.** AI agents are first-class contributors here; unreviewed generation
is exactly how silent boundary/validation violations enter
([`PROJECT_VISION.md`](./PROJECT_VISION.md) §5).

**Risk prevented.** Unvetted changes that violate principles, boundaries, or scope.

**Enforcement mechanism.** Mandatory review on every change; GCC boundary/import
checks in CI; AI-generated changes are held to the **same or higher** review bar
as human changes.

---

## NR-8 · Never Violate Module Boundaries Or Import Rules

**Rule.** The dependency direction is fixed and **acyclic**. The forbidden imports
in [`architecture/IMPORT_RULES.md`](./architecture/IMPORT_RULES.md) are never
introduced — notably: **frontend never imports backend/ml/preprocessing/datasets/
evaluation**, and **preprocessing imports nobody.**

**Rationale.** Enforced boundaries are how modularity and maintainability survive
deadlines (Principle **AP-7**).

**Risk prevented.** The "architecture-drift failure"; the dependency tangle that
makes systems unmaintainable.

**Enforcement mechanism.** Per-directory README contracts;
[`architecture/DEPENDENCY_GRAPH.md`](./architecture/DEPENDENCY_GRAPH.md) (acyclic);
GCC import checks fail the build on violation.

---

## NR-9 · Never Make Preprocessing Nondeterministic

**Rule.** Production-path preprocessing must be **deterministic and versioned**:
same input + same version ⇒ same output.

**Rationale.** Determinism is the foundation of reproducibility and auditability
(Principles **AP-3**, **AP-6**).

**Risk prevented.** The "irreproducibility failure."

**Enforcement mechanism.** `preprocessing/` is pure and dependency-free; seeds/
parameters pinned and versioned; determinism unit-tested; preprocessing version
recorded with every output.

---

## NR-10 · Never Report A Result That Cannot Be Reproduced

**Rule.** Every reported result must be **regenerable** from pinned inputs, pinned
code, and a versioned environment.

**Rationale.** A result that cannot be regenerated effectively does not exist
(Principle **AP-6**).

**Risk prevented.** Irreproducible claims that cannot be audited or defended.

**Enforcement mechanism.** Determinism + pinned environments + recorded provenance;
reproducibility checks in `tests/`; reproducibility is a V1 exit criterion.

---

## NR-11 · Never Produce A Clinical Output That Cannot Be Traced

**Rule.** Every clinical output must be **traceable end-to-end** to its input,
preprocessing version, model version, and uncertainty.

**Rationale.** A clinical platform must be able to explain any output it produced
(Principles **AP-5**, **AP-8**).

**Risk prevented.** Un-auditable outputs; inability to answer "why did it say
that?".

**Enforcement mechanism.** Provenance metadata on outputs; audit-trail is a V2
exit criterion; GCC verifies traceability; audit-completeness tests.

---

## NR-12 · Never Skip A Version

**Rule.** A version may not claim its exit criteria until **every prior version's
exit criteria are satisfied and recorded.**

**Rationale.** Each version de-risks the next; skipping relocates risk to where it
is most expensive ([`VERSION_EVOLUTION_MODEL.md`](./VERSION_EVOLUTION_MODEL.md) §8).

**Risk prevented.** Building clinical/real-time/hospital layers on unvalidated
foundations.

**Enforcement mechanism.** Version-gate decision records in `.gcc/`; exit-criteria
checklists; review enforces gate order.

---

## NR-13 · Never Work Outside Scope

**Rule.** No work begins on **OUT OF SCOPE** or **REJECTED** capabilities. FUTURE
scope is promoted only by a recorded governance decision.

**Rationale.** Scope discipline is a clinical-safety property; dilution causes
the "scope-creep failure" ([`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md)).

**Risk prevented.** Drift into seizure prediction, BCI, consumer EEG, autonomous
decisions, etc.

**Enforcement mechanism.** Scope check before work starts; scope changes are
governance events; review rejects out-of-scope work.

---

## NR-14 · Never Lose The Rationale (Lore Protocol)

**Rule.** Consequential knowledge — decisions, constraints, terminology — must be
captured in versioned documentation so the repository stays **self-explanatory**
without the original research corpus.

**Rationale.** Context is the asset most easily lost across team/AI-agent turnover
(Principle **AP-9**; the Lore Protocol).

**Risk prevented.** Context drift; a repository that no future human or AI agent
can understand.

**Enforcement mechanism.** The Lore Protocol governed by `.gcc/`; the glossary as
the canonical terminology source; review requires terms to be defined and
decisions recorded.

---

## NR-15 · Never Treat Domain Shift As An Edge Case

**Rule.** Generalization claims require **held-out-site/montage** evaluation;
in-distribution-only metrics must not be presented as general performance.

**Rationale.** Domain shift is an expected operating condition, not a rare edge
case (Principle **AP-10**).

**Risk prevented.** The "domain-shift failure" — systems that work only where
they were trained.

**Enforcement mechanism.** Held-out-site evaluation in `evaluation/`; drift
monitoring in `monitoring/`; review checks generalization claims against the
evaluation regime.

---

## Rule Compliance Summary

| Rule | Enforces principle | Prevents failure ([Vision §10](./PROJECT_VISION.md)) |
|------|--------------------|------------------------------------------------------|
| NR-1 Speed over architecture | AP-12 | silent-debt / rewrite |
| NR-2 Hidden debt | AP-12 | silent-debt |
| NR-3 Bypass validation | AP-2 | leakage |
| NR-4 No uncertainty | AP-4 | overconfidence |
| NR-5 Undocumented architecture change | AP-9/AP-11 | context drift |
| NR-6 Rewrite | AP-1 | rewrite |
| NR-7 Unreviewed code | AP-11 | governance |
| NR-8 Boundary/import violation | AP-7 | architecture drift |
| NR-9 Nondeterministic preprocessing | AP-3 | irreproducibility |
| NR-10 Irreproducible result | AP-6 | irreproducibility |
| NR-11 Untraceable output | AP-5/AP-8 | governance/audit |
| NR-12 Version skipping | (version model) | rewrite/foundation |
| NR-13 Out of scope | (scope) | scope creep |
| NR-14 Lost rationale | AP-9 | context drift |
| NR-15 Domain shift as edge case | AP-10 | domain shift |

---

## How These Rules Are Applied

1. **Before work:** confirm scope (NR-13) and version gate (NR-12).
2. **During work:** respect boundaries (NR-8), determinism (NR-9), validation
   (NR-3), uncertainty (NR-4).
3. **At review:** require recorded decisions (NR-5), human review of all code
   incl. AI-generated (NR-7), recorded debt (NR-2), reproducibility (NR-10),
   traceability (NR-11), and rationale capture (NR-14).
4. **Always:** never rewrite (NR-6), never trade architecture for speed (NR-1),
   never treat domain shift as an edge case (NR-15).

A violation halts the change until remediated and recorded.

---

## Relationship To Other Documents

- These rules **enforce** the principles in
  [`ARCHITECTURAL_PRINCIPLES.md`](./ARCHITECTURAL_PRINCIPLES.md) and protect the
  vision/objectives/scope.
- They are **mechanized** by the Governance & Context Control layer
  ([`../.gcc/README.md`](../.gcc/README.md)) and the architecture docs in
  [`architecture/`](./architecture/).

Rule changes are governance events and require a recorded, reviewed decision.
