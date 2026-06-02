# POSTMORTEM FRAMEWORK

> **Document type:** Context Preservation System (V0-P6) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Context Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Integrates:** [`../quality/FAILURE_HANDLING.md`](../quality/FAILURE_HANDLING.md), [`../governance/Release_Governance.md`](../governance/Release_Governance.md) §8, [`../../.gcc/LORE_PROTOCOL.md`](../../.gcc/LORE_PROTOCOL.md) §7
> **Template:** [`../../.gcc/TEMPLATES/POSTMORTEM_TEMPLATE.md`](../../.gcc/TEMPLATES/POSTMORTEM_TEMPLATE.md) · **Home:** `.gcc/postmortems/`

A **postmortem** converts an incident or failure into **durable, reusable
knowledge** so it cannot recur silently. This framework defines what triggers a
postmortem, what it must capture, and how its outputs feed prevention, risk, and
lessons. Postmortems are **blameless** (focused on systems, not people) and
**permanent**.

> **Premise:** the value of a failure is the learning extracted from it. A failure
> with no postmortem is a failure paid for twice.

---

## 1. When a Postmortem Is Required
- Any **deployed incident** (V3+): outage, drift breach, safety-relevant error
  (Release_Governance §8) — **mandatory**.
- Any failure that **reached `main`** (architecture/governance/test/doc/context) —
  ([`../quality/FAILURE_HANDLING.md`](../quality/FAILURE_HANDLING.md)).
- Any **realized risk** ([`RISK_MEMORY_SYSTEM.md`](./RISK_MEMORY_SYSTEM.md)).
- Any **failed version gate** or near-loss of context (a knowledge silo discovered).
- Optional (encouraged) for a significant **near-miss** caught before merge — the
  cheapest lesson of all.

## 2. What a Postmortem Captures

(Per the template; every field required.)

| Section | Content |
|---------|---------|
| **Summary** | What happened + impact, one paragraph. |
| **Timeline** | Detection → diagnosis → mitigation → resolution, with times. |
| **Impact** | What/who affected; which invariant/guarantee at risk; clinical-safety relevance. |
| **Root cause(s)** | The real cause(s), via repeated "why" — not just symptoms. |
| **What caught it / what didn't** | The detection that worked, or the **detection gap**. |
| **Recovery** | Corrective actions taken; rollback used? |
| **Lessons learned** | Transferable insight (→ [`LESSONS_LEARNED_SYSTEM.md`](./LESSONS_LEARNED_SYSTEM.md)). |
| **Future prevention** | The new/strengthened check, test, rule, or doc so it **cannot recur silently**. |
| **Follow-ups / links** | New RISK/ADR/tests/change records created. |

## 3. Postmortem Workflow

```
 INCIDENT/FAILURE ─► CONTAIN+RECOVER (FAILURE_HANDLING) ─► WRITE POSTMORTEM (blameless) ─►
 EXTRACT: prevention + risk update + lesson ─► IMPLEMENT prevention ─► LINK + INDEX ─► CLOSE
```

1. **Contain & recover** first ([`../quality/FAILURE_HANDLING.md`](../quality/FAILURE_HANDLING.md) §1).
2. **Write** the postmortem (`.gcc/postmortems/PM-NNNN-title.md`) from the template;
   blameless; durable.
3. **Extract outputs:** (a) a **prevention** (new guarding check/test/rule);
   (b) a **risk update** — close, or accept-with-mitigation
   ([`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md)); (c) a **lesson**
   ([`LESSONS_LEARNED_SYSTEM.md`](./LESSONS_LEARNED_SYSTEM.md)); (d) an **ADR** if a
   decision changes (NR-5).
4. **Implement** the prevention (it is part of closing the incident).
5. **Link & index:** changelog entry; cross-link postmortem ↔ risk ↔ lesson ↔ ADR.
6. **Close:** an incident is **not closed until its prevention exists** (Failure
   Handling §1) — no prevention, not closed.

## 4. Blameless Principle
Postmortems analyze **systems and processes**, never individuals (human or AI).
The question is always *"what allowed this, and how do we make it impossible/loud
next time?"* — because the goal is a stronger repository, and blame suppresses the
honest reporting that prevention depends on.

## 5. Postmortems and AI
- An AI failure (hallucination, drift, scope creep that reached `main`) gets a
  postmortem that updates the **AI risk model / prompt standards / a guarding check**
  ([`../quality/AI_OUTPUT_VALIDATION.md`](../quality/AI_OUTPUT_VALIDATION.md)).
- AI agents may **draft** postmortems (with full context recovery), but a human
  confirms root cause and approves the prevention (NR-7).

## 6. Retention
Postmortems are **permanent** ([`MEMORY_RETENTION_POLICY.md`](./MEMORY_RETENTION_POLICY.md)):
never deleted, always linked from the risk/lesson/ADR they relate to, and read
during context recovery (so the same failure isn't re-learned).

## 7. Recovery & Audit
- **Recovery:** before working in an area with prior incidents, an agent reads the
  relevant postmortems (reachable via the knowledge model).
- **Audit (G7):** every realized risk/`main`-reaching failure has a postmortem;
  every postmortem has an implemented prevention; postmortems are linked + indexed.

## 8. Relationship To Other Documents
- Failure framework: [`../quality/FAILURE_HANDLING.md`](../quality/FAILURE_HANDLING.md) · Incident policy: [`../governance/Release_Governance.md`](../governance/Release_Governance.md) §8
- Lessons/risks: [`LESSONS_LEARNED_SYSTEM.md`](./LESSONS_LEARNED_SYSTEM.md), [`RISK_MEMORY_SYSTEM.md`](./RISK_MEMORY_SYSTEM.md)
- Template/Lore: [`../../.gcc/TEMPLATES/POSTMORTEM_TEMPLATE.md`](../../.gcc/TEMPLATES/POSTMORTEM_TEMPLATE.md), [`../../.gcc/LORE_PROTOCOL.md`](../../.gcc/LORE_PROTOCOL.md) §7

Changes to this document are governance-class and require an ADR.
