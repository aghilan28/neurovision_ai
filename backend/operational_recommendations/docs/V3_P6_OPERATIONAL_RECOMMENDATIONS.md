# V3-P6 — Operational Recommendation Layer (design notes)

> **Phase:** V3-P6 · **Subsystem:** `backend/operational_recommendations/` · **ADR:** ADR-0009

## Purpose
Turn derived operational intelligence (V3-P5) into **explainable operational
recommendations** — guidance, prioritization, optimization suggestions, and
escalation candidates. Strictly operational; never clinical.

## Domain model
- **RecommendationIdentity** (`identity/`) — content-addressed
  `recommendation+{hash16}`, derived from `(kind, scope)`.
- **RecommendationKind / PriorityLevel** (`models/kinds.py`) — closed vocabularies:
  kinds `guidance|prioritization|optimization|escalation`; priorities
  `low|medium|high|critical` with a fixed rank.
- **RecommendationEvidence** — a reference to a real upstream artifact (analytics
  metric / workflow / graph node / event) with the cited `metric_name` + `value`
  and its `lineage_id`. No recommendation exists without evidence.
- **RecommendationContext** — a deterministic bundle aggregating analytics /
  workflow / graph / temporal / risk / health context (a derived view).
- **RecommendationPriority** — level + [0,1] score + reason + supporting
  metrics/risks/trends/workflow signals (explainable).
- **RecommendationRecord** — kind + scope + subject + `statement` + priority +
  evidence + `context_id` + `analytics_ids`/`workflow_ids`/`graph_ids` + rationale.
- **RecommendationAuditRecord / Version / LineageRecord / RegistryRecord** —
  governance bookkeeping projections.

## Source view
`RecommendationSourceView` wraps the V3-P5 analytics records (indexed by category),
the V3-P3 workflows, and the V3-P4 graph registry, and exposes the upstream lineage
ids so recommendation lineage nodes are parented by the analytics they cite.

## Engines (all deterministic, read-only, no execution)
1. **Context** — aggregates per-dimension headline analytics, workflow/graph size +
   bottlenecks, temporal/risk/health signals into one `RecommendationContext`.
2. **Prioritization** — maps a [0,1] score to a level via fixed bands
   (≥0.75 critical, ≥0.5 high, ≥0.25 medium, else low) with an explainable reason
   and supporting signal lists.
3. **Guidance** — workflow / review-queue / escalation / operational /
   resource-awareness guidance, each citing analytics evidence.
4. **Optimization** — workflow / dependency / queue / process **suggestions** only.
5. **Escalation** — emits an escalation **candidate** per risk dimension at/above a
   fixed threshold (0.5), with reason + evidence + risk-context evidence + priority.
   No automatic escalation.

## Governance path (per recommendation)
gate (architecture = valid kind; quality = explainable statement/rationale/priority;
context = has lineage parents; **risk = evidence-linked AND analytics-linked**) →
shared lineage node (parents = the analytics lineage ids carried by the cited
evidence) → immutable audit (`recommendation_created` → `version_changed` →
`recommendation_registered`) → content-addressed version → registry sync. The
context is registered first so every recommendation links to a registered context.

## Traceability
Because lineage parents are the analytics nodes (which already reach the patient
through workflow/graph/event/temporal nodes),
`verify_chain(recommendation.lineage_id)` spans
`Patient → … → Event → Workflow → Graph → Analytics → Recommendation`.

## Determinism (NR-9/NR-10)
No wall-clock, no randomness. Scores derive from analytics metrics; priority banding
is fixed; identical inputs reproduce identical recommendation ids, versions, and
audit heads.

## Scope guard (NR-13)
No dashboards, workstation, realtime/autonomous execution, auto escalation, clinical
recommendations/diagnosis/treatment, FHIR/HL7/EMR, or V4 features.
