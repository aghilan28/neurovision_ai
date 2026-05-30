# V3-P5 — Operational Analytics Layer (design notes)

> **Phase:** V3-P5 · **Subsystem:** `backend/operational_analytics/` · **ADR:** ADR-0009

## Purpose
Give the platform **operational intelligence** — the ability to understand
behavior, performance, quality, trends, risk, and health — as **derived
intelligence** that is never a source of truth.

## Domain model
- **AnalyticsIdentity** (`identity/`) — content-addressed `analytics+{hash16}`,
  derived from `(category, scope)`; stable across re-derivation.
- **AnalyticsCategory** (`models/categories.py`) — closed vocabulary: `metrics`,
  `health`, `performance`, `quality`, `trend`, `risk`, `operational`.
- **AnalyticsMetric** — name/value/unit/observed + `dimension`, `explanation`,
  `inputs`. Every metric is explainable; unobserved metrics carry a sentinel.
- **AnalyticsRecord** — a first-class derived artifact: category + scope + subject +
  metrics + `sources` (the upstream refs it derived from) + version/lineage/audit.
- **AnalyticsAuditRecord / AnalyticsVersion / AnalyticsLineageRecord /
  AnalyticsRegistryRecord** — governance bookkeeping projections.

## Source view
`AnalyticsSourceView` is the single read-only, deterministically-ordered bundle over
events (via the V3-P2 `EventSourceView`), workflows, the graph registry, and
temporal analytics. It also exposes upstream **lineage ids** so analytics lineage
nodes are parented by the artifacts they summarize.

## Engines (all deterministic, read-only)
1. **Metrics** — counts (events, workflows, graph nodes/edges, per-category),
   rates/distributions, throughput/velocity (from workflow metrics), durations
   (from temporal analytics, logical steps), coverage.
2. **Health** — explainable [0,1] composites: case/review/workflow/knowledge/graph,
   plus `operational_health` and a data-gated `system_health_score`.
3. **Performance** — completion/transition/workflow/review performance, operational
   efficiency, latency + velocity (logical steps).
4. **Quality** — workflow/review/finding/knowledge quality + graph integrity
   (edges reference registered endpoints) + analytics integrity (sources are
   lineage-traceable).
5. **Trend** — earlier-vs-later logical halves of the ordered event stream produce a
   signed slope in [-1,1] with a `rising/falling/flat` explanation, for
   temporal/workflow/review/finding/knowledge/operational trends.
6. **Risk** — workflow/operational/quality/knowledge/dependency/bottleneck **risk
   scores** in [0,1] (higher = more risk). **No recommendations** — risks only.

## Governance path (per record)
gate (architecture = valid category; quality = bounded/explainable metrics; context
= has lineage parents; **risk = derived from upstream sources**) → shared lineage
node (parents = upstream event/workflow/graph/temporal nodes) → immutable audit
(`analytics_created` → `version_changed` → `analytics_registered`) →
content-addressed version → registry sync.

## Traceability
Because lineage parents are the upstream nodes (which already reach the patient),
`verify_chain(analytics.lineage_id)` spans
`Patient → Case → Review → Finding → Knowledge → Decision → Event → Timeline →
Workflow → Graph → Analytics`.

## Determinism (NR-9/NR-10)
No wall-clock, no randomness. Durations/latencies are logical steps; trends use
logical halves. Identical inputs reproduce identical analytics ids, versions, and
audit heads.

## Scope guard (NR-13)
No recommendations (V3-P6), dashboards, workstation, realtime/autonomous actions,
FHIR/HL7/EMR, or V4 features.
