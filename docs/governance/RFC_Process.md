# RFC PROCESS

> **Document type:** Governance Layer (V0-P3)
> **Status:** Authoritative
> **Owner:** Founder (Process Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Enforces:** Principles **AP-9, AP-11, AP-12** and Rules **NR-5, NR-13, NR-14**
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

An **RFC (Request For Comments)** is how a non-trivial change is **proposed and
reasoned about** *before* it becomes a decision. The RFC is the deliberation; the
**ADR** ([`Decision_Governance.md`](./Decision_Governance.md)) is the conclusion.
RFCs make thinking visible and reviewable, and they become permanent Lore even
when rejected.

> **When an RFC is required:** any **A2/A3** change (new contract/dependency,
> method choice, architecture, governance, scope promotion, version-gate). A0/A1
> changes do not need an RFC. **When in doubt, write a short RFC.**

---

## 1. RFC Lifecycle

```
 PROPOSAL ─► REVIEW ─► DISCUSSION ─► APPROVAL ─► IMPLEMENTATION ─► VALIDATION ─► CLOSURE
     │           │          │            │              │              │           │
   draft     completeness  options   ADR recorded   per approved   gates pass   registry +
            + scope/gate   weighed   (Founder)      change record               changelog
```

| Stage | What happens | Exit condition |
|-------|--------------|----------------|
| **Proposal** | Author drafts the RFC (template below); states problem, options, impact, risks, rollback. | RFC complete; scope-valid (NR-13); version-gate valid (NR-12). |
| **Review** | Completeness + alignment checked against constitution/architecture. | No missing fields; no obvious rule violation. |
| **Discussion** | Options and tradeoffs are weighed; alternatives challenged. | Converged on a recommendation (or explicit "reject"). |
| **Approval** | Founder decides; the decision is recorded as an **ADR**. | ADR `Accepted` (or RFC `Rejected`, recorded). |
| **Implementation** | The approved change is implemented via the right [`Change_Management.md`](./Change_Management.md) path. | Change merged per Review_Governance. |
| **Validation** | Required tests/validations pass ([`Testing_Governance.md`](./Testing_Governance.md)). | Gates green; no regression. |
| **Closure** | RFC marked `Closed`; linked to its ADR, change record, and changelog entry. | Registry + changelog updated. |

## 2. RFC States
`Draft → Under-Review → Discussion → Accepted / Rejected → Implemented → Closed`
(or `Withdrawn`). States are recorded; **rejected/withdrawn RFCs are kept** (they
preserve why a path was not taken — context-drift defense, NR-14).

## 3. RFC Template (summary)
Full template: [`../../.gcc/TEMPLATES/RFC_TEMPLATE.md`](../../.gcc/TEMPLATES/RFC_TEMPLATE.md).
Mandatory sections:
- **ID** (`RFC-NNNN`), **Title**, **Author**, **Date**, **Status**
- **Summary** — one paragraph.
- **Motivation / Problem** — why now; what breaks if we do nothing.
- **Scope & Version** — affected version/phase; confirmation it is in scope and
  version-gate valid.
- **Proposed Change** — the precise structural/behavioral change.
- **Impact** — modules, contracts, **invariants**, dependency graph, docs affected.
- **Options & Tradeoffs** — ≥2 real alternatives, including "do nothing."
- **Risks** — with categories (links to [`Risk_Governance.md`](./Risk_Governance.md)).
- **Rollback Plan** — how to reverse it.
- **Validation Plan** — what tests/checks prove it correct.
- **Open Questions** — explicit unknowns / assumptions to record.

## 4. RFC Quality Standards
An RFC is acceptable only if it:
- names the **real** alternatives (a one-option RFC is not an RFC);
- makes the **tradeoffs explicit** and honest;
- enumerates **every invariant** it could affect and argues none is weakened;
- includes a **concrete rollback** and **validation** plan;
- is **self-contained** — understandable without external/private context (Lore);
- ends in a **clear recommendation**.

## 5. Roles
- **Author:** anyone (Founder or AI agent). An AI-authored RFC follows
  [`AI_Governance.md`](./AI_Governance.md) (context recovery, traceability).
- **Reviewer/Approver:** **Founder** (A2+); approval is the ADR.
- AI agents may draft, critique, and refine RFCs but never **approve** them (NR-7).

## 6. Relationship To Other Governance Documents
- Decisions: [`Decision_Governance.md`](./Decision_Governance.md) · Change: [`Change_Management.md`](./Change_Management.md)
- Architecture: [`Architecture_Governance.md`](./Architecture_Governance.md) · Risk: [`Risk_Governance.md`](./Risk_Governance.md)
- Registry: [`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md)

Changes to this document are governance-class and require an ADR.
