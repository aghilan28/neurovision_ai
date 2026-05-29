# AI OUTPUT VALIDATION

> **Document type:** Quality Assurance Foundation (V0-P5) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Quality Owner / AI Governance Owner roles)
> **Update procedure:** Governance-class change (ADR).
> **Policy authority:** [`../governance/AI_Governance.md`](../governance/AI_Governance.md) (this document **operationalizes** AI validation; on conflict, AI Governance governs).
> **Feeds:** the **AI Review Gate (G3)** in [`QUALITY_GATES.md`](./QUALITY_GATES.md) and **VC-AI** in [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md)

NeuroVision AI is built primarily by AI agents under a solo founder. This document
defines how **AI-generated artifacts are validated** before they are trusted, and
the **trust / confidence / risk** models that decide how much scrutiny each
artifact gets. It applies to **Claude, Codex, Cursor, Kiro, MCP tools, and any
future AI system** ([`../governance/AI_Governance.md`](../governance/AI_Governance.md) §1).

> **Premise:** AI output is **plausible by default and correct only by
> verification.** The danger is not obvious garbage — it is confident,
> well-formatted, *wrong*. Validation is how we separate the two. **No AI approves
> its own output** (NR-7).

---

## 1. What Is Validated (artifact types)

| Artifact | Primary risks | Validation focus |
|----------|---------------|------------------|
| **Generated code** | Hallucinated APIs; boundary/cycle violations; silent deps; scope creep | Symbol resolution; GCC/boundary; diff scope; tests |
| **Generated documentation** | Conflicts with higher tier; undefined terms; orphan; overclaim | Doc scans (G2); Glossary; tier consistency |
| **Generated architecture** | Drift; rewrite; unrecorded edge | RFC/ADR present; Architecture Gate (G1) |
| **Generated tests** | Tests that don't test the invariant; tests weakened to pass | Mutation/sanity review; assert invariant behavior; not disabled |
| **Generated workflows** (scripts/CI/agents) | Bypassing gates; smuggling forbidden deps; non-determinism | Gate-bypass check; support-isolation; reproducibility |

## 2. Validation Pipeline (every AI change)

```
 AI output ─► (a) AI-TRACE present & accurate? ─► (b) anti-hallucination (symbols resolve?) ─►
 (c) scope/dependency diff clean? ─► (d) boundary/invariant checks (GCC+tests) ─►
 (e) artifact-specific checks (§1) ─► (f) AI risk score (§5) ─► (g) human review (NR-7) ─► decision (§6)
```

- **(a) AI-TRACE:** the block from [`../governance/AI_Governance.md`](../governance/AI_Governance.md) §9
  must be present and **match what the diff actually does** (agent, context-read,
  scope, risk-class, decisions, deps, assumptions, invariants, self-validation).
- **(b) Anti-hallucination:** **every** referenced symbol/file/endpoint resolves to
  real source; no invented APIs; no fabricated metrics. Unresolvable reference ⇒ fail.
- **(c) Scope/dependency:** the diff does **only** what was requested; no silent
  scope expansion (NR-13) or unrecorded dependency (NR-2, Dependency Registry).
- **(d) Boundary/invariant:** GCC + boundary/invariant tests green (NR-8 and the
  cross-version invariants).
- **(e) Artifact-specific:** the focus column in §1.
- **(f)–(g):** score, then a **human** decides.

## 3. AI Trust Model

Trust is **earned per artifact, not granted per system.** Trust modulates *review
depth*, never *whether* review happens (review always happens — NR-7).

| Trust level | When it applies | Effect on review |
|-------------|-----------------|------------------|
| **T0 — Untrusted** | New AI system; or any artifact touching architecture/invariants/clinical | Deepest review; RFC/ADR if A2+ |
| **T1 — Provisional** | Approved system, in-boundary change, clean recent history | Standard review |
| **T2 — Established** | Approved system with a sustained record of clean, low-risk artifacts of this type | Standard review, faster; **still human-approved** |

- Trust is **per (system × artifact-type)** and is **reset to T0** for that pair
  after any validated failure (a hallucination, a boundary breach, a scope creep).
- **Trust never reaches a level that removes human approval.** There is no "auto-merge"
  for AI output (NR-7).
- MCP tool output is **always T0** (untrusted input source).

## 4. AI Confidence Model

The agent's **stated confidence is an input, not evidence.** It is treated like
the platform's own stance on clinical uncertainty (AP-4): honesty is rewarded,
overclaiming is penalized.

