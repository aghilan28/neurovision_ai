# PROJECT VISION

> **Document type:** Project Constitution Layer (V0-P1)
> **Status:** Authoritative / Immutable intent
> **Owner:** Founder
> **Update procedure:** Governance-class change (ADR); constitution changes require a recorded, reviewed decision (NR-5).
> **Applies to:** All versions (V0 → V4)
> **Audience:** Human contributors, clinical stakeholders, and AI engineering agents
> **Canonical terminology:** See [`GLOSSARY.md`](./GLOSSARY.md)

This document defines **why NeuroVision AI exists**. It is the highest-level
statement of intent in the repository. Every objective, scope decision,
architectural principle, and line of future code must be traceable back to the
vision described here. If a future change cannot be justified against this
document, that change is out of bounds until the vision is formally amended.

---

## 1. What NeuroVision AI Is

NeuroVision AI is a **production-oriented EEG-AI platform for critical-care
neurology**. Its purpose is to assist clinicians in detecting and characterizing
seizures and seizure-like activity in the **Intensive Care Unit (ICU)** from
continuous EEG (cEEG), with **calibrated uncertainty** attached to every
clinically meaningful output.

NeuroVision AI is **explicitly not**:

- an EEG classifier,
- a research notebook,
- a student project,
- a Kaggle-style competition entry,
- a throwaway prototype.

It is a **multi-year platform** designed to evolve through five deliberate
versions (see [`VERSION_EVOLUTION_MODEL.md`](./VERSION_EVOLUTION_MODEL.md)):

| Version | Name | One-line mission |
|---------|------|------------------|
| **V0** | Repository Foundation | Build the permanent foundation everything else depends on. |
| **V1** | Offline EEG Platform | Prove rigorous, reproducible offline EEG interpretation. |
| **V2** | Clinical Workflow Platform | Make outputs usable inside a real clinical review workflow. |
| **V3** | Near Real-Time Platform | Move from retrospective analysis to near-live monitoring. |
| **V4** | Hospital-Ready Foundation | Become deployable, governable, and auditable in a hospital. |

The vision is a destination (V4). The version model is the road. V0 is the
foundation under the road.

---

## 2. Why The Platform Exists

NeuroVision AI exists because three distinct, compounding problems prevent
EEG-AI from helping patients today: a **clinical problem**, a **technical
problem**, and a **research-to-clinical translation problem**.

### 2.1 The Clinical Problem

In the ICU, **non-convulsive seizures (NCS)** and **non-convulsive status
epilepticus (NCSE)** are common, dangerous, and invisible without EEG. Patients
who are comatose, sedated, or post-cardiac-arrest can be seizing continuously
with **no outward physical sign**. Untreated, this activity is associated with
secondary brain injury and worse outcomes.

The standard of care is **continuous EEG monitoring (cEEG)**, interpreted by
trained neurophysiologists. But:

- **EEG expertise is scarce.** Most hospitals do not have 24/7 access to a
  fellowship-trained epileptologist. Many have none.
- **cEEG produces enormous data volumes.** Days of multichannel EEG per patient
  far exceed what a reviewer can examine exhaustively.
- **Review is delayed.** A seizure that is reviewed hours after it occurs is a
  seizure that was not treated when it mattered.
- **The signal is ambiguous.** Much ICU EEG falls on the
  **Ictal-Interictal Continuum (IIC)** — patterns such as **LPD**, **GPD**,
  **LRDA**, and **GRDA** that are neither clearly seizure nor clearly normal,
  and over which even experts disagree.

The clinical consequence is a **detection and triage gap**: dangerous activity
exists in the data, but the right human does not see it in time.

### 2.2 The Technical Problem

EEG is one of the hardest signals to model reliably:

- **Low signal-to-noise ratio** and pervasive artifact (muscle, movement,
  electrode, electrical).
- **High inter-patient variability** — two patients with the same pattern can
  look completely different, and the same patient can change hour to hour.
- **Non-stationarity** — the statistics of the signal change over time.
- **Montage and hardware heterogeneity** — different electrode layouts,
  reference schemes, amplifiers, and sampling rates across sites and machines.
- **Expert label noise** — ground truth itself is uncertain on the IIC, so
  models trained naively inherit and amplify that ambiguity.

