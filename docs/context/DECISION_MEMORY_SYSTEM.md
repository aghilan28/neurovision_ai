# DECISION MEMORY SYSTEM

> **Document type:** Context Preservation System (V0-P6) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Decision Owner / Context Owner roles)
> **Update procedure:** Governance-class change (ADR).
> **Policy authority:** [`../governance/Decision_Governance.md`](../governance/Decision_Governance.md) (the ADR framework). This document **extends** it with the *memory* lifecycle (retirement, supersession, recovery). On conflict, Decision Governance governs.
> **Live artifacts:** [`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md) + `.gcc/decisions/ADR-*.md`

Decisions are the **highest-value context**: they answer *why the project is the
way it is.* This system ensures every consequential decision is **captured,
indexed, linked, kept forever, and recoverable** — so a future agent never has to
guess at, or re-litigate, a settled question.

> **Premise (NR-5/AP-9):** no consequential or architectural change proceeds
> without a recorded, reviewed decision. **Decisions are append-only and never
> deleted** — only superseded.

---

## 1. What Is Tracked (per decision)

The ADR's mandatory fields (Decision_Governance §2) are the memory record; this
system adds two memory-specific fields (**Review Date** already exists; **Retirement
Criteria** is added):

| Field | Source |
|-------|--------|
| Decision · Context · Problem | ADR (Decision_Governance §2) |
| **Alternatives** (options) · **Tradeoffs** | ADR |
| **Rationale** (chosen solution + why) | ADR |
| **Consequences** | ADR |
| **Affected Systems** | ADR |
| **Future Impact** | ADR |
| **Risk** (linked RISK-ids) | ADR |
| **Review Date** | ADR |
| **Retirement Criteria** *(memory extension)* | this system, §3 |
| Status · Links (RFC/change/registry/related ADRs) | ADR + Registry |

Template: [`../../.gcc/TEMPLATES/ADR_TEMPLATE.md`](../../.gcc/TEMPLATES/ADR_TEMPLATE.md).
Index: [`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md).

## 2. Decision Lifecycle

Extends Decision_Governance §3 with explicit **revisit** and **retire** transitions:

```
 PROPOSED ─► ACCEPTED ─► (Review Date or new evidence) ─► REVISIT
     │           │                                          │
     │           │                                  ┌───────┼─────────┐
     │           │                                  ▼       ▼         ▼
     │           │                              REAFFIRM  SUPERSEDE  RETIRE
     │           │                              (unchanged) (ADR-MMMM) (no longer applies)
     └─ REJECTED (recorded, kept) ──────────────────────────────────────────
```

- **Proposed → Accepted:** approved by the required approver (Founder for A2+).
- **Accepted → Revisit:** triggered by the **Review Date** or new evidence
  (a learning, a risk, a changed assumption).
- **Revisit outcomes:**
  - **Reaffirm** — still correct; record the re-review (date) and a new Review Date.
  - **Supersede** — replaced by a newer ADR; mark `Superseded by ADR-MMMM`, link both ways.
  - **Retire** — the decision no longer applies (its context dissolved); mark
    `Retired` with the **Retirement Criteria** that were met.
- **Rejected:** recorded with the reason so the option is not silently re-tried.

**All transitions are append-only.** A superseded/retired ADR is **kept**, marked,
and linked — never deleted (this is what makes "why did we once do X?" answerable).

## 3. Retirement Criteria (new)

Every ADR records, at acceptance, the **conditions under which it would no longer
apply** — so retirement is *evidence-based*, not forgetfulness. Examples:
- "Retire if the module it governs is removed via a future ADR."
- "Retire if the assumption it rests on (ASM-NNNN) is refuted."
- "Stable / constitutional — does not retire (revisit only)" for AP/NR-derived decisions.

A decision with **no** retirement criteria defaults to **"revisit at Review Date;
do not auto-retire."** Constitutional baselines are explicitly **non-retiring**.

## 4. Capture Rules (how decisions enter memory)
1. Consequential decision identified (often via an RFC — [`../governance/RFC_Process.md`](../governance/RFC_Process.md)).
2. Draft ADR from the template; **all mandatory fields** filled (an incomplete ADR is invalid).
3. Approve per Decision_Governance §4 (**Founder** for A2+; **never** AI self-approval — NR-7).
4. Save as `.gcc/decisions/ADR-NNNN-title.md`; add a row to the Registry; **link it
   from the artifacts it governs and to its RFC + changelog entry** (bidirectional).
5. New terms introduced → Glossary (NR-14).

## 5. Traceability (the decision web)
Every decision is linked **both ways** so it is reachable from any direction:
```
 ADR ──► Affected systems (modules/docs)        modules/docs ──► ADR that governs them
 ADR ──► RISK-ids it addresses/accepts           RISK ──► ADR that decided its handling
 ADR ──► ASM-ids it rests on                      ASM  ──► ADR(s) depending on it
 ADR ──► RFC it came from + changelog entry        change ──► ADR it implements
 ADR ──► superseding / superseded ADR
```
This web is what makes context recovery **deterministic**
([`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md) step 11).

## 6. Recovery & Audit
- **Recovery:** an agent answers "why is X this way?" by following links from X to
  its governing ADR(s) — no chat history needed.
- **Audit (Context Integrity Gate G7 + Lore audit):** every consequential change in
  a range has an ADR (M8 = 100%); no orphan ADR (every ADR links to what it
  governs); no decision references a deleted artifact; superseded/retired ADRs are
  marked. Findings → defects/risks ([`CONTEXT_AUDIT_SYSTEM.md`](./CONTEXT_AUDIT_SYSTEM.md)).

## 7. Relationship To Other Documents
- Policy: [`../governance/Decision_Governance.md`](../governance/Decision_Governance.md) · Registry/template: [`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md), [`../../.gcc/TEMPLATES/ADR_TEMPLATE.md`](../../.gcc/TEMPLATES/ADR_TEMPLATE.md)
- Risk/assumption links: [`RISK_MEMORY_SYSTEM.md`](./RISK_MEMORY_SYSTEM.md), [`ASSUMPTION_MEMORY_SYSTEM.md`](./ASSUMPTION_MEMORY_SYSTEM.md)
- Retention: [`MEMORY_RETENTION_POLICY.md`](./MEMORY_RETENTION_POLICY.md) · Graph: [`REPOSITORY_KNOWLEDGE_MODEL.md`](./REPOSITORY_KNOWLEDGE_MODEL.md)

Changes to this document are governance-class and require an ADR.
