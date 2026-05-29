# DOCUMENTATION VALIDATION

> **Document type:** Quality Assurance Foundation (V0-P5) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Documentation Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Policy authority:** [`../governance/Documentation_Governance.md`](../governance/Documentation_Governance.md) (this document **operationalizes** its audit §8; on conflict, Documentation Governance governs).
> **Feeds:** the **Documentation Gate (G2)** in [`QUALITY_GATES.md`](./QUALITY_GATES.md) and **VC-DOC** in [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md)

Documentation is **infrastructure** in NeuroVision AI: the repository must stay
self-explanatory without the original research corpus (NR-14). This document makes
documentation quality **measurable and enforceable** — correctness, completeness,
consistency, freshness, traceability, and ownership — plus a **quality score** and
a **retirement process**.

> **Premise:** outdated or conflicting documentation is worse than none — it
> actively misleads. Documentation validation exists so the docs can always be
> trusted as truth.

---

## 1. The Six Quality Dimensions

| # | Dimension | Definition | Validated by |
|---|-----------|------------|--------------|
| 1 | **Correctness** | The doc's claims are true and match reality/the canonical source. | Conflict scan + review |
| 2 | **Completeness** | No placeholders/stubs/"TBD" in an authoritative doc; all required sections present. | Section/placeholder scan |
| 3 | **Consistency** | Uses Glossary terms exactly; never contradicts a higher tier. | Term scan + tier-precedence check |
| 4 | **Freshness** | Reflects current reality; Tier-3 state files match the repo; within review window. | Staleness scan |
| 5 | **Traceability** | Links to the principles/rules/decisions it depends on; reachable from an index. | Link scan + orphan scan |
| 6 | **Ownership** | Declares an Owner + Update procedure in its header. | Ownership scan |

## 2. The Six Audit Scans (operationalize Documentation_Governance §8)

Run per merge on touched docs, and **fully** at every version gate, each active
quarter, and after dormancy. Each scan is mechanizable (markdown tooling) and is
part of the Documentation Gate (G2).

| Scan | Passes when | Fails → action |
|------|-------------|----------------|
| **Orphan** | Every doc is reachable from root README → `docs/README.md` → a domain index. | Link it from the correct index or retire it (§5). |
| **Conflict** | No two docs assert contradictory facts; no lower tier contradicts a higher tier. | Reconcile to canonical source; fix the lower-tier doc. |
| **Staleness** | Tier-3 state files match git reality; dated docs within review window; superseded items marked. | Refresh from evidence; mark superseded; log. |
| **Term** | Every consequential term used is defined in the Glossary (NR-14). | Add the term to the Glossary in the same change set. |
| **Link** | Every internal link resolves. | Fix or remove the broken link. |
| **Ownership** | Every doc has an Owner + Update procedure. | Assign an Owner + Update procedure. |

Any scan failure **blocks** the Documentation Gate.

## 3. Documentation Quality Score

A simple, auditable score per document (and an aggregate for the repo). Each of the
six dimensions scores **2 (pass) / 1 (minor finding) / 0 (fail)**; max **12**.

| Score | Status | Consequence |
|-------|--------|-------------|
| **12** | Healthy | – |
| **9–11** | Minor findings | Fix at next touch; tracked. |
| **5–8** | Degraded | Fix before the doc is cited as authoritative again; raise a defect. |
| **0–4** | Failing | The doc is **not authoritative** until remediated; blocks G2 if in the change set. |

**Hard zeros (any one ⇒ doc fails regardless of total):** a conflict with a higher
tier; a placeholder in an authoritative doc; no Owner; an undefined consequential
term. The **repository aggregate** (mean score; count of failing docs) is the
*Documentation Freshness* metric in [`QUALITY_METRICS.md`](./QUALITY_METRICS.md).

## 4. Validation by Document Tier
(Tiers per [`../governance/Documentation_Governance.md`](../governance/Documentation_Governance.md) §1.)
- **Tier 0 Constitution / Tier 1 Architecture / Tier 2 Governance+Quality+Context:**
  changes are governance-class (ADR); conflict scan is strict; an ADR must exist.
- **Tier 3 OS state (`.gcc/`):** **freshness is paramount** — these are living docs;
  staleness is the dominant failure; each must have "Last updated" + update procedure.
- **Tier 4 module READMEs:** must match the module's real boundary (cross-checked by
  [`ARCHITECTURE_VALIDATION.md`](./ARCHITECTURE_VALIDATION.md)).
- **Tier 5 working docs (V1+: specs, model cards, runbooks):** must be reproducible
  and traceable to the artifact they describe.

> **Quality/Context placement:** the `docs/quality/` and `docs/context/` documents
> are **Tier 2 (process authority)**, governed identically to `docs/governance/`
> (governance-class changes, ADR-gated). They are canonical for their own subjects.

## 5. Documentation Retirement Process

Docs are **never silently deleted** (deletion destroys Lore). Retirement is a
governed lifecycle (Documentation_Governance §7):

```
 AUTHORITATIVE ─► (superseded by newer canonical doc/ADR) ─► SUPERSEDED ─► ARCHIVED
```
1. Mark the doc **Superseded** (Status header) and **link to its successor**.
2. Update every inbound link to point to the successor (no broken/orphan links).
3. Move to an archive location if it would otherwise clutter active navigation,
   keeping it reachable from a history index.
4. Record the retirement (changelog + ADR if it was Tier 0–2).
- **Never delete:** decisions, risks, assumptions, postmortems, learnings, or any
  superseded authoritative doc (see [`../context/MEMORY_RETENTION_POLICY.md`](../context/MEMORY_RETENTION_POLICY.md)).

## 6. Roles & Cadence
- **Owner:** Founder (Documentation Owner); each doc names its own Owner.
- **Review cycle:** touched docs every merge (G2); full audit at version gate,
  quarterly, and post-dormancy ([`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md) §5).
- AI agents may **run** the scans and **draft** fixes; a human approves substantive
  documentation changes (NR-7).

## 7. Relationship To Other Documents
- Policy: [`../governance/Documentation_Governance.md`](../governance/Documentation_Governance.md) · Gate: [`QUALITY_GATES.md`](./QUALITY_GATES.md) (G2)
- Context audits (missing/outdated/conflicting context): [`../context/CONTEXT_AUDIT_SYSTEM.md`](../context/CONTEXT_AUDIT_SYSTEM.md)
- Metric: [`QUALITY_METRICS.md`](./QUALITY_METRICS.md) (Documentation Freshness)

Changes to this document are governance-class and require an ADR.
