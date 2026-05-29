# BRANCH WORKFLOW

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (workflow)**
> **Status:** Authoritative
> **Owner:** Founder · **Kept current by:** the active contributor
> **Update procedure:** Governance-class change (ADR).
> **Enforces:** Principles **AP-8, AP-9, AP-11**, Rules **NR-5, NR-7, NR-8, NR-14**
> **Last updated:** V0-P4

Defines how branches are used so that **every change is reviewable, traceable, and
governed** before it reaches `main`. The model is deliberately simple (suited to a
solo founder + AI agents) but strict on the things that matter: review, Lore, and
governance.

---

## 1. Branch Types

| Type | Prefix | Purpose | Typical change class |
|------|--------|---------|----------------------|
| **Main** | `main` | Always-releasable, governed trunk. Protected. | — |
| **Feature** | `feat/` | A scoped capability or deliverable within a version. | Minor/Major |
| **Architecture** | `arch/` | A change to layers/edges/boundaries/invariants. | Architecture (A3) |
| **Research** | `research/` | Exploration/experiments; **not** mergeable as-is. | Exploratory |
| **Hotfix** | `hotfix/` | Time-critical fix to a live problem (V3+). | Emergency (AE) |
| **Governance** | `gov/` | Changes to `docs/governance/*` or `.gcc/` policy. | Governance (A3) |
| **Docs** | `docs/` | Documentation-only changes. | Documentation |

Branch names: `<prefix>/<short-topic>` (e.g. `feat/preprocessing-bandpass`,
`arch/add-contracts-module`, `gov/update-risk-policy`). Phase branches may use
`v<n>/<phase>` (e.g. `v0/governance-and-os`).

## 2. Core Rules
- **Never commit directly to `main`** (except the initial bootstrap). All change
  arrives via a reviewed merge.
- **One concern per branch** — keep branches small and reviewable (survivability
  over speed, AP-12).
- **Branch from current `main`**; rebase/merge `main` in to stay current.
- **Research branches are quarantine:** insights from them re-enter only through a
  proper `feat/`/`arch/` branch with review + Lore. Raw research is never merged.

## 3. Merge Requirements (by branch type)
A branch may merge to `main` only when its requirements are met:

| Requirement | feat | arch | gov | docs | hotfix |
|-------------|:----:|:----:|:---:|:----:|:------:|
| GCC checks green (imports/boundaries/acyclicity) | ✅ | ✅ | ✅ | ✅ | ✅ (post-hoc if AE) |
| Required tests green ([`../docs/governance/Testing_Governance.md`](../docs/governance/Testing_Governance.md)) | ✅ | ✅ | n/a | n/a | ✅ |
| Human review ([`../docs/governance/Review_Governance.md`](../docs/governance/Review_Governance.md)) — **never AI-only** (NR-7) | ✅ | ✅ (Founder) | ✅ (Founder) | ✅ | ✅ (Founder) |
| Approved **ADR** ([`DECISION_REGISTRY.md`](./DECISION_REGISTRY.md)) | if A2+ | ✅ | ✅ | if meaning-change | retro ≤72h |
| **RFC** trail | if A2+ | ✅ | ✅ | — | retro |
| **Lore** updated (commit annotations, registries, state) | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Changelog** entry ([`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md)) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Affected docs/READMEs updated in same change set | ✅ | ✅ | ✅ | ✅ | ✅ |

## 4. Lore Requirements (every merge)
Per [`LORE_PROTOCOL.md`](./LORE_PROTOCOL.md), each merge must leave:
- Commit messages explaining **why** (template:
  [`TEMPLATES/COMMIT_MESSAGE_TEMPLATE.md`](./TEMPLATES/COMMIT_MESSAGE_TEMPLATE.md)).
- Links to ADR/RFC/RISK/DEP as applicable.
- Updated `CURRENT_STATE`/registries if state changed.
- For AI-authored work, the **AI-TRACE block** ([`../docs/governance/AI_Governance.md`](../docs/governance/AI_Governance.md) §9).

## 5. Governance Requirements
- **Architecture (`arch/`)** and **Governance (`gov/`)** branches require an
  approved ADR **and** Founder review before merge (A3).
- **No branch** may merge while it skips a version gate (NR-12) or works out of
  scope (NR-13) — caught at change classification (Change_Management §1) and review.
- A merge that bypasses checks is reverted and recorded as an incident.

## 6. Review Requirements
- Review depth is **risk-based** (Review_Governance §4): A1 standard → A3 deepest.
- The **producing agent never reviews/approves its own change** (NR-7).
- Cross-module branches require enumeration of every module touched and proof that
  no new forbidden edge was introduced (Review_Governance §6).

## 7. Lifecycle
```
 create branch ─► commit (annotated) ─► self-validate ─► open PR ─► GCC+tests ─►
 human review ─► (ADR if A2+) ─► merge to main ─► changelog + state update ─► delete branch
```
Tags/releases are cut from `main` per [`../docs/governance/Release_Governance.md`](../docs/governance/Release_Governance.md).

## 8. Relationship To Other Documents
- Change routing: [`../docs/governance/Change_Management.md`](../docs/governance/Change_Management.md)
- Review/Release: [`../docs/governance/Review_Governance.md`](../docs/governance/Review_Governance.md), [`../docs/governance/Release_Governance.md`](../docs/governance/Release_Governance.md)
- Logging/Lore: [`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md), [`LORE_PROTOCOL.md`](./LORE_PROTOCOL.md)

Changes to this document are governance-class and require an ADR.
