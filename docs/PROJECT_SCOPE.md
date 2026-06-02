# PROJECT SCOPE

> **Document type:** Project Constitution Layer (V0-P1)
> **Status:** Authoritative
> **Owner:** Founder
> **Update procedure:** Governance-class change (ADR); scope changes require a recorded, reviewed decision (NR-5/NR-13).
> **Derived from:** [`PROJECT_VISION.md`](./PROJECT_VISION.md), [`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md)
> **Canonical terminology:** [`GLOSSARY.md`](./GLOSSARY.md)

This document defines the **boundaries** of NeuroVision AI. Scope discipline is a
clinical-safety property: a platform that tries to do everything does nothing
trustworthily. **Every scope decision below includes its rationale.** Scope is
organized as **IN SCOPE**, **OUT OF SCOPE**, **FUTURE SCOPE**, and **REJECTED
SCOPE**.

A change of scope is a **governance event**. Nothing moves between these
categories casually; movement requires a recorded, reviewed decision and a
re-check of the vision and objectives.

---

## 1. IN SCOPE

Capabilities the platform is committed to building (across V0 → V4). Each is
within the clinical mission of critical-care EEG interpretation.

| # | In-scope capability | Rationale |
|---|---------------------|-----------|
| **I1** | **ICU seizure detection** from continuous EEG (cEEG). | The core clinical need: non-convulsive seizures are common, dangerous, and invisible without EEG. |
| **I2** | **IIC (Ictal-Interictal Continuum) monitoring** — detection/characterization of **LPD, GPD, LRDA, GRDA** (and "Other"). | The IIC is where clinical ambiguity and risk concentrate; it is precisely where decision support helps most. |
| **I3** | **Uncertainty quantification** (e.g. Conformal Prediction) on clinical outputs, including abstain/escalate. | In critical care, honest uncertainty is safer than a confident guess. A primary objective (P2). |
| **I4** | **Deterministic, versioned preprocessing** of EEG (filtering, montage handling, windowing, normalization). | Reproducibility and auditability require deterministic, documented signal processing. |
| **I5** | **Patient-disjoint (LOSO-style) evaluation** as the only valid evaluation regime. | The single most important defense against the EEG-AI translation failure (data leakage). |
| **I6** | **Offline (retrospective) analysis** of completed recordings (V1–V2). | Establishes rigor before assuming the harder real-time problem. |
| **I7** | **Near real-time monitoring** of ongoing recordings (V3+). | The clinical value of detection is time-sensitive. |
| **I8** | **Clinical review workflow** integration: prioritized, reviewable, traceable outputs (V2+). | A model only helps if a clinician can actually use it in their workflow. |
| **I9** | **Governance & Context Control (GCC)**: enforced boundaries, decision records, audit trails. | A clinical platform must be able to prove why it behaves as it does. |
| **I10** | **Observability/monitoring** of model and system behavior in deployment. | Performance degradation under domain shift must be detectable, not silent. |
| **I11** | **Hospital-oriented deployment** packaging and operation (V4). | The strategic destination is a Hospital-Ready Foundation. |
| **I12** | Adherence to **ACNS** standardized critical-care EEG terminology. | Clinical interpretability requires speaking the clinicians' standardized language. |

---

## 2. OUT OF SCOPE

Capabilities deliberately excluded. Being adjacent to EEG or AI is **not**
sufficient reason for inclusion.

| # | Out-of-scope capability | Rationale for exclusion |
|---|-------------------------|-------------------------|
| **O1** | **Seizure prediction / forecasting** (predicting seizures before they occur). | A fundamentally different, unsolved problem with different validation and risk; mixing it in would dilute the detection mission and invite overclaiming. |
| **O2** | **Brain-Computer Interface (BCI)** / neural control. | Different signal goals, hardware, and users; orthogonal to critical-care interpretation. |
| **O3** | **Neurogaming / entertainment**. | Non-clinical; contrary to the platform's purpose and quality bar. |
| **O4** | **Consumer / wellness EEG products** (meditation, focus, sleep wearables). | Consumer-grade goals and signals conflict with clinical rigor and safety constraints. |
| **O5** | **Autonomous clinical decision-making** (acting without a clinician). | NeuroVision AI is decision-*support*; the clinician is always the decision-maker (Vision §11). |
| **O6** | **Diagnosis of epilepsy syndromes / etiologies**. | A clinical-judgment task beyond seizure/IIC detection; outside the platform's evidentiary basis. |
| **O7** | **Treatment recommendation / dosing**. | Therapeutic decisions are clinician responsibilities and carry liability/regulatory burdens outside this platform. |
| **O8** | **Non-EEG modalities as primary inputs** (imaging, labs, genomics). | The platform is an EEG-AI platform; multimodal fusion is not its mission (see Future Scope for narrow exceptions). |
| **O9** | **General-purpose ML/AutoML framework**. | The platform is a focused clinical system, not a tooling product. |
| **O10** | **Non-patient-disjoint "leaderboard" optimization**. | Forbidden by principle; chasing leaked-split metrics is an anti-objective. |

---

## 3. FUTURE SCOPE

Capabilities **not** being built now, but plausibly aligned with the mission and
permitted to be reconsidered in a later version through a governance decision.
Listing here is **not** a commitment — it is a pre-authorized place to revisit.

| # | Future capability | Earliest reasonable version | Rationale / condition |
|---|-------------------|------------------------------|------------------------|
| **F1** | Additional critical-care EEG patterns beyond the core IIC set (e.g. burst-suppression characterization). | V2+ | Clinically relevant; deferred until the core IIC capability is rigorous. |
| **F2** | **Sleep staging** or other non-ICU EEG contexts. | Post-V4 | Adjacent and valuable, but outside the current critical-care focus; must not dilute V0–V4. |
| **F3** | Narrow **multimodal context** (e.g. EEG + basic vitals) strictly to improve ICU detection. | V3+ | Allowed only if it serves the in-scope detection mission and preserves validation integrity. |
| **F4** | **Site-adaptation / domain-adaptation** tooling for new hospitals. | V4 | Directly serves deployment readiness and domain-shift robustness. |
| **F5** | **Federated or privacy-preserving training** across sites. | Post-V4 | Plausible for multi-hospital scaling; large governance/security implications. |
| **F6** | **Regulatory submission artifacts** (e.g. documentation packages for clearance). | V4+ | The governance/audit foundation is built earlier precisely to make this feasible later. |

Promotion of a future-scope item to in-scope requires: (a) a recorded governance
decision, (b) confirmation it does not violate any architectural principle, and
(c) confirmation it fits within an existing or planned version's exit criteria.

---

## 4. REJECTED SCOPE

Capabilities that have been **considered and explicitly refused.** Unlike "Future
Scope," these are not expected to be revisited; re-opening one requires
overturning a recorded decision and amending the vision.

| # | Rejected capability | Reason for rejection |
|---|---------------------|----------------------|
| **R1** | **Replacing the neurophysiologist** / fully autonomous interpretation. | Conflicts with the foundational philosophy that the clinician is the decision-maker; unsafe and out of mission. |
| **R2** | **Direct-to-consumer EEG device or app**. | Contradicts the clinical-grade quality bar and target users. |
| **R3** | **Architecture-on-the-fly / rewrite-per-idea development style**. | Directly violates the no-rewrite principle; destroys accumulated validation and trust. |
| **R4** | **"Ship fast, validate later"** development. | Inverts the survivability-over-speed philosophy; the cause of EEG-AI translation failure. |
| **R5** | **Closed/undocumented "black-box" pipeline** with no reproducibility or audit trail. | Violates reproducibility, auditability, and governance principles; un-deployable in a hospital. |
| **R6** | **Marketing accuracy claims based on leaked splits**. | Scientific and clinical misconduct; explicitly an anti-objective. |
| **R7** | **Vendor/EEG-hardware lock-in as an architectural assumption**. | Montage/hardware heterogeneity is a first-class concern; baking in one vendor undermines robustness and portability. |

---

## 5. Scope Boundary Diagram

```
                         ┌───────────────────────────────────────┐
                         │              IN SCOPE                   │
                         │  ICU seizure detection · IIC monitoring │
                         │  (LPD/GPD/LRDA/GRDA) · UQ · LOSO ·       │
                         │  deterministic preprocessing · offline  │
                         │  + near-real-time · clinical workflow · │
                         │  GCC governance · monitoring · hospital │
                         │  deployment · ACNS terminology          │
                         └───────────────────────────────────────┘
        FUTURE SCOPE  ↑ (governance-gated promotion)        ↓ never
   burst-suppression · sleep staging ·            OUT OF SCOPE / REJECTED
   narrow multimodal · site adaptation ·     seizure prediction · BCI ·
   federated training · regulatory pkg       neurogaming · consumer EEG ·
                                             autonomous decisions · dx ·
                                             treatment · leaked-split claims
```

---

## 6. How To Use This Document

- **Before starting any work**, confirm it is IN SCOPE for the current version.
- If it is **OUT OF SCOPE or REJECTED**, do not build it; if you believe it
  should be reconsidered, raise a governance decision rather than implementing it.
- If it is **FUTURE SCOPE**, do not build it now; record interest as a governance
  note for the appropriate version.
- **Scope creep is a failure metric** (see [`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md) §6).

---

## 7. Relationship To Other Constitution Documents

- Upstream: [`PROJECT_VISION.md`](./PROJECT_VISION.md), [`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md).
- Interacts with: [`VERSION_EVOLUTION_MODEL.md`](./VERSION_EVOLUTION_MODEL.md)
  (which version owns each in-scope capability) and
  [`NON_NEGOTIABLE_RULES.md`](./NON_NEGOTIABLE_RULES.md) (the "stay in scope" law).

Scope changes are governance events and require a recorded, reviewed decision.
