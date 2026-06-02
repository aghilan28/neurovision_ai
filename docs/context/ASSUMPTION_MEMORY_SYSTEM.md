# ASSUMPTION MEMORY SYSTEM

> **Document type:** Context Preservation System (V0-P6) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Context Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Live artifact:** [`../../.gcc/ACTIVE_ASSUMPTIONS.md`](../../.gcc/ACTIVE_ASSUMPTIONS.md) · **Template:** [`../../.gcc/TEMPLATES/ASSUMPTION_TEMPLATE.md`](../../.gcc/TEMPLATES/ASSUMPTION_TEMPLATE.md)

An **assumption** is something the project currently treats as true **without
verification.** Unrecorded assumptions are the quietest way context rots: they
silently harden into "facts," and decisions built on them become unexplainable and
unsafe to change. This system makes every consequential assumption **explicit,
evidenced, and lifecycle-managed** — and **prevents assumption rot.**

> **Premise (NR-14):** an assumption that is acted on but not recorded is a hidden
> dependency on luck. Record it, give it a verification plan, and resolve it.

---

## 1. What Is Tracked (per assumption)

| Field | Meaning |
|-------|---------|
| **ID** | `ASM-NNNN` (monotonic). |
| **Assumption** | The thing treated as true without proof. |
| **Evidence** | What (if anything) currently supports it. |
| **Confidence** | Low / Medium / High. |
| **Verification Method** | *How* it will be confirmed/refuted (experiment, evaluation, source check). |
| **Verification Date** | *When* verification is due/was done. |
| **Outcome** | Result of verification (confirmed / refuted / partial). |
| **Status** | Open / Verified / Refuted / Retired. |
| **Links** | ADRs that rest on it; related risks; modules. |

(Live register fields per [`../../.gcc/ACTIVE_ASSUMPTIONS.md`](../../.gcc/ACTIVE_ASSUMPTIONS.md);
this system adds **Verification Method/Date** and **Outcome** explicitly.)

## 2. Assumption Lifecycle

```
 IDENTIFY ─► RECORD (ACTIVE_ASSUMPTIONS, with verification plan) ─► (Verification Date) ─► VERIFY
     │                                                                                      │
     │                                                          ┌───────────────┬───────────┤
     │                                                          ▼               ▼           ▼
     └─ (no plan = defect) ──────────────────────────────── VERIFIED        REFUTED      RETIRED
                                                            (becomes fact/  (triggers     (no longer
                                                             documented)     ADR + risk)   relevant)
```

- **Identify & record:** any time a decision/design rests on something unproven,
  record it **with a verification plan** (method + date). *An assumption with no
  plan is a defect* (the core anti-rot rule).
- **Verify (at the Verification Date):** apply the method; record the **Outcome**.
- **Verified:** it becomes established knowledge — promote into documentation/the
  relevant doc; the assumption is marked `Verified` (kept, linked).
- **Refuted:** **trigger an ADR** to revisit every decision that rested on it
  ([`DECISION_MEMORY_SYSTEM.md`](./DECISION_MEMORY_SYSTEM.md) §3); open/raise a risk
  for anything now exposed; mark `Refuted` (kept, linked).
- **Retired:** the assumption no longer matters (its context dissolved); mark
  `Retired` with the reason.
All transitions are **append-only** — assumptions are never deleted
([`MEMORY_RETENTION_POLICY.md`](./MEMORY_RETENTION_POLICY.md)).

## 3. Preventing Assumption Rot (the central job)
Assumption rot = an unverified assumption silently treated as fact for so long that
no one remembers it was ever an assumption. Defenses:
1. **Mandatory verification plan** — no assumption is recorded without *method +
   date*; a missing plan is a defect (metric **M12**, [`../quality/QUALITY_METRICS.md`](../quality/QUALITY_METRICS.md)).
2. **Overdue verification is a finding** — the context audit flags assumptions past
   their Verification Date ([`CONTEXT_AUDIT_SYSTEM.md`](./CONTEXT_AUDIT_SYSTEM.md)).
3. **Link to decisions** — every ADR that rests on an assumption links to its
   `ASM-id`; if the assumption is refuted, the dependent decisions are revisited.
4. **High-impact + low-confidence ⇒ also a risk** — mirror it in
   [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md) so it gets risk-cadence review.
5. **Post-dormancy re-validation** — open assumptions are re-reviewed on resuming
   work ([`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md) §5).

## 4. Examples (seeded; live in ACTIVE_ASSUMPTIONS)
- **ASM-0001** repository is self-sufficient without the research corpus — verify by a
  cold onboarding test.
- **ASM-0002** target label space is the ACNS-aligned IIC set — verify at V1 data onboarding.
- **ASM-0003** Conformal Prediction is a suitable reference UQ technique — verify by V1 coverage evaluation.
- **ASM-0004** Mamba-class models are viable candidates — verify by V1 patient-disjoint benchmark; *no model adopted without this*.
(Full list + status: [`../../.gcc/ACTIVE_ASSUMPTIONS.md`](../../.gcc/ACTIVE_ASSUMPTIONS.md).)

## 5. Recovery & Audit
- **Recovery (step 12):** an agent reads open assumptions before acting in their
  area — so it does not unknowingly build on an unverified premise.
- **Audit (G7):** every assumption has a verification plan; none overdue without
  action; refuted assumptions triggered ADRs; high-impact ones are mirrored as risks.

## 6. Relationship To Other Documents
- Live/template: [`../../.gcc/ACTIVE_ASSUMPTIONS.md`](../../.gcc/ACTIVE_ASSUMPTIONS.md), [`../../.gcc/TEMPLATES/ASSUMPTION_TEMPLATE.md`](../../.gcc/TEMPLATES/ASSUMPTION_TEMPLATE.md)
- Decisions/risks: [`DECISION_MEMORY_SYSTEM.md`](./DECISION_MEMORY_SYSTEM.md), [`RISK_MEMORY_SYSTEM.md`](./RISK_MEMORY_SYSTEM.md)
- Audit/retention/metric: [`CONTEXT_AUDIT_SYSTEM.md`](./CONTEXT_AUDIT_SYSTEM.md), [`MEMORY_RETENTION_POLICY.md`](./MEMORY_RETENTION_POLICY.md), [`../quality/QUALITY_METRICS.md`](../quality/QUALITY_METRICS.md) (M12)

Changes to this document are governance-class and require an ADR.
