# Commit Message Template

> **Framework:** [`../LORE_PROTOCOL.md`](../LORE_PROTOCOL.md) §5
> Commits are permanent Lore. Every consequential commit explains **why**, not just
> **what**, and links its governing records.

```
<type>(<scope>): <imperative summary, <=72 chars>

Why: <the reason / problem being solved>
What: <what changed, briefly>
Refs: ADR-NNNN, RFC-NNNN, RISK-NNNN, DEP-NNNN   (as applicable)
Invariants: <which invariants were checked / preserved>
AI-TRACE: <present for AI-authored commits; see AI_Governance §9; else omit>
```

**`type`** ∈ `feat` · `fix` · `docs` · `refactor` · `test` · `chore` · `gov` ·
`arch` (aligned with the changelog types in [`../CHANGELOG_SYSTEM.md`](../CHANGELOG_SYSTEM.md) §3).

**`scope`** = the module or area (e.g. `preprocessing`, `evaluation`, `gcc`, `docs`).

**Rules:**
- Architecture/governance commits **must** reference an ADR (NR-5).
- A commit that introduces/changes a dependency references the Dependency Registry
  update (NR-2 if debt).
- Keep the summary imperative ("add", "fix", "record"), present tense.

**Examples:**
```
arch(evaluation): add held-out-site split to LOSO runner

Why: generalization claims require domain-shift evidence (NR-15)
What: adds site-disjoint fold generation; updates evaluation README contract
Refs: ADR-0014, RFC-0009, RISK-0007
Invariants: patient-disjoint preserved; reproducibility preserved
AI-TRACE: agent=Claude; reviewer=Founder; self-validation=pass
```
```
docs(gcc): update CURRENT_STATE after V1 preprocessing milestone

Why: keep live state honest for the next agent
What: marks preprocessing determinism tests complete
Refs: ADR-0012
Invariants: n/a (state doc)
```
