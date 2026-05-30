# `backend/decision_support/` — Decision Support Layer (V2-P6)

> **Layer:** Application Layer (`backend/`) — a V2 subsystem
> **Status:** Implemented (V2-P6)
> **Governing docs:** AP-4 (preserve uncertainty), AP-5/AP-8 (traceability/audit),
> AP-6 (reproducibility), AP-7 (boundaries), AP-9 (versioned decisions),
> AP-11 (governance); NR-4/NR-8/NR-11/NR-13/NR-14;
> [`../../docs/PROJECT_SCOPE.md`](../../docs/PROJECT_SCOPE.md) (O5/O6/O7, R1)

Structured, **explainable decision support** for clinical reviewers. It helps a
reviewer understand **what matters, why it matters, what evidence supports it, and
what uncertainty exists** — and nothing more.

> **This layer never diagnoses, treats, prescribes, issues clinical orders, or
> makes autonomous decisions.** The clinician is always the decision-maker. These
> limits are enforced mechanically by the `DecisionScopeGuard`.

---

## Purpose
Aggregate per-case context and produce explainable, traceable, governed
decision-support artifacts: context bundles, ranked evidence bundles, risk
context, review prioritization, and process guidance.

## Responsibilities
- **Context** (`context/`): aggregate case/review/finding/interpretation/
  knowledge/evidence (+ optional population) context into a deterministic bundle.
- **Evidence** (`evidence/`): bundle *all* evidence for a context, ranked; nothing
  hidden.
- **Risk** (`risk/`): aggregate inference/coverage/calibration/finding/evidence/
  knowledge/review risk into an explainable risk context (review-attention, not
  clinical risk).
- **Prioritization** (`prioritization/`): explainable review-priority from
  transparent weighted factors.
- **Guidance** (`guidance/`): review/evidence/knowledge/investigation/risk
  guidance from controlled, process-only templates.
- **Registry/Audit/Lineage** (`registry/`, `audit/`, `lineage/`): governed,
  versioned, immutable, traceable — reusing the shared mechanism from V2-P5.
- **Validation** (`validation/`): evidence/guidance/risk/registry/audit/lineage/
  version integrity + the **scope guard** and governance gate.
- **Reports** (`reports/`): decision-support/guidance/evidence/risk/prioritization/
  validation reports.
- **Schemas** (`schemas/`): the decision-support entity model.
- **Service** (`service.py`): the orchestration facade (`process_case`).

## Domain entities
`DecisionContext`, `EvidenceBundle`, `RiskContext`, `PrioritizationRecord`,
`GuidanceRecord`, `DecisionSupportRecord`, `DecisionVersion`, plus the
`DecisionAuditRecord` and `DecisionRegistryRecord` (shared event/registry types).

## Allowed dependencies
- ✅ `backend.multi_case_intelligence` — this layer builds on V2-P5 (it embeds
  population context and reuses the deterministic foundation, audit, lineage, and
  registry mechanisms).
- ✅ Pinned standard-library only.

## Forbidden dependencies / actions
- ❌ Importing `frontend/` (NR-8).
- ❌ Mutating any source or intelligence artifact (read-only).
- ❌ Diagnosis, treatment, medication advice, clinical orders, or autonomous
  decisions (out of scope; mechanically blocked by `DecisionScopeGuard`).

## Decision-support principles (enforced)
Every artifact is **explainable** (carries its factors/reason), **traceable**
(linked to evidence/knowledge/finding/review/context and, transitively, the
patient), **auditable**, **governed**, and **deterministic**. No black-box
recommendations.

## Integration boundary
Like V2-P5, the upstream clinical artifacts are read through the source
integration port defined in
[`../multi_case_intelligence/schemas/source.py`](../multi_case_intelligence/schemas/source.py).
Population context is consumed from a V2-P5 `PopulationAnalytics` artifact.

## Quick start
```python
from backend.decision_support import DecisionSupportService

ds = DecisionSupportService(population, population_analytics=analytics)  # analytics optional
bundle = ds.process_case("C3")     # context -> evidence -> risk -> priority -> guidance -> record
assert ds.validate().passed        # incl. decision_scope_integrity
```

Run the tests: `pytest backend/decision_support/tests`.
See [`docs/DESIGN.md`](./docs/DESIGN.md) and [`docs/DECISIONS.md`](./docs/DECISIONS.md).
