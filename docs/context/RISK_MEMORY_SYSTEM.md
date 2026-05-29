# RISK MEMORY SYSTEM

> **Document type:** Context Preservation System (V0-P6) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Risk Owner / Context Owner roles)
> **Update procedure:** Governance-class change (ADR).
> **Policy authority:** [`../governance/Risk_Governance.md`](../governance/Risk_Governance.md) (categories, scoring, fields). This document **extends** it with the *memory* dimension: the full life of a risk, including resolved/rejected/unknown. On conflict, Risk Governance governs.
> **Live artifact:** [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md)

Risks are context too: *what could go wrong, what we did about it, and what we
learned.* This system preserves risks across their **entire life** — not just
while open — so the project never re-discovers a known hazard or repeats a handled
one. It also names the hardest category: **unknown risks.**

> **Premise:** a closed risk that is forgotten is a risk that recurs. Risk memory
> is **append-only**: risks are resolved or rejected, **never deleted.**

---

## 1. Risk States (the memory dimension)

The live register tracks `Open / Mitigating / Accepted / Closed`
(Risk_Governance §2). Risk *memory* organizes risks across these states **plus**
their origin and disposition:

| State | Meaning | Home |
|-------|---------|------|
| **Active** | Open or Mitigating — being worked. | [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md) |
| **Accepted** | Consciously accepted with rationale (+ debt record if a shortcut, NR-2). | ACTIVE_RISKS (marked) + ADR |
| **Resolved** | Mitigated/closed; the hazard no longer applies. | Risk archive (kept, linked) |
| **Rejected** | Considered and judged not a real risk (with reason). | Risk archive (kept) |
| **Historical** | Any past risk retained for learning (resolved/rejected). | Risk archive |
| **Unknown** | Acknowledged areas of ignorance (§4). | ACTIVE_RISKS "Unknowns" section |

Fields per risk (mandatory): Risk_Governance §2 (ID, category, severity,
probability, impact, detection, mitigation, recovery, owner, review frequency,
status, links). Template: [`../../.gcc/TEMPLATES/RISK_TEMPLATE.md`](../../.gcc/TEMPLATES/RISK_TEMPLATE.md).

## 2. Risk Evolution Process

```
 IDENTIFY ─► RECORD (ACTIVE_RISKS) ─► SCORE ─► MITIGATE ─► (occurs?) ─► RECOVER + POSTMORTEM
     ▲                                   │                                     │
     │                                   ▼                                     ▼
  re-review ◄── MONITOR ◄────────────────┴── RESOLVE / ACCEPT / REJECT ──► ARCHIVE (kept)
```

- New risks are recorded **at identification** (not after they bite).
- Scored via the exposure matrix (Risk_Governance §3); **any risk to a
  cross-version invariant or clinical-safety property is ≥ High**.
- A realized risk triggers **recovery + a postmortem** ([`POSTMORTEM_FRAMEWORK.md`](./POSTMORTEM_FRAMEWORK.md)).
- A risk that motivates a decision links to its **ADR**; an accepted risk records
  rationale (+ debt if applicable).
- On resolution/rejection, the risk is **archived (kept, linked)** with its outcome.

## 3. Risk Learning Process
Every resolved or realized risk yields **transferable knowledge**:
- a **lesson** ([`LESSONS_LEARNED_SYSTEM.md`](./LESSONS_LEARNED_SYSTEM.md)) — "this
  hazard exists in this situation; here's the early signal and the fix";
- a **prevention** — a new check/test/rule so it is detected earlier or cannot recur
  ([`../quality/FAILURE_HANDLING.md`](../quality/FAILURE_HANDLING.md) §5);
- if the hazard is general, an update to **detection/mitigation** guidance for its
  category so future similar risks inherit the learning.
The pre-seeded AI risks (RISK-0002) come directly from the AI failure modes
([`../governance/AI_Governance.md`](../governance/AI_Governance.md) §5) — risk
memory keeps that mapping current.

## 4. Unknown Risks (the hardest category)
We explicitly track **what we don't yet know**, so ignorance is at least *visible*:
- The `ACTIVE_RISKS` register carries an **"Unknown / emerging"** section naming
  areas of acknowledged uncertainty (e.g. "real-world drift behavior at a new site
  is unknown until V3 data exists").
- Each unknown has a **plan to reduce it** (an experiment, a future evaluation, an
  assumption to verify — [`ASSUMPTION_MEMORY_SYSTEM.md`](./ASSUMPTION_MEMORY_SYSTEM.md)).
- When an unknown becomes characterized, it converts to a normal risk (scored) or is
  closed — and that transition is recorded.
> Naming unknowns is a humility discipline: it prevents the illusion that the risk
> register is complete.

## 5. Risk Archival Process
- A resolved/rejected risk is moved to the **risk archive** (a retained section/file
  under `.gcc/`), **marked** with its final state + date + outcome, and **linked**
  from any ADR/postmortem/lesson that references it.
- Archived risks are **never deleted** ([`MEMORY_RETENTION_POLICY.md`](./MEMORY_RETENTION_POLICY.md)).
- Archival keeps the **active** register focused while preserving the **historical**
  record for learning and audit.

## 6. Recovery & Audit
- **Recovery:** during context recovery (step 12), an agent reads active risks +
  scans the archive for prior occurrences before acting in a risky area.
- **Audit (G7 / Context Audit):** every consequential change's introduced risk is
  registered; no undocumented risk (M7/M9); resolved risks are archived not deleted;
  unknowns have reduction plans; realized risks have postmortems.

## 7. Relationship To Other Documents
- Policy: [`../governance/Risk_Governance.md`](../governance/Risk_Governance.md) · Live: [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md)
- Failures/postmortems/lessons: [`../quality/FAILURE_HANDLING.md`](../quality/FAILURE_HANDLING.md), [`POSTMORTEM_FRAMEWORK.md`](./POSTMORTEM_FRAMEWORK.md), [`LESSONS_LEARNED_SYSTEM.md`](./LESSONS_LEARNED_SYSTEM.md)
- Retention/graph: [`MEMORY_RETENTION_POLICY.md`](./MEMORY_RETENTION_POLICY.md), [`REPOSITORY_KNOWLEDGE_MODEL.md`](./REPOSITORY_KNOWLEDGE_MODEL.md)

Changes to this document are governance-class and require an ADR.
