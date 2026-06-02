# DOCUMENTATION GOVERNANCE

> **Document type:** Governance Layer (V0-P3)
> **Status:** Authoritative
> **Owner:** Founder (Documentation Owner role)
> **Update procedure:** *Documentation change* path in [`Change_Management.md`](./Change_Management.md); changes to **this** policy are governance-class (ADR).
> **Enforces:** Principles **AP-8, AP-9, AP-11** and Rules **NR-5, NR-14** ([`../NON_NEGOTIABLE_RULES.md`](../NON_NEGOTIABLE_RULES.md))
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

In NeuroVision AI, **documentation is infrastructure.** The repository must remain
**self-explanatory without the original research corpus** (Rule **NR-14**, the
Lore Protocol). This document governs how documentation is structured, owned,
reviewed, versioned, and audited — so that documentation stays *true, singular,
and current*, and the project never decays into **repository entropy**.

---

## 1. Documentation Hierarchy

Documents have a strict precedence. When two documents appear to conflict, the
**higher tier governs**, and the conflict is logged as a consistency defect to fix.

```
 Tier 0  CONSTITUTION (docs/*.md)              ── highest authority (the "why/what")
            Vision · Objectives · Scope · Version Model · Principles · Rules · Glossary
 Tier 1  ARCHITECTURE (docs/architecture/*.md) ── structural authority ("how it's shaped")
 Tier 2  GOVERNANCE (docs/governance/*.md)     ── process authority ("how we change it")
 Tier 3  OPERATING SYSTEM (.gcc/*.md)          ── live state/context ("where we are")
 Tier 4  MODULE READMEs (<module>/README.md)   ── local contracts
 Tier 5  WORKING DOCS (specs, model cards, runbooks — created V1+)
```

- **Tier 0** can only change via a recorded, reviewed governance decision.
- A **lower tier may never contradict a higher tier.** The Glossary (Tier 0) is the
  canonical terminology source for all tiers.

## 2. Canonical Documents

A **canonical document** is the single source of truth for its subject. There is
**exactly one** canonical document per subject; everything else **links** to it
rather than restating it (to prevent conflicting copies).