A model that ignores these realities can score well on a clean test split and
**fail completely** in a different ICU, on a different machine, in a different
month. The technical problem is not "can a model classify a segment?" — it is
**"can a system stay trustworthy under domain shift, artifact, and ambiguity,
and say so honestly when it is uncertain?"**

### 2.3 The Research-to-Clinical Translation Problem

The literature is full of EEG-AI models with impressive published accuracy that
**never reach a patient**. The translation gap is caused by predictable failure
modes:

- **Data leakage.** Splitting train/test by *recording* or *segment* instead of
  by *patient* lets the model memorize patient identity. Reported metrics are
  inflated and do not survive **patient-disjoint** evaluation (see
  [`GLOSSARY.md`](./GLOSSARY.md) → *LOSO*, *patient-disjoint validation*).
- **Overconfidence.** Models emit a single point prediction with no honest
  measure of uncertainty, so clinicians cannot calibrate trust.
- **Irreproducibility.** Preprocessing is undocumented or nondeterministic;
  results cannot be regenerated, audited, or defended.
- **No governance.** There is no record of *why* a decision was made, so the
  system cannot be safely changed, reviewed, or certified.
- **Architecture rewrites.** Each new idea triggers a rewrite, destroying
  accumulated validation and trust.

NeuroVision AI exists to **close this translation gap by construction** — by
treating reproducibility, patient-disjoint validation, uncertainty, and
governance as **first-class, non-negotiable platform features**, not afterthoughts.

---

## 3. Why EEG-AI Systems Fail In Real Deployment

This section is intentionally explicit, because **avoiding these failures is the
core reason the platform is structured the way it is.**

1. **They are validated on the wrong split.** Segment- or recording-level splits
   leak patient identity. The model looks excellent, then collapses on unseen
   patients. *NeuroVision AI mandates patient-disjoint (LOSO-style) validation
   everywhere — see [`ARCHITECTURAL_PRINCIPLES.md`](./ARCHITECTURAL_PRINCIPLES.md).*

2. **They break under domain shift.** A new site, montage, amplifier, or patient
   population shifts the input distribution and the model silently degrades.
   *NeuroVision AI treats domain shift as an expected operating condition, not an
   edge case, and measures performance under shift.*

3. **They are confidently wrong.** A softmax score is not a probability of
   correctness. Overconfident errors are the most dangerous kind in medicine.
   *NeuroVision AI requires calibrated uncertainty (e.g. Conformal Prediction)
   on every clinical output.*

4. **They cannot be reproduced.** Nondeterministic preprocessing and unpinned
   environments make results impossible to regenerate or audit. *NeuroVision AI
   mandates deterministic, versioned preprocessing.*

5. **They cannot be governed.** No decision record, no boundary enforcement, no
   audit trail. The system cannot be safely evolved or certified. *NeuroVision
   AI builds a Governance & Context Control (GCC) layer from V0.*

6. **They rot.** Architecture drift and context drift accumulate until the
   system is unmaintainable and no one remembers why anything was built. *The
   Lore Protocol and versioned documentation exist to prevent exactly this.*

A system that does not engineer against these failures is not a clinical
platform — it is a demo with a short shelf life.

---

## 4. Why Uncertainty Quantification Matters

In critical care, **the cost of an error is asymmetric and the cost of an honest
"I am not sure" is low**. A clinician who knows the system is uncertain can
review the segment themselves. A clinician who is given a confident wrong answer
may act on it.

NeuroVision AI therefore treats **uncertainty quantification (UQ)** as a core
output, not a nice-to-have:

- Every clinically meaningful prediction carries a **calibrated** measure of
  confidence with **statistical coverage guarantees** where possible (e.g.
  Conformal Prediction produces prediction sets with a guaranteed error rate).
- The system is explicitly allowed to **abstain or escalate** rather than force
  a low-confidence decision.
- Uncertainty is a **design constraint that flows down through the architecture**:
  the ML layer must produce it, the application layer must preserve it, and the
  presentation layer must communicate it faithfully to a human.

UQ is what turns a classifier into a **decision-support instrument that a
clinician can reason about.**

---

## 5. Why Architectural Governance Matters

A clinical platform that lives for a decade will be touched by many people and
many AI agents. Without governance, three things happen:

- **Architecture drift:** the implemented system slowly diverges from the
  intended architecture until the documentation is fiction.
- **Context drift:** the *reasons* behind decisions are lost; new contributors
  re-litigate settled questions or unknowingly break invariants.