- The agent **must** state, in AI-TRACE, its self-validation result and any
  **assumptions** ([`../../.gcc/ACTIVE_ASSUMPTIONS.md`](../../.gcc/ACTIVE_ASSUMPTIONS.md)).
- **High stated confidence + low evidence ⇒ higher scrutiny**, not lower (the
  confident-wrong failure, [`../governance/AI_Governance.md`](../governance/AI_Governance.md) §5.9).
- An agent that says **"I am not sure / I could not verify X"** is behaving
  correctly and is preferred over one that guesses. Uncertainty must be surfaced,
  never hidden.
- Confidence claims are **never** accepted in place of validation evidence (§2).

## 5. AI Risk Scoring Model

Every AI artifact gets a score that sets review depth and trust impact. Score
combines **blast radius** (the change's risk tier) and **verification signals**.

**Step 1 — base tier** = the change's risk class A0–A3/AE
([`../governance/Architecture_Governance.md`](../governance/Architecture_Governance.md) §13.1).

**Step 2 — risk signals** (each present signal raises the effective score):
- touches a **cross-version invariant** or **clinical** output (auto ≥ High);
- introduces/changes a **dependency** or **contract**;
- spans **multiple modules**;
- AI-TRACE **incomplete/inaccurate**;
- any **unresolved symbol** (auto fail, not just score);
- **stated confidence high but evidence thin**.

**Step 3 — effective AI risk** (drives review depth):
| Score | Condition | Review depth |
|-------|-----------|--------------|
| **Low** | A0/A1, in-boundary, clean AI-TRACE, no signals | Standard human review |
| **Medium** | A2, or one risk signal | Deep review + ADR if A2+ |
| **High** | A3, invariant/clinical, dependency/contract, or multiple signals | Deepest review + ADR + Founder architecture review |
| **Reject-on-sight** | unresolved symbol, missing AI-TRACE, self-approval attempt, gate-bypass | Auto-reject (§6) |

Scores are trended as the **AI reliability** metric
([`QUALITY_METRICS.md`](./QUALITY_METRICS.md)).

## 6. AI Approval / Rejection / Escalation Workflows

### 6.1 Approval workflow
1. Pipeline §2 (a)–(f) all pass.
2. A **human (Founder)** runs [`../../.gcc/CHECKLISTS/ai_review_checklist.md`](../../.gcc/CHECKLISTS/ai_review_checklist.md).
3. For A2+: an **ADR** exists and is approved (NR-5).
4. Founder records approval; change merges with its **AI-TRACE** preserved as Lore.
   *(The producing agent never approves — NR-7.)*

### 6.2 Rejection workflow
Reject (do **not** "fix in review") when any holds: unresolved/hallucinated symbol;
missing/inaccurate AI-TRACE; silent scope or dependency change; boundary/cycle
violation; weakened/disabled guarding test; self-approval attempt; gate bypass.
- Return to the agent with the **specific** failure and the rule it violated.
- If a **class** of error recurs, open an **AI**-category risk
  ([`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md)) and add a guarding
  check (preventive quality).

### 6.3 Escalation workflow
- **Ambiguity** (is this in scope / is this architecture?) ⇒ escalate to Founder;
  default conservative (treat as architecture; treat as out-of-scope until confirmed).
- **Suspected invariant/clinical-safety impact** ⇒ **halt** immediately; do not
  merge; Founder decision required; record.
- **Repeated failures from one system×artifact pair** ⇒ reset trust to T0; consider
  an ADR adjusting that system's approved uses.

## 7. Evidence (recorded, reproducible)
For each AI change, the repository retains: the **AI-TRACE block**, the validation
pipeline result, the AI risk score, the reviewer + decision, and links to any
ADR/RISK/assumption. This is Lore ([`../../.gcc/LORE_PROTOCOL.md`](../../.gcc/LORE_PROTOCOL.md))
and feeds context recovery.

## 8. Relationship To Other Documents
- Policy: [`../governance/AI_Governance.md`](../governance/AI_Governance.md) · Review: [`../governance/Review_Governance.md`](../governance/Review_Governance.md)
- Gate/metric: [`QUALITY_GATES.md`](./QUALITY_GATES.md) (G3), [`QUALITY_METRICS.md`](./QUALITY_METRICS.md) (AI reliability)
- Checklists: [`../../.gcc/CHECKLISTS/ai_review_checklist.md`](../../.gcc/CHECKLISTS/ai_review_checklist.md); per-domain in [`CODE_REVIEW_CHECKLISTS.md`](./CODE_REVIEW_CHECKLISTS.md)

Changes to this document are governance-class and require an ADR.
