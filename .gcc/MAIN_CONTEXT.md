# MAIN CONTEXT — Master Memory

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (live)**
> **Status:** Living — the single fastest path to understanding the whole project.
> **Owner:** Founder · **Kept current by:** the active contributor (human or AI)
> **Update procedure:** Update whenever project identity, architecture, version position, priorities, or top risks change. Every update is logged ([`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md)).
> **Last updated:** V0-P4 (Governance + AI OS foundation established)

**Purpose:** allow a *completely new AI agent* (or the founder after months away)
to understand the entire project **in minutes** and act safely. If you read only
one file, read this — then follow the reading order in §15.

> **One-sentence project:** NeuroVision AI is a production-oriented, governed,
> uncertainty-aware EEG-AI platform that helps critical-care clinicians detect and
> characterize seizures and the ictal-interictal continuum, built to mature
> safely from a repository foundation (V0) to a hospital-ready foundation (V4).

---

## 1. Project Identity
- **Name:** NeuroVision AI (`neurovision_ai`).
- **Domain:** Critical-care (ICU) EEG-AI; clinical **decision-support** (never autonomous).
- **What it is NOT:** an EEG classifier, a notebook, a prototype, a Kaggle entry.
- **Primary users:** critical-care neurologists/epileptologists, intensivists, EEG
  technologists, clinical researchers, platform engineers, hospital IT (V4), and
  **future AI agents**.

## 2. Vision (why it exists)
EEG-AI rarely reaches patients due to predictable failures: leaked
(non-patient-disjoint) validation, overconfident predictions, irreproducibility,
undocumented architecture, and rewrites. NeuroVision AI closes this gap **by
construction**. Full text: [`../docs/PROJECT_VISION.md`](../docs/PROJECT_VISION.md).

## 3. Mission
Build a trustworthy, reproducible, uncertainty-aware EEG-AI platform that helps
clinicians **in time to matter**, and that can be **maintained, governed, and
trusted for a decade**. Details: [`../docs/PROJECT_OBJECTIVES.md`](../docs/PROJECT_OBJECTIVES.md).

## 4. Architecture Summary
**Seven layers** (top depends on lower; cross-cutting layers govern/record):
- **Presentation** (`frontend/`) → **Application** (`backend/`) → **ML** (`ml/`) →
  **DSP** (`preprocessing/`), with supporting **datasets/** and **evaluation/**.
- **Infrastructure** (`deployment/`, `monitoring/`) wraps the stack one-way.
- **Governance** (`.gcc/`) and **Context** (`docs/`) are cross-cutting, imported by
  nobody.

**Dependency direction (acyclic / one-way):**
```
frontend ─(API only)─► backend ─► { ml, evaluation, datasets, preprocessing }
                                   ml ─► { preprocessing, datasets }
                                   datasets ─► preprocessing
                                   evaluation ─► { ml, datasets, preprocessing }
                                   preprocessing ─► (nobody)
```
Canonical: [`../docs/architecture/`](../docs/architecture/) (layered, dependency
graph, module boundaries, import rules, system context).

## 5. Version Summary (the road)
| V | Name | Mission |
|---|------|---------|
| **V0** | Repository Foundation | Build the permanent foundation (constitution, architecture, governance, AI OS). |
| **V1** | Offline EEG Platform | Rigorous, reproducible, patient-disjoint, uncertainty-aware offline detection. |
| **V2** | Clinical Workflow Platform | Reviewable, prioritized, traceable clinician workflow. |
| **V3** | Near Real-Time Platform | Near-live ingestion + incremental inference, integrity preserved. |
| **V4** | Hospital-Ready Foundation | Deployable, governable, auditable, reliable (maturity state, not a clearance claim). |
Canonical: [`../docs/VERSION_EVOLUTION_MODEL.md`](../docs/VERSION_EVOLUTION_MODEL.md).

## 6. Current Position
- **Version:** V0 (Repository Foundation).
- **Phases complete:** V0-P1 (Constitution), V0-P2 (Architecture), V0-P3
  (Governance framework), **V0-P4 (AI Operating System foundation — current).**
- **Code:** none yet (correct for V0).
- Live detail: [`CURRENT_STATE.md`](./CURRENT_STATE.md).

## 7. Target Position
- **Immediate:** complete V0 (satisfy V0 exit criteria) → begin **V1**.
- **Strategic:** reach **V4** by extending — never rewriting — the V0 architecture.
- Live detail: [`NEXT_STATE.md`](./NEXT_STATE.md), [`VERSION_STATUS.md`](./VERSION_STATUS.md).

## 8. Critical Constraints (never violated)
- **Patient-disjoint validation only** (AP-2 / NR-3).
- **Calibrated uncertainty on every clinical output**; abstain/escalate allowed (AP-4 / NR-4).
- **Deterministic, versioned preprocessing** (AP-3 / NR-9).
- **Reproducible results** (AP-6 / NR-10).
- **Traceable clinical outputs** (AP-5 / NR-11).
- **No forbidden imports / acyclic graph** (AP-7 / NR-8).
- **No architecture rewrites** (AP-1 / NR-6).
- **Recorded decisions for consequential change** (AP-9 / NR-5).
- **Stay in scope; never skip a version** (NR-13 / NR-12).
- **All code reviewed, incl. AI-generated** (NR-7).
- Full law: [`../docs/NON_NEGOTIABLE_RULES.md`](../docs/NON_NEGOTIABLE_RULES.md);
  principles: [`../docs/ARCHITECTURAL_PRINCIPLES.md`](../docs/ARCHITECTURAL_PRINCIPLES.md).

## 9. Critical Invariants (cross-version, never weaken once introduced)
Patient-disjoint validation · deterministic preprocessing · calibrated uncertainty
· reproducibility · enforced boundaries · recorded decisions · no rewrite · in
scope. (See [`../docs/VERSION_EVOLUTION_MODEL.md`](../docs/VERSION_EVOLUTION_MODEL.md) §6.)

## 10. Current Priorities
1. Finalize V0 (governance + OS) and verify **V0 exit criteria**.
2. Keep the OS state files current (this directory).
3. Prepare V1 entry: preprocessing determinism + patient-disjoint evaluation design.
(Live: [`NEXT_STATE.md`](./NEXT_STATE.md), [`ROADMAP_STATUS.md`](./ROADMAP_STATUS.md).)

## 11. Future Priorities
V1 offline rigor → V2 clinical workflow → V3 near-real-time → V4 hospital-ready,
each gated by the prior version's exit criteria (NR-12).

## 12. Known Risks (top, live in [`ACTIVE_RISKS.md`](./ACTIVE_RISKS.md))
- **CTX:** context loss across dormancy/agent turnover → mitigated by this OS + Lore.
- **AI:** context drift, hallucinated APIs, scope expansion → AI Governance §5.
- **ARCH:** boundary/cycle drift → GCC checks + boundary tests.
- **CLIN (future):** overconfident outputs → uncertainty + abstain (AP-4).

## 13. Known Assumptions (live in [`ACTIVE_ASSUMPTIONS.md`](./ACTIVE_ASSUMPTIONS.md))
- Source research corpus is **not required** to operate — the repo is
  self-explanatory by design (Lore Protocol).
- ACNS-aligned IIC classes (SZ, LPD, GPD, LRDA, GRDA, Other) are the target label
  space (to be confirmed with data in V1).

## 14. AI Entry Point
**If you are an AI agent starting work:**
1. Read this file (you're here).
2. Run [`CONTEXT_RECOVERY_PROTOCOL.md`](./CONTEXT_RECOVERY_PROTOCOL.md) and
   [`AI_ONBOARDING_PROTOCOL.md`](./AI_ONBOARDING_PROTOCOL.md).
3. Read [`CURRENT_STATE.md`](./CURRENT_STATE.md) + [`NEXT_STATE.md`](./NEXT_STATE.md).
4. Before changing anything, obey [`../docs/governance/AI_Governance.md`](../docs/governance/AI_Governance.md)
   (context recovery, scope/version checks, boundaries, self-validation, traceability).
5. **Never self-approve** (NR-7); record decisions (NR-5); leave Lore (NR-14).

## 15. Reading Order (deterministic)
1. `.gcc/MAIN_CONTEXT.md` (this file)
2. `.gcc/CONTEXT_RECOVERY_PROTOCOL.md` → `.gcc/AI_ONBOARDING_PROTOCOL.md`
3. `.gcc/CURRENT_STATE.md` → `.gcc/NEXT_STATE.md` → `.gcc/VERSION_STATUS.md`
4. Constitution: `docs/PROJECT_VISION.md` → `OBJECTIVES` → `SCOPE` →
   `VERSION_EVOLUTION_MODEL` → `ARCHITECTURAL_PRINCIPLES` → `NON_NEGOTIABLE_RULES`
   → `GLOSSARY`
5. Architecture: `docs/architecture/` (layered → system context → boundaries →
   dependency graph → import rules)
6. Governance: `docs/governance/` (start at its `README.md`)
7. Registers: `.gcc/DECISION_REGISTRY.md`, `ACTIVE_RISKS.md`,
   `ACTIVE_ASSUMPTIONS.md`, `DEPENDENCY_REGISTRY.md`
8. `.gcc/KNOWLEDGE_GRAPH.md` (to see how it all connects)

---
*This is the master memory. It summarizes; the linked canonical documents govern.
Keep it short, current, and honest — it is the project's first impression on every
future contributor.*
