# LORE PROTOCOL

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (operating protocol)**
> **Status:** Authoritative protocol (the operational form of the constitution's Lore Protocol).
> **Owner:** Founder · **Kept current by:** the active contributor
> **Update procedure:** Changes to the protocol are governance-class (ADR). Routine Lore *capture* happens continuously per this protocol.
> **Enforces:** Principle **AP-9**, Rule **NR-14**; defined in [`../docs/GLOSSARY.md`](../docs/GLOSSARY.md)
> **Last updated:** V0-P4

This is **critical infrastructure.** The Lore Protocol is how NeuroVision AI keeps
its *reasons* — not just its code — so the repository stays **self-explanatory for
a decade**, across founder dormancy and AI-agent turnover. Code rots and is
replaced; **Lore is the durable asset.**

---

## 1. What "Lore" Is
**Lore** is the durable record of *why the project is the way it is*: decisions and
their rationale, constraints, terminology, learnings, postmortems, and the context
behind consequential changes. It is the captured answer to every future *"why?"*.

Lore is **not**: chat transcripts, ephemeral scratch notes, or undocumented
"tribal knowledge" in someone's head. Lore is **written, versioned, and indexed.**

## 2. Why Lore Exists
- **Context drift** is a named failure ([`../docs/PROJECT_VISION.md`](../docs/PROJECT_VISION.md) §10):
  intent and rationale silently erode as people/agents change.
- A solo founder + AI agents cannot rely on memory across months/years.
- Without recorded *why*, settled questions get re-litigated and invariants get
  broken unknowingly.
- Auditability (AP-8) and trust require that any output/decision be explainable
  after the fact.

> **Principle:** *If it isn't written down, it didn't happen* — for anything
> consequential.

## 3. Where Lore Lives (the Lore surface)
| Kind of Lore | Home |
|--------------|------|
| Decisions + rationale + alternatives | ADRs in `.gcc/decisions/` indexed by [`DECISION_REGISTRY.md`](./DECISION_REGISTRY.md) |
| Terminology | [`../docs/GLOSSARY.md`](../docs/GLOSSARY.md) (canonical) |
| Constraints / laws / principles | `docs/` constitution (AP/NR) |
| Open assumptions | [`ACTIVE_ASSUMPTIONS.md`](./ACTIVE_ASSUMPTIONS.md) |
| Risks | [`ACTIVE_RISKS.md`](./ACTIVE_RISKS.md) |
| What changed + why (history) | [`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md) + git history |
| Learnings | learnings log (§6) |
| Postmortems | postmortems (§7), template in `TEMPLATES/` |
| Current/next state | [`CURRENT_STATE.md`](./CURRENT_STATE.md) / [`NEXT_STATE.md`](./NEXT_STATE.md) |

## 4. How Context Is Preserved (the capture loop)
For **every consequential change**:
1. **Decide in the open** — RFC (if A2+) → ADR with rationale + alternatives.
2. **Annotate the commit** (§5) — link the ADR/RFC/risk; explain *why*.
3. **Update state** — `CURRENT_STATE` / `NEXT_STATE` / registries as affected.
4. **Capture learnings** (§6) when something non-obvious is discovered.
5. **Capture postmortems** (§7) after any incident/failure.
6. **Log it** — a changelog entry ties the artifacts together.

AI agents additionally emit the **AI-TRACE block**
([`../docs/governance/AI_Governance.md`](../docs/governance/AI_Governance.md) §9),
which is itself Lore.

## 5. Commit Annotation Standards
Commits are part of the permanent record. Format (template:
[`TEMPLATES/COMMIT_MESSAGE_TEMPLATE.md`](./TEMPLATES/COMMIT_MESSAGE_TEMPLATE.md)):

```
<type>(<scope>): <imperative summary>

Why: <the reason / problem being solved>
What: <what changed, briefly>
Refs: ADR-NNNN, RFC-NNNN, RISK-NNNN, DEP-NNNN (as applicable)
Invariants: <which invariants were checked / preserved>
AI-TRACE: <present for AI-authored changes; see AI_Governance §9>
```
- `type` ∈ {feat, fix, docs, refactor, test, chore, gov, arch}.
- **Every consequential commit explains *why*, not just *what*.**
- A commit that changes architecture/governance **must** reference its ADR (NR-5).

## 6. Learning Capture Standards
When a non-obvious fact is discovered (a method that fails on EEG, a subtle leakage
trap, a tooling gotcha), record a **learning**:
- **What was learned**, **context**, **evidence**, **implication for the project**,
  **links** (ADR/risk/module).
- Store in `.gcc/learnings/` (and reflect in the Glossary/relevant doc if it changes
  shared understanding). A learning that changes a decision triggers an ADR.

## 7. Postmortem Capture Standards
After any incident, failed gate, or significant defect (template:
[`TEMPLATES/POSTMORTEM_TEMPLATE.md`](./TEMPLATES/POSTMORTEM_TEMPLATE.md)):
- **Timeline**, **what happened**, **impact**, **root cause(s)**, **what caught it
  (or didn't)**, **corrective actions**, **prevention** (new check/test/rule),
  **links**.
- Postmortems are **blameless and durable**; their purpose is to prevent
  recurrence. They feed new risks and, where needed, ADRs and new tests.

## 8. Knowledge Capture Standards (general)
- **Single canonical source** per fact (Documentation_Governance §2) — Lore links,
  it does not duplicate.
- **New terms → Glossary** in the same change (NR-14).
- **Append-only history** — superseded Lore is marked and linked, never deleted.
- **Reader-aware** — written so a future agent with no prior context can use it.

## 9. Lore Audit
At each version gate and on resuming after dormancy:
- Every consequential change since the last audit has a *why* (commit + ADR/log).
- No decision exists without rationale; no term used without a Glossary entry.
- Learnings/postmortems are filed and linked.
Findings become defects/risks and are remediated.

## 10. Relationship To Other Documents
- Definition/laws: [`../docs/GLOSSARY.md`](../docs/GLOSSARY.md) (Lore Protocol), AP-9, NR-14.
- Decisions/changes: [`DECISION_REGISTRY.md`](./DECISION_REGISTRY.md), [`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md).
- Recovery: [`CONTEXT_RECOVERY_PROTOCOL.md`](./CONTEXT_RECOVERY_PROTOCOL.md) (consumes Lore to rebuild context).

*Lore is the project's memory. Protect it as you would the code — more, in fact,
because the code can be rewritten from the Lore, but not the reverse.*