| Subject | Canonical document |
|---------|--------------------|
| Why the project exists | [`../PROJECT_VISION.md`](../PROJECT_VISION.md) |
| Objectives & metrics | [`../PROJECT_OBJECTIVES.md`](../PROJECT_OBJECTIVES.md) |
| Scope | [`../PROJECT_SCOPE.md`](../PROJECT_SCOPE.md) |
| Versions | [`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md) |
| Principles | [`../ARCHITECTURAL_PRINCIPLES.md`](../ARCHITECTURAL_PRINCIPLES.md) |
| Rules | [`../NON_NEGOTIABLE_RULES.md`](../NON_NEGOTIABLE_RULES.md) |
| Terminology | [`../GLOSSARY.md`](../GLOSSARY.md) |
| Architecture (5 docs) | [`../architecture/`](../architecture/) |
| Each governance domain | the corresponding `docs/governance/*.md` |
| Live project state | [`../../.gcc/CURRENT_STATE.md`](../../.gcc/CURRENT_STATE.md) |
| Decisions index | [`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md) |

**Rule:** facts live in exactly one canonical place. Duplication is a defect.

## 3. Document Ownership

Every document declares an **Owner** in its header. Ownership means accountability
for accuracy and currency, not exclusive authorship.

| Document class | Owner | Approver of changes |
|----------------|-------|---------------------|
| Constitution (Tier 0) | Founder | Founder (ADR required) |
| Architecture (Tier 1) | Founder (Architecture Owner) | Founder (ADR; Architecture_Governance) |
| Governance (Tier 2) | Founder | Founder (ADR) |
| OS state (Tier 3) | Founder; **kept current by the active agent** | Founder (state updates are routine, audited) |
| Module READMEs (Tier 4) | Module owner (Founder in solo context) | Reviewer |
| Working docs (Tier 5) | Author | Reviewer |

Every document **must** have an owner; an ownerless document is an audit finding.

## 4. Documentation Review Process

- **Editorial** (typos, formatting, clarifying wording without changing meaning):
  lightweight review; may be self-reviewed and logged.
- **Substantive** (changes meaning, adds/removes a claim, alters a contract):
  reviewed under [`Review_Governance.md`](./Review_Governance.md); if it touches a
  Tier 0–2 document, an **ADR is required** (Rule **NR-5**).
- **Every** documentation change is recorded in the changelog
  ([`../../.gcc/CHANGELOG_SYSTEM.md`](../../.gcc/CHANGELOG_SYSTEM.md)).
- A change that introduces a **new term** must update the Glossary in the same
  change set (Rule **NR-14**).

## 5. Versioning Process

- All documents are **version-controlled in git**; history is the version record.
- Tier 0–2 documents carry a **Status** header (`Authoritative`, or
  `Proposed`/`Superseded` during change).
- A superseded decision is **not deleted**; it is marked superseded and linked to
  the ADR that replaced it (decisions are append-only — see
  [`Decision_Governance.md`](./Decision_Governance.md)).
- Tier 3 (OS state) documents are **living**: updated continuously, each with a
  "Last updated / Updated by" line and an update procedure.

## 6. Documentation Quality Standards

Every document must be:
1. **Complete** — no placeholders, stubs, or "TBD" in an authoritative document.
2. **Singular** — states each fact once, in the canonical place; links elsewhere.
3. **Consistent** — uses Glossary terms exactly; agrees with higher tiers.
4. **Owned** — declares an Owner and an Update procedure in its header.
5. **Traceable** — links to the principles/rules/decisions it depends on.
6. **Current** — reflects reality; staleness is a defect (see §8).
7. **Navigable** — cross-links to related documents; reachable from an index.
8. **Reader-aware** — written so a new human or AI agent can use it without prior
   context (Lore Protocol).

## 7. Documentation Lifecycle

```
 DRAFT ──► REVIEW ──► AUTHORITATIVE ──► (amend via ADR) ──► SUPERSEDED/ARCHIVED
   │                      │
   └── must not be cited as truth while DRAFT
```

- **Draft:** in progress; clearly marked; not authoritative.
- **Review:** under governance review.
- **Authoritative:** the canonical truth for its subject.
- **Superseded/Archived:** replaced; retained for history, clearly marked, linked
  to its successor. **Never silently deleted** (deletion destroys Lore).

## 8. Documentation Audit Process (entropy prevention)

Run at every version gate, each active quarter, and on resuming after dormancy:

1. **Orphan scan** — every doc is reachable from an index/parent (root README →
   `docs/README.md` → domain indexes). Unreachable docs are flagged.
2. **Conflict scan** — no two documents assert contradictory facts; lower tiers
   do not contradict higher tiers.
3. **Staleness scan** — Tier 3 state files match reality; dated docs are within
   their review window; superseded items are marked.
4. **Term scan** — every consequential term used is defined in the Glossary.
5. **Link scan** — internal links resolve (no broken references).
6. **Ownership scan** — every doc has an Owner + Update procedure.

Findings are logged as defects/risks and remediated; results are recorded in the
changelog.

### 8.1 The Four Entropy Failures This Document Prevents
| Failure | Definition | Primary defense |
|---------|------------|-----------------|
| **Orphaned documents** | Docs reachable by no index/link. | Orphan scan (§8.1); index-from-root rule. |
| **Conflicting documents** | Two docs disagree. | Single-canonical-source rule (§2); conflict scan; tier precedence. |
| **Outdated documents** | Doc no longer matches reality. | Living Tier-3 update procedures; staleness scan; ownership. |
| **Undocumented architecture** | Structure exists with no doc/decision. | NR-5; Architecture_Governance; audit reconciliation. |

## 9. Relationship To Other Governance Documents
- Decisions: [`Decision_Governance.md`](./Decision_Governance.md) · Change paths: [`Change_Management.md`](./Change_Management.md)
- Review: [`Review_Governance.md`](./Review_Governance.md) · Lore: [`../../.gcc/LORE_PROTOCOL.md`](../../.gcc/LORE_PROTOCOL.md)
- Indexes: [`../README.md`](../README.md), [`../../.gcc/README.md`](../../.gcc/README.md)

Changes to this document are governance-class and require an ADR.
