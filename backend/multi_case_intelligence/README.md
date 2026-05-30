# `backend/multi_case_intelligence/` — Multi-Case Intelligence Layer (V2-P5)

> **Layer:** Application Layer (`backend/`) — a V2 subsystem
> **Status:** Implemented (V2-P5)
> **Governing docs:** AP-3 (determinism), AP-5/AP-8 (traceability/auditability),
> AP-6 (reproducibility), AP-7 (boundaries), AP-9 (versioned decisions),
> AP-11 (governance by construction); NR-8/NR-9/NR-11/NR-13/NR-14;
> [`../../docs/architecture/IMPORT_RULES.md`](../../docs/architecture/IMPORT_RULES.md)

A system that understands **collections of cases**. It generates *intelligence*
(cohorts, population analytics, trends, quality analytics) over the populations of
Version 2 cases, reviews, findings, interpretations, knowledge, and evidence —
**without ever altering individual case truth**.

The purpose is **intelligence generation, not prediction** and not diagnosis.

---

## Purpose
Produce versioned, traceable, auditable, deterministic, governed, reproducible
intelligence about populations of clinical artifacts, so reviewers and the
decision-support layer (V2-P6) gain cohort awareness, population analytics, and
quality insight.

## Responsibilities
- **Cohorts** (`cohorts/`): build case/review/finding/knowledge/evidence cohorts
  from serializable selection criteria.
- **Population analytics** (`analytics/`, `statistics/`): counts, distributions,
  coverage, variability, frequency, confidence — per subject kind.
- **Trends** (`trends/`): finding/evidence/review/knowledge/cohort trends over a
  deterministic ordinal dimension.
- **Quality analytics** (`quality/`): review/finding quality, evidence/
  interpretation completeness, knowledge coverage, referential integrity.
- **Registry** (`registry/`): the system of record; no artifact exists outside it.
- **Audit** (`audit/`): append-only, hash-chained, immutable event log.
- **Lineage** (`lineage/`): provenance back to Patient/Case/Review/Finding/Knowledge.
- **Validation** (`validation/`): integrity validators + the governance gate
  (architecture/quality/context/risk).
- **Reports** (`reports/`): cohort/analytics/trend/population/quality/validation.
- **Schemas** (`schemas/`): the deterministic foundation + artifact/source models.
- **Service** (`service.py`): the orchestration facade.

## Allowed dependencies
- ✅ The shared deterministic foundation in this package's `schemas/`.
- ✅ Pinned standard-library only (no third-party runtime deps).
- ✅ (Conceptually) the V1 ML/evaluation and V2 case/review/finding/knowledge
  modules — see **Integration boundary** below.

## Forbidden dependencies / actions
- ❌ Importing `frontend/` (NR-8) or any infrastructure module as code.
- ❌ Mutating any source artifact (population intelligence is read-only; the
  `SourcePopulation` is immutable and source immutability is validated).
- ❌ Diagnosis, treatment, prediction, or autonomous decision-making.
- ❌ Producing any artifact outside the registry, audit trail, and lineage graph.

## Integration boundary (important)
In a fully materialized repository, the source artifact contracts in
[`schemas/source.py`](./schemas/source.py) would be **imported from** the V2
case/review/finding/knowledge `backend` modules and the V1 `ml`/`evaluation`
layers. Those modules are not yet present on disk, so this subsystem defines a
**minimal, faithful integration port** for them (immutable dataclasses carrying
exactly the fields the documented contracts specify, including the V1
`UncertaintySignal` and `RiskAttributes`). The port is the single seam to replace
when the upstream modules land; no intelligence logic changes.

## Determinism & governance guarantees
- **No wall-clock, no randomness** anywhere (ordering uses logical sequence
  numbers; identity is content-addressed).
- Every artifact is **versioned** (logical id = definition/scope; content hash =
  result), **audited** (immutable hash chain), and **lineage-tracked**.
- Every artifact passes the **governance gate** before registry admission.

## Examples
- Build a cohort of all `SZ` findings, then compute its analytics.
- Generate population analytics + trends + quality, roll them into a population
  report, and validate the whole subsystem.

## Boundary rules
- One-way dependency: this subsystem may be consumed by `decision_support/`
  (V2-P6); it does not import it.
- See [`docs/DESIGN.md`](./docs/DESIGN.md) and [`docs/DECISIONS.md`](./docs/DECISIONS.md).

## Quick start
```python
from backend.multi_case_intelligence import MultiCaseIntelligenceService
from backend.multi_case_intelligence.population import PopulationBuilder

population = PopulationBuilder().add_patient(...).add_case(...).build()
svc = MultiCaseIntelligenceService(population)
bundle = svc.run_full_intelligence()      # analytics + trend + quality + report
assert svc.validate().passed
```

Run the tests: `pytest backend/multi_case_intelligence/tests`.