- **Silent debt:** shortcuts accumulate invisibly until the system is fragile.

Governance is the discipline that keeps intent and implementation aligned. In
NeuroVision AI it is **mechanized**, not merely aspirational:

- The **Governance & Context Control (GCC)** layer (`.gcc/`, formally
  implemented in **Phase V0-P3**) encodes architectural rules, import
  constraints, and decision records in a machine-checkable form.
- The **Lore Protocol** (see [`GLOSSARY.md`](./GLOSSARY.md)) is the discipline of
  capturing durable project knowledge — rationale, constraints, terminology — so
  that the repository remains self-explanatory.

Governance matters because **it is cheaper to prevent drift than to recover from
it**, and because a system that cannot prove why it behaves as it does cannot be
trusted with patients.

---

## 6. Why Maintainability Matters

This platform is a **multi-year effort**. The dominant cost over its life is not
writing code — it is **understanding, changing, and trusting** code that already
exists. Maintainability is therefore a clinical-safety property, not a
developer-comfort preference:

- A maintainable system can be **fixed quickly** when a patient-facing problem is
  found.
- A maintainable system can be **audited** when a regulator or clinician asks
  "why did it say that?"
- A maintainable system can **absorb new evidence** (new data, new patterns, new
  models) without a rewrite that destroys accumulated validation.

NeuroVision AI optimizes for **survivability and maintainability over speed and
convenience**. This is a deliberate, permanent trade-off recorded in
[`NON_NEGOTIABLE_RULES.md`](./NON_NEGOTIABLE_RULES.md).

---

## 7. The Long-Term Vision: Why Version 4 Exists

**Version 4 — the Hospital-Ready Foundation — is the strategic destination of
the entire project.** Every earlier version exists to make V4 achievable without
a rewrite.

V4 is the version where NeuroVision AI is:

- **Deployable** inside a hospital's technical and security environment,
- **Governable** with full decision records and enforced boundaries,
- **Auditable** end-to-end (every output traceable to inputs, model version,
  preprocessing version, and uncertainty),
- **Reliable** under real-world domain shift and operational load,
- **Maintainable** by a team that did not necessarily build the original system.

V4 is **not** a marketing milestone and it is **not** a regulatory clearance
claim. It is an **engineering and governance maturity state**: the point at
which the platform is structurally ready to be entrusted with continuous
clinical use.

V4 exists as an explicit goal because **building toward an undefined "someday
production" is how EEG-AI projects fail.** Naming the destination forces every
intermediate version to pay its structural debts on time. See
[`VERSION_EVOLUTION_MODEL.md`](./VERSION_EVOLUTION_MODEL.md) for why skipping
versions toward V4 is forbidden.

---

## 8. Strategic Mission

> **Mission:** Build a trustworthy, reproducible, uncertainty-aware EEG-AI
> platform that helps critical-care clinicians detect and characterize seizures
> and the ictal-interictal continuum in time to matter — and that can be
> maintained, governed, and trusted for a decade.

The mission rests on four load-bearing commitments:

1. **Trust by construction** — patient-disjoint validation, calibrated
   uncertainty, deterministic preprocessing.
2. **Governance by construction** — enforced boundaries, decision records, audit
   trails (GCC).
3. **Evolution without rewrites** — a stable architecture that grows V0 → V4.
4. **Clinical relevance** — measured against what helps a clinician, not against
   leaderboard accuracy.

---

## 9. Strategic Success Criteria

The project is succeeding, at the strategic level, when **all** of the following
hold:

- **Validation integrity:** every reported metric comes from patient-disjoint
  evaluation; no result depends on a leaked split.
- **Calibrated trust:** clinically meaningful outputs carry uncertainty whose
  calibration is measured and honest, not assumed.
- **Reproducibility:** any result can be regenerated from pinned inputs, code
  versions, and deterministic preprocessing.
- **Architectural stability:** the architecture established in V0 still stands at
  V4 — extended, not rewritten.
- **Governance:** every consequential decision has a recorded rationale; module
  boundaries are enforced, not merely described.
- **Maintainability:** a competent new contributor (human or AI) can understand
  project direction from the repository alone, without the original research
  corpus.
- **Clinical alignment:** capabilities map to real ICU needs (detection, triage,
  characterization of the IIC), not to whatever is easiest to model.

