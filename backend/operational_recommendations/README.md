# `backend/operational_recommendations/` — Operational Recommendation Layer (V3-P6)

> **Layer:** Application (`backend/`) — a V3 subsystem
> **Status:** Implemented (V3-P6)
> **Governing docs:** AP-3/AP-6 (determinism/reproducibility), AP-5/AP-8 (traceability/
> audit), AP-7/NR-8 (boundaries), AP-9, NR-9/NR-10/NR-11/NR-13; ADR-0009

Creates **explainable operational recommendations**: guidance, prioritization,
optimization suggestions, and escalation candidates. This is **not** clinical
decision support, medical advice, diagnosis, or treatment.

---

## Operational intelligence only — never clinical
Every recommendation is derived strictly from operational/workflow/system
intelligence: the V3-P5 **analytics** records (primary input), plus the V3-P3
**workflows** and V3-P4 **graph** for linking and evidence. It never reads clinical
signal data and never produces clinical advice.

## No black-box recommendations
Every recommendation is **evidence-linked AND analytics-linked**. The governance
gate's **risk** dimension fails any record that is not both — mechanizing *no
black-box recommendations*. Each record carries an explainable `statement`,
`rationale`, a `RecommendationPriority` (level + score + reason + supporting
signals), and the `RecommendationEvidence` it cites.

## Engines
| Engine | Module | Produces |
|--------|--------|----------|
| Context | `context/` | a deterministic `RecommendationContext` bundle (analytics/workflow/graph/temporal/risk/health) |
| Guidance | `guidance/` | workflow / review-queue / escalation / operational / resource-awareness guidance (each cites evidence) |
| Prioritization | `prioritization/` | explainable priority levels (low→critical) + reasons + supporting metrics/risks/trends/workflow |
| Optimization | `optimization/` | workflow / dependency / queue / process **suggestions** (no execution) |
| Escalation | `escalation/` | escalation **candidates** + reasons + evidence + risk context + priority (no automatic escalation) |

## Suggestions only — never executed, never auto-escalated
The engines describe candidate improvements and escalation candidates; a human
decides whether to act. Nothing mutates a workflow, reorders a queue, or escalates
anything.

## Governance, audit, lineage, registry
Each recommendation passes the `RecommendationGovernanceGate`
(architecture/quality/context/**risk = evidence-linked + analytics-linked**), then
gets a shared-lineage node parented by the **analytics** nodes it cites, an
immutable hash-chained audit event, a content-addressed version, and a registry
record. `verify_chain` spans Patient → … → Analytics → **Recommendation**. No
recommendation exists outside the registry. Shares the single
`ml.lineage.LineageTracker` and the shared `ImmutableAuditLog`.

## Quick start
```python
from backend.operational_recommendations import OperationalRecommendationService

orr = OperationalRecommendationService(lineage_tracker=shared_tracker)
orr.load_intelligence(analytics=analytics_records, workflows=workflow_records,
                      graph_registry=graph.registry)
produced = orr.generate()                    # guidance + optimization + escalation
assert all(orr.validate(r).ok for r in orr.all_records(produced))
```

Run the tests: `pytest tests/test_operational_recommendations.py`.
See [`docs/V3_P6_OPERATIONAL_RECOMMENDATIONS.md`](./docs/V3_P6_OPERATIONAL_RECOMMENDATIONS.md).

## Scope guard (NOT built — NR-13)
No dashboards, no operational workstation, no realtime/autonomous execution, no
auto escalation, no clinical recommendations/diagnosis/treatment, no FHIR/HL7/EMR,
no V4 features.
