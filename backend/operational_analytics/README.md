# `backend/operational_analytics/` — Operational Analytics Layer (V3-P5)

> **Layer:** Application (`backend/`) — a V3 subsystem
> **Status:** Implemented (V3-P5)
> **Governing docs:** AP-3/AP-6 (determinism/reproducibility), AP-5/AP-8 (traceability/
> audit), AP-7/NR-8 (boundaries), AP-9, NR-9/NR-10/NR-11/NR-13; ADR-0009

Creates platform-wide **operational intelligence**: the platform can now understand
operational behavior, performance, quality, trends, risks, and system health. This
phase creates **intelligence only** — no recommendations, no actions, no dashboards.

---

## Derived intelligence — analytics is never a source of truth
Every analytics artifact is computed strictly from already-governed upstream
artifacts — **events** (V3-P1), **temporal intelligence** (V3-P2), **workflows**
(V3-P3), and the **operational graph** (V3-P4) — read through the single,
deterministic `AnalyticsSourceView`. The governance gate's **risk** dimension fails
any record that is not derived from upstream sources, mechanizing *analytics must
never become a source of truth*.

## Engines
| Engine | Module | Produces |
|--------|--------|----------|
| Metrics | `metrics/` | counts, rates, distributions, coverage, throughput, velocity, health indicators |
| Health | `health/` | explainable [0,1] case/review/workflow/knowledge/graph/operational/system health |
| Performance | `performance/` | completion/transition/workflow/review performance, efficiency, latency + velocity (logical steps) |
| Quality | `quality/` | workflow/review/finding/knowledge quality + graph & analytics integrity |
| Trend | `trends/` | temporal/workflow/review/finding/knowledge/operational trends (from the ordered event stream) |
| Risk | `risk/` | workflow/operational/quality/knowledge/dependency/bottleneck risk **scores** (no recommendations) |

`engine/` (the `AnalyticsBuilder`) combines them into derived `AnalyticsRecord`
artifacts — one per category plus a composite `operational` summary.

## Deterministic, logical-step time (NR-9/NR-10)
The platform forbids wall-clock, so durations/latencies are counts of ordered
**logical steps** and trends are computed over the deterministically-ordered event
stream split into two equal logical halves (earlier vs later). Identical inputs
reproduce identical analytics, versions, and audit heads.

## Governance, audit, lineage, registry
Each analytics record passes the `AnalyticsGovernanceGate`
(architecture/quality/context/**risk = derived**), then gets a shared-lineage node
parented by the **upstream** nodes it summarizes, an immutable hash-chained audit
event, a content-addressed version, and a registry record. `verify_chain` spans
Patient → … → Event → Workflow → Graph → **Analytics**. No analytics exists outside
the registry. Shares the single `ml.lineage.LineageTracker` and the shared
`ImmutableAuditLog`.

## Quick start
```python
from backend.operational_analytics import OperationalAnalyticsService

oa = OperationalAnalyticsService(lineage_tracker=shared_tracker)
oa.load_sources(events=all_events, workflows=workflow_records,
                graph_registry=graph.registry, temporal_analytics=temporal)
records = oa.build_all()                 # 6 dimensions + operational summary
assert oa.validate(records["health"]).ok
```

Run the tests: `pytest tests/test_operational_analytics.py`.
See [`docs/V3_P5_OPERATIONAL_ANALYTICS.md`](./docs/V3_P5_OPERATIONAL_ANALYTICS.md).

## Scope guard (NOT built — NR-13)
No operational recommendations (V3-P6), no dashboards, no operational workstation,
no realtime/autonomous actions, no FHIR/HL7/EMR, no V4 features.
