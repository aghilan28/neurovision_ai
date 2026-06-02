# CHANGELOG SYSTEM

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (workflow)**
> **Status:** Authoritative — defines how change history is logged and traced.
> **Owner:** Founder · **Kept current by:** the active contributor (every change)
> **Update procedure:** Governance-class for the *system*; routine for *entries* (one per change).
> **Enforces:** Principles **AP-8, AP-9**, Rules **NR-5, NR-14**
> **Last updated:** V0-P4

The changelog is the project's **traceable spine of history**: the single place
that ties every change to its decision, risk, dependency, validation, and review.
It is what makes the project **auditable** (AP-8) and what a future agent reads to
understand *what happened and why* (with the Lore Protocol).

> This document defines the **system**. The running log lives in
> **`CHANGELOG.md` at the repository root** (created with the first post-foundation
> change) and/or per-release notes; git history is the immutable backing store.

---

## 1. What Gets Logged
**Every change that merges to `main`** gets a changelog entry. At minimum:
- All **Major / Architecture / Governance / Emergency** changes (always).
- **Minor** and **Documentation** changes (concise entry).
- **State/registry updates** that reflect a milestone (e.g. a version gate).
- **Releases/tags** (with their validation evidence).

Trivial, non-meaning edits may be grouped, but are never invisible.

## 2. When It Gets Logged
- **At merge time**, as part of the change (not "later"). A merge without a log
  entry is an incomplete change (Branch_Workflow §3).
- **Version gates** and **releases** add a summary entry referencing the gate ADR.
- **Incidents/postmortems** add an entry linking the postmortem (Lore).

## 3. How Changes Are Categorized
Each entry is tagged with a **type** (aligned to commit types and change classes):

| Type | Meaning | Change class |
|------|---------|--------------|
| `arch` | Architecture/structure change | Architecture (A3) |
| `gov` | Governance/policy change | Governance (A3) |
| `feat` | New capability (in-boundary) | Minor/Major |
| `fix` | Bug fix | Minor |
| `docs` | Documentation | Documentation |
| `test` | Tests | Minor |
| `refactor` | Internal change, no contract effect | Minor |
| `chore` | Tooling/maintenance | Minor |
| `release` | Tag/release | — |
| `incident` | Incident + postmortem link | Emergency |

## 4. Entry Format
Template: [`TEMPLATES/CHANGE_RECORD_TEMPLATE.md`](./TEMPLATES/CHANGE_RECORD_TEMPLATE.md).

```
## [<version-tag or date>] — <type>(<scope>): <summary>
- Why:        <reason / problem solved>
- What:       <what changed>
- Class:      <A0|A1|A2|A3|AE>           (Architecture_Governance §13.1)
- Modules:    <modules touched>
- Refs:       ADR-NNNN, RFC-NNNN, RISK-NNNN, DEP-NNNN   (as applicable)
- Invariants: <which checked / preserved>
- Validation: <tests/GCC result>
- Review:     <human reviewer; never the producing agent>
- Rollback:   <how to reverse, or link>
- AI-TRACE:   <present for AI-authored changes; see AI_Governance §9>
```

## 5. How History Is Preserved
- **Append-only.** Entries are never edited to rewrite history; corrections are new
  entries that reference the prior one (mirrors ADR append-only — NR-14).
- **Git is the backing store.** The changelog summarizes; git history is the
  immutable detail. Tags are immutable (Release_Governance §6).
- **Superseded artifacts stay linked**, never deleted.

## 6. How Traceability Is Maintained
Each entry forms a **bidirectional link web**:
```
 change entry ──► ADR (why)        ADR ──► change entry (how realized)
        │       ──► RISK (managed)  RISK ──► change entry (mitigation)
        │       ──► DEP (recorded)  DEP  ──► change entry (introduced)
        └─────── ──► tests/CI (validated)
```
This is what lets any artifact answer "why does this exist / what changed it?"
deterministically — the recovery target of
[`CONTEXT_RECOVERY_PROTOCOL.md`](./CONTEXT_RECOVERY_PROTOCOL.md).

## 7. Responsibilities
- **The contributor** (human or AI) writes the entry as part of the change.
- **AI contributors** include the AI-TRACE block (AI_Governance §9).
- **The reviewer** confirms the entry is present and accurate before approving
  (Review_Governance §3).

## 8. Relationship To Other Documents
- Lore: [`LORE_PROTOCOL.md`](./LORE_PROTOCOL.md) · Decisions: [`DECISION_REGISTRY.md`](./DECISION_REGISTRY.md)
- Change routing/branching: [`../docs/governance/Change_Management.md`](../docs/governance/Change_Management.md), [`BRANCH_WORKFLOW.md`](./BRANCH_WORKFLOW.md)
- Releases: [`../docs/governance/Release_Governance.md`](../docs/governance/Release_Governance.md)

Changes to this system are governance-class and require an ADR.
