# CODE REVIEW CHECKLISTS

> **Document type:** Quality Assurance Foundation (V0-P5) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Quality Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Extends:** the general/AI/architecture/release checklists in [`../../.gcc/CHECKLISTS/`](../../.gcc/CHECKLISTS/); governed by [`../governance/Review_Governance.md`](../governance/Review_Governance.md)

Per-domain, **actionable** review checklists. Every item is a concrete,
verifiable check — **no vague criteria** ("looks good", "seems fine" are not
items). A reviewer applies: **the general checklist** first
([`../../.gcc/CHECKLISTS/review_checklist.md`](../../.gcc/CHECKLISTS/review_checklist.md)),
then the **domain checklist(s)** below for every domain the change touches, then
the **AI checklist** ([`../../.gcc/CHECKLISTS/ai_review_checklist.md`](../../.gcc/CHECKLISTS/ai_review_checklist.md))
if AI-generated. A failed mandatory item = **request changes / block** (NR-7;
producing agent never self-approves).

> Most domain checklists are **V1+** (no code exists in V0). They are authoritative
> now so that the *first* line of code in each domain is reviewed correctly.

---

## 0. How to use
1. Classify the change (Documentation/Minor/Major/Architecture/Governance/Emergency)
   and risk tier (A0–A3/AE) — [`../governance/Change_Management.md`](../governance/Change_Management.md).
2. Run **General review** (always).
3. Run each **domain checklist** that applies (a change may touch several).
4. Run **AI-generated** checklist if AI authored any part.
5. Confirm the relevant **quality gates** (G1–G8) pass.

---

## 1. Architecture Changes (A3)
- [ ] Genuinely architecture (Architecture_Governance §2)? If unsure, treated as such.
- [ ] Approved **ADR** + RFC trail exist (NR-5).
- [ ] Dependency graph remains **acyclic**; no forbidden edge added (NR-8).
- [ ] **Extends, not rewrites** (NR-6).
- [ ] No cross-version invariant weakened.
- [ ] **Dependency Registry** updated for any edge/dependency change.
- [ ] All affected architecture docs + module READMEs updated in the same change set.
- [ ] Concrete **rollback** recorded before approval.
- [ ] In scope (NR-13); version-gate valid (NR-12).
- [ ] Architecture Gate (G1) green; Founder architecture review done.

## 2. Backend Changes (Application layer; V2+)
- [ ] Imports only `ml`/`evaluation`/`datasets`/`preprocessing` (never `frontend`; no infra code-import) (NR-8).
- [ ] **Uncertainty preserved** end-to-end — not dropped/flattened (NR-4).
- [ ] **Provenance/audit trail** maintained for every clinical output (NR-11/AP-5).
- [ ] API contract change (if any) has an ADR + updated contract tests **before** merge.
- [ ] No domain logic reimplemented that belongs in `ml`/`preprocessing`/`evaluation`.
- [ ] Errors handled without leaking internals; no PII in logs (use placeholders).
- [ ] Contract + integration tests green; no V1 regression.

## 3. Frontend Changes (Presentation layer; V2+)
- [ ] Imports **no domain module**; reaches backend **via API only** (NR-8) — the canonical forbidden-import rule.
- [ ] **Uncertainty rendered faithfully** — never hidden, flattened, or implied as certainty (NR-4).
- [ ] Provenance/"why" reference surfaced so a result is traceable (NR-11).
- [ ] No DSP/ML/data/eval logic embedded in the UI.
- [ ] Accessibility + clear "uncertain / needs review" states present.
- [ ] Contract tests against the API green; no broken end-to-end traceability.

## 4. ML Changes (ML layer; V1+)
- [ ] Imports only `preprocessing`/`datasets`; **never** `evaluation` (no cycle), `backend`, `frontend` (NR-8).
- [ ] Output carries **calibrated uncertainty** + supports **abstain/escalate** (NR-4); no bare-label clinical output.
- [ ] Output carries **provenance** (model version + preprocessing version) (AP-5/NR-11).
- [ ] Any metric reported is **patient-disjoint** (NR-3); **no** in-distribution-only claim presented as general (NR-15).
- [ ] Training/inference **reproducible** from pinned inputs/code (NR-10); seeds pinned.
- [ ] Model/method choice has an **ADR**; new dependency recorded.
- [ ] ML + clinical-validation tests green ([`TEST_STRATEGY.md`](./TEST_STRATEGY.md) §2.7–2.8).

## 5. DSP / Preprocessing Changes (DSP leaf; V1+)
- [ ] Imports **nobody internal** (third-party numerics only) (NR-8).
- [ ] **Deterministic + versioned**: same input + version ⇒ same output; determinism test included (NR-9).
- [ ] No unseeded randomness, wall-clock, or ordering-dependent global state on the production path.
- [ ] Emits the **preprocessing version** as provenance.
- [ ] Does not load datasets / run models / serve.
- [ ] Determinism + unit tests green.

## 6. Deployment / Monitoring Changes (Infrastructure; V3+)
- [ ] **No domain-module code imports** into infra; domain emits telemetry via shared contracts (NR-8).
- [ ] Not imported **by** any domain module.
- [ ] Environments **pinned/reproducible** (AP-6); no **vendor/hardware lock-in** baked in (Scope R7).
- [ ] (Monitoring) **drift detectors tested** on synthetic shift; alert thresholds **recorded** (AP-10/NR-15).
- [ ] (Deployment) **tested rollback** to last known-good exists; observability live before release (V3+).

## 7. Governance Changes (A3; docs/governance, docs/quality, docs/context, .gcc policy)
- [ ] Change is genuinely governance-class; approved **ADR** exists (NR-5).
- [ ] No contradiction introduced with the constitution or a higher tier (consistency).
- [ ] **All dependent documents reconciled** in the same change set (propagate consistency).
- [ ] New terms added to the **Glossary** (NR-14).
- [ ] Founder approval recorded; changelog entry present.

## 8. AI-Generated Changes (any domain)
- [ ] **AI-TRACE block** present and matches the diff ([`../governance/AI_Governance.md`](../governance/AI_Governance.md) §9).
- [ ] **Every referenced symbol resolves** — no hallucinated APIs.
- [ ] No silent **scope** (NR-13) or **dependency** (NR-2) expansion.
- [ ] Boundary/invariant checks cross-checked against GCC result.
- [ ] AI risk score computed; review depth matches ([`AI_OUTPUT_VALIDATION.md`](./AI_OUTPUT_VALIDATION.md) §5).
- [ ] Reviewed by a **human**; producing agent did **not** self-approve (NR-7).

## 9. Documentation Changes
- [ ] Six doc scans pass (orphan/conflict/staleness/term/link/ownership) — [`DOCUMENTATION_VALIDATION.md`](./DOCUMENTATION_VALIDATION.md) §2.
- [ ] No conflict with a higher tier; single canonical source preserved.
- [ ] New terms in the **Glossary** (NR-14); Owner + Update procedure present.
- [ ] If Tier 0–2 **meaning** changed → an **ADR** exists.
- [ ] Superseded docs marked + linked (no silent deletion); changelog entry present.

---

## 10. Relationship To Other Documents
- General/AI/architecture/release/version-gate checklists: [`../../.gcc/CHECKLISTS/`](../../.gcc/CHECKLISTS/)
- Review policy: [`../governance/Review_Governance.md`](../governance/Review_Governance.md) · Gates: [`QUALITY_GATES.md`](./QUALITY_GATES.md)

Changes to this document are governance-class and require an ADR.
