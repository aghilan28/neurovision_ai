# QUALITY METRICS

> **Document type:** Quality Assurance Foundation (V0-P5) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Quality Owner role)
> **Update procedure:** Governance-class change (ADR). Metric **values** are recorded routinely (not governance-class); the metric **set/scoring** is governance-class.
> **Derives from:** [`QUALITY_PHILOSOPHY.md`](./QUALITY_PHILOSOPHY.md); reports on the gates in [`QUALITY_GATES.md`](./QUALITY_GATES.md)

This document defines the **measurable indicators** of repository health and the
**scoring model** that turns them into a single, auditable signal. Metrics make
quality *visible* and *trendable* so decay is caught early (continuous quality).

> **Premise:** *what is not measured, drifts.* These metrics are deliberately
> **objective and countable** — not subjective. Every metric has a source, a
> target, and a gate it relates to.

---

## 1. Metric Catalog

Each metric: **definition · source · target · direction · related gate.**
(Direction: ↓ = lower is better, ↑ = higher is better.)

| ID | Metric | Definition | Source | Target | Dir | Gate |
|----|--------|------------|--------|--------|-----|------|
| **M1** | Architecture Violations | Open forbidden-import / boundary / cycle / rewrite findings | GCC + architecture audit | **0** | ↓ | G1 |
| **M2** | Dependency Violations | Import edges / external deps not recorded in the registry | Registry reconciliation | **0** | ↓ | G1 |
| **M3** | Documentation Freshness | Aggregate doc quality score + count of failing docs; staleness findings | Doc audit ([`DOCUMENTATION_VALIDATION.md`](./DOCUMENTATION_VALIDATION.md)) | score ≥ target; **0** failing | ↑/↓ | G2 |
| **M4** | Review Coverage | % of merged changes with required review completed | Changelog / review records | **100%** | ↑ | G3/G8 |
| **M5** | Test Coverage | Coverage of **invariant behaviors** (and per-version coverage number) | Test suite / CI | **100%** invariants | ↑ | G4 |
| **M6** | Validation Coverage | % of claims/results with required validation evidence | Validation records ([`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md)) | **100%** | ↑ | G5 |
| **M7** | Risk Closure Rate | Rate at which open risks are mitigated/closed; **# open Critical** | [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md) | 0 open Critical | ↑ / ↓ | G6/G7 |
| **M8** | Decision Traceability | % of consequential changes with an ADR; % ADRs linked both ways | Decision Registry + changelog | **100%** | ↑ | G8 |
| **M9** | Context Integrity | Context-audit findings (missing/outdated/conflicting/orphaned knowledge) | [`../context/CONTEXT_AUDIT_SYSTEM.md`](../context/CONTEXT_AUDIT_SYSTEM.md) | **0** | ↓ | G7 |
| **M10** | AI Reliability | AI changes accepted without rework ÷ total; recurrence of AI failure modes | AI review records ([`AI_OUTPUT_VALIDATION.md`](./AI_OUTPUT_VALIDATION.md)) | ↑ over time; **0** repeat-class failures | ↑/↓ | G3 |
| **M11** | Release Certification Rate | Approved ÷ attempted; count Approved-with-Risk / Deferred / Blocked | [`RELEASE_CERTIFICATION.md`](./RELEASE_CERTIFICATION.md) | trend; **0** post-release invariant regressions | ↑ | G6 |
| **M12** | Assumption Health | Open assumptions with no verification plan; overdue verifications | [`../../.gcc/ACTIVE_ASSUMPTIONS.md`](../../.gcc/ACTIVE_ASSUMPTIONS.md) | **0** unplanned/overdue | ↓ | G7 |

## 2. Hard-Zero Metrics (must be zero to pass a version gate)
These are non-negotiable; any nonzero value **blocks the version gate** (NR-12 +
Risk_Governance §3 "≥ High for invariants"):
- **M1** Architecture Violations = 0
- **M2** Dependency Violations = 0
- **M5** invariant Test Coverage = 100% (i.e. zero untested invariant behaviors)
- **M7** open **Critical** risks = 0
- **M8** Decision Traceability = 100% (no undocumented consequential change)
- **M9** Context Integrity findings = 0

## 3. Scoring Model (Repository Quality Index, RQI)

A single 0–100 index summarizing health, for trend-watching (not a substitute for
the hard-zero rules in §2). Five weighted pillars:

| Pillar | Metrics | Weight |
|--------|---------|-------:|
| **Architecture integrity** | M1, M2 | 25 |
| **Validation & testing** | M5, M6, M11 | 25 |
| **Governance & traceability** | M4, M8 | 20 |
| **Context & memory** | M7, M9, M12 | 20 |
| **Documentation & AI** | M3, M10 | 10 |

Each pillar scores 0–100% of its weight from its metrics' attainment vs. target;
**RQI = weighted sum**. Interpretation:
- **RQI = 100 and all §2 hard-zeros satisfied** → healthy; eligible for a version gate.
- **RQI 80–99** → minor findings; fix on schedule.
- **RQI < 80, or any §2 hard-zero unmet** → **not gate-eligible**; remediate first.

> RQI is a **health gauge**, never an excuse: a high RQI with a single hard-zero
> violation is still **blocked**. Metrics inform; gates decide.

## 4. Cadence & Recording
- **Per change/CI:** M1, M2, M4, M5, M8, M10 (mechanical) update automatically.
- **Per phase:** M3, M6, M9, M12 audited.
- **Per version gate / quarter / post-dormancy:** **all** metrics recomputed; RQI
  recorded in the changelog and reflected in [`../../.gcc/CURRENT_STATE.md`](../../.gcc/CURRENT_STATE.md).
- Metric **values** are stored in the repository (changelog/state), **never only**
  in a chat or memory (P6 mandate). Trends are part of Lore.

## 5. Using Metrics
- Metrics **trigger** preventive/corrective action ([`FAILURE_HANDLING.md`](./FAILURE_HANDLING.md)),
  feed **risk** review (Risk_Governance §4), and inform **release certification** (M11).
- A worsening trend is itself a **defect signal**, even if no single value is yet
  failing — investigate before it crosses a threshold.

## 6. Relationship To Other Documents
- Gates: [`QUALITY_GATES.md`](./QUALITY_GATES.md) · Validation: [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md)
- Risk: [`../governance/Risk_Governance.md`](../governance/Risk_Governance.md) · Context audit: [`../context/CONTEXT_AUDIT_SYSTEM.md`](../context/CONTEXT_AUDIT_SYSTEM.md)
- Live state: [`../../.gcc/CURRENT_STATE.md`](../../.gcc/CURRENT_STATE.md)

Changes to this document's metric set/scoring are governance-class and require an ADR.
