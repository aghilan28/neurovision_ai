# `docs/quality/` — Quality Assurance Foundation Index (V0-P5)

> **Document type:** Quality Assurance Foundation (V0-P5) index · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Quality Owner role)
> **Update procedure:** Index updated (Documentation change) when a quality doc is added/renamed; policy changes are governance-class (ADR).
> **Parent:** [`../README.md`](../README.md) · **Governance:** [`../governance/README.md`](../governance/README.md) · **OS:** [`../../.gcc/README.md`](../../.gcc/README.md)

The **Quality Assurance Foundation** — *what "good" means and how it is enforced* —
governing **Version 1 → Version 4**. Where **governance** (`docs/governance/`)
defines *how we change things*, **quality** defines *what correctness is, how it is
validated, gated, measured, and recovered when it fails.* These are **Tier 2
(process authority)** documents; quality **wraps** the governance checkpoints and
never contradicts them (on conflict, governance policy governs).

---

## Documents

| Document | Governs |
|----------|---------|
| [`QUALITY_PHILOSOPHY.md`](./QUALITY_PHILOSOPHY.md) | What quality is/isn't; preventive/detective/corrective/continuous; the quality hierarchy. |
| [`QUALITY_GATES.md`](./QUALITY_GATES.md) | The eight mandatory gates (G1–G8): purpose, owner, inputs/outputs, blocking/approval, failure, escalation. |
| [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md) | Validation taxonomy (VC-ARCH…VC-CLIN) + method/evidence/approval/audit/failure per category. |
| [`TEST_STRATEGY.md`](./TEST_STRATEGY.md) | Testing philosophy/strategy for V1–V4 (elaborates Testing Governance). |
| [`ARCHITECTURE_VALIDATION.md`](./ARCHITECTURE_VALIDATION.md) | Architecture compliance + drift/coupling detection + audit. |
| [`AI_OUTPUT_VALIDATION.md`](./AI_OUTPUT_VALIDATION.md) | Validating AI artifacts; AI trust / confidence / risk-scoring models; approve/reject/escalate. |
| [`DOCUMENTATION_VALIDATION.md`](./DOCUMENTATION_VALIDATION.md) | Doc correctness/completeness/consistency/freshness/traceability/ownership; quality score; retirement. |
| [`CODE_REVIEW_CHECKLISTS.md`](./CODE_REVIEW_CHECKLISTS.md) | Actionable per-domain review checklists (architecture/backend/frontend/ml/dsp/deploy/gov/AI/docs). |
| [`RELEASE_CERTIFICATION.md`](./RELEASE_CERTIFICATION.md) | Release certification: Approved / Approved-with-Risk / Deferred / Blocked + evidence. |
| [`QUALITY_METRICS.md`](./QUALITY_METRICS.md) | Measurable indicators (M1–M12) + the Repository Quality Index. |
| [`FAILURE_HANDLING.md`](./FAILURE_HANDLING.md) | Repository-level failure framework (detect→contain→recover→postmortem→prevent). |

## How quality fits together
```
              QUALITY_PHILOSOPHY  (what "good" means; hierarchy)
                       │
        ┌──────────────┼───────────────────────────────┐
        ▼              ▼                                 ▼
   QUALITY_GATES  VALIDATION_FRAMEWORK              QUALITY_METRICS
   (G1..G8)        (VC-* taxonomy)                   (M1..M12 + RQI)
        │              │                                 ▲
   ┌────┼──────────────┼─────────────────────────────────┘
   ▼    ▼              ▼
 ARCHITECTURE_  AI_OUTPUT_  DOCUMENTATION_   TEST_STRATEGY   CODE_REVIEW_CHECKLISTS
 VALIDATION     VALIDATION  VALIDATION       (V1..V4 tests)  (per-domain)
        │              │            │              │               │
        └──────────────┴─────► RELEASE_CERTIFICATION ◄─────────────┘
                                    │
                              FAILURE_HANDLING  (when any of the above fails)
```

## Reading order (first time)
1. [`QUALITY_PHILOSOPHY.md`](./QUALITY_PHILOSOPHY.md)
2. [`QUALITY_GATES.md`](./QUALITY_GATES.md) → [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md)
3. [`TEST_STRATEGY.md`](./TEST_STRATEGY.md), [`ARCHITECTURE_VALIDATION.md`](./ARCHITECTURE_VALIDATION.md), [`AI_OUTPUT_VALIDATION.md`](./AI_OUTPUT_VALIDATION.md), [`DOCUMENTATION_VALIDATION.md`](./DOCUMENTATION_VALIDATION.md)
4. [`CODE_REVIEW_CHECKLISTS.md`](./CODE_REVIEW_CHECKLISTS.md), [`RELEASE_CERTIFICATION.md`](./RELEASE_CERTIFICATION.md)
5. [`QUALITY_METRICS.md`](./QUALITY_METRICS.md), [`FAILURE_HANDLING.md`](./FAILURE_HANDLING.md)

All changes to documents in this directory are **governance-class** and require an
ADR ([`../governance/Decision_Governance.md`](../governance/Decision_Governance.md)).