These criteria are made measurable in
[`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md).

---

## 10. Failure Scenarios (What We Are Engineering Against)

The vision is defined as much by the failures we refuse to accept as by the
successes we pursue. The project has **failed**, regardless of any metric, if:

- **Leakage failure:** impressive metrics turn out to depend on non-patient-disjoint
  splits.
- **Overconfidence failure:** the system emits confident predictions with no
  honest, calibrated uncertainty and a clinician is misled.
- **Irreproducibility failure:** a result cannot be regenerated or audited.
- **Drift failure:** the implemented system silently diverges from its documented
  architecture (architecture drift) or the rationale behind it is lost (context
  drift).
- **Rewrite failure:** progress requires throwing away the architecture and the
  validation built on it.
- **Governance failure:** a change ships with no recorded rationale, no review,
  or by violating a module boundary.
- **Scope failure:** the platform drifts into out-of-scope territory (seizure
  prediction, BCI, consumer EEG) and dilutes its clinical mission — see
  [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md).
- **Silent-debt failure:** shortcuts are taken to move faster and are never
  recorded or repaid.

Each failure scenario has a corresponding defense encoded in the architectural
principles, non-negotiable rules, and governance layer.

---

## 11. Target Users

NeuroVision AI is built for, and evaluated against the needs of, the following
users. (Some are served only in later versions; the version that introduces each
is noted.)

| User | Need | Served from |
|------|------|-------------|
| **Critical-care neurologist / epileptologist** | Faster, prioritized review of cEEG; honest uncertainty to calibrate trust. | V2+ |
| **ICU intensivist** | Early signal that a patient may be seizing and needs expert attention. | V3+ |
| **EEG technologist** | Reliable, reproducible processing of recordings across machines/montages. | V1+ |
| **Clinical researcher** | Reproducible, patient-disjoint benchmarks on the IIC. | V1+ |
| **ML / platform engineer** | A stable, well-governed architecture that can be extended without rewrites. | V0+ |
| **Hospital IT / security / compliance** | A deployable, auditable, governable system. | V4 |
| **Future AI engineering agents** | A self-explanatory repository whose intent and boundaries are machine-discoverable. | V0+ |

The clinician is always the **decision-maker**. NeuroVision AI is
**decision-support**; it never replaces clinical judgment.

---

## 12. Platform Philosophy

The following beliefs are the cultural DNA of the project. They resolve ties when
a decision is otherwise ambiguous.

1. **Survivability over speed.** We optimize for a system that lasts a decade,
   not for a milestone next week.
2. **Honesty over confidence.** A calibrated "uncertain" is more valuable than a
   confident guess.
3. **Reproducibility over cleverness.** A result that cannot be regenerated does
   not exist.
4. **Patient-disjoint or it didn't happen.** No metric is real unless the
   evaluation is patient-disjoint.
5. **Boundaries are real.** Module boundaries and import rules are enforced, not
   suggested (see [`architecture/IMPORT_RULES.md`](./architecture/IMPORT_RULES.md)).
6. **Document the why, not just the what.** The reasoning is the asset; code is
   replaceable, rationale is not (the Lore Protocol).
7. **No rewrites.** We extend the architecture; we do not restart it.
8. **Govern by construction.** Rules that are merely written are rules that will
   be broken; rules that are mechanized are rules that hold.
9. **Clinical relevance is the north star.** We measure ourselves against what
   helps a clinician and a patient.
10. **Stay in scope.** The discipline to *not* build something is as important as
    the ability to build it.

---

## 13. Relationship To Other Constitution Documents

This vision is the root. It is elaborated by:

- [`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md) — turns vision into
  measurable objectives, metrics, and acceptance criteria.
- [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) — defines what is in, out, future, and
  rejected scope, with rationale.
- [`VERSION_EVOLUTION_MODEL.md`](./VERSION_EVOLUTION_MODEL.md) — defines the V0→V4
  road and why each version exists.
- [`ARCHITECTURAL_PRINCIPLES.md`](./ARCHITECTURAL_PRINCIPLES.md) — the immutable
  principles that realize the vision in structure.
- [`NON_NEGOTIABLE_RULES.md`](./NON_NEGOTIABLE_RULES.md) — the laws that protect
  the vision from erosion.
- [`GLOSSARY.md`](./GLOSSARY.md) — the canonical meaning of every term used above.

**This document may only be changed through a recorded, reviewed governance
decision.** It is not edited casually. If the vision changes, everything
downstream must be re-checked against it.
