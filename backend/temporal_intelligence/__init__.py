"""``backend/temporal_intelligence`` — Temporal Intelligence Layer (V3-P2).

Teaches the platform about **time**. Version 2 understood current state; Version 3
understands state *evolution, history, progression, temporal context*, and
*operational timelines*.

It produces four temporal artifact families, all derived strictly **from events**
(V3-P1) — never by reconstructing hidden state:

* **Timelines** — the deterministically-ordered event sequence for a subject
  (patient/case/review/finding/knowledge/decision/operational).
* **Histories** — the reconstructed change-log of a subject.
* **Evolution records** — the ordered state transitions of a subject.
* **Temporal analytics** — duration/timing metrics in deterministic *logical steps*
  (the platform forbids wall-clock, so durations are reproducible event-count spans).

Plus **visualization-ready contracts** (no UI implementation) for timelines, event
sequences, evolution graphs, duration/trend graphs, and a future operational
dashboard.

Every artifact is versioned, traceable, auditable, lineage-tracked, reproducible,
deterministic, and governed. Lineage parents are the **event** nodes the artifact
derives from, so ``verify_chain`` spans Patient → ... → Event → Temporal artifact.
The subsystem shares the platform's single ``ml.lineage.LineageTracker`` and the
shared ``ImmutableAuditLog``; it creates no parallel registry for existing entities.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and the
sibling subsystems (operational_events) it derives from; never imports ``frontend``.
Scope is strictly V3-P2 — no knowledge graph, no operational analytics/
recommendations/dashboards (only viz *contracts*), no FHIR/HL7/EMR, no realtime, no
V4. See ``.gcc/decisions/ADR-0007``.
"""

from __future__ import annotations

from .version import (
    TEMPORAL_INTELLIGENCE_VERSION, TEMPORAL_DOMAIN_VERSION, TEMPORAL_IDENTITY_VERSION,
    TEMPORAL_TIMELINE_VERSION, TEMPORAL_HISTORY_VERSION, TEMPORAL_EVOLUTION_VERSION,
    TEMPORAL_ANALYTICS_VERSION, TEMPORAL_REGISTRY_VERSION, TEMPORAL_AUDIT_VERSION,
    TEMPORAL_LINEAGE_VERSION, TEMPORAL_VALIDATION_VERSION, TEMPORAL_REPORT_VERSION,
    TEMPORAL_VIZ_VERSION,
)
from .identity import (
    TemporalIdentity, TemporalIdentityError, mint_timeline, mint_history, mint_evolution,
    mint_analytics, mint_report, validate_identity,
)
from .models import (
    TimelinePoint, Timeline, HistoryEntry, History, EvolutionStep, EvolutionRecord,
    DurationMetric, TemporalAnalytics, VisualizationContract,
    TemporalAuditRecord, TemporalVersion, TemporalRegistryRecord,
)
from .timelines import EventSourceView, TimelineEngine
from .history import HistoryEngine
from .evolution import EvolutionEngine
from .analytics import TemporalAnalyticsEngine
from .audit import make_temporal_audit_log
from .registry import TemporalRegistry
from .validation import TemporalGovernanceGate, TemporalValidator, TemporalValidationError
from .service import TemporalIntelligenceService

__all__ = [
    "TEMPORAL_INTELLIGENCE_VERSION", "TEMPORAL_DOMAIN_VERSION", "TEMPORAL_IDENTITY_VERSION",
    "TEMPORAL_TIMELINE_VERSION", "TEMPORAL_HISTORY_VERSION", "TEMPORAL_EVOLUTION_VERSION",
    "TEMPORAL_ANALYTICS_VERSION", "TEMPORAL_REGISTRY_VERSION", "TEMPORAL_AUDIT_VERSION",
    "TEMPORAL_LINEAGE_VERSION", "TEMPORAL_VALIDATION_VERSION", "TEMPORAL_REPORT_VERSION",
    "TEMPORAL_VIZ_VERSION",
    "TemporalIdentity", "TemporalIdentityError", "mint_timeline", "mint_history",
    "mint_evolution", "mint_analytics", "mint_report", "validate_identity",
    "TimelinePoint", "Timeline", "HistoryEntry", "History", "EvolutionStep", "EvolutionRecord",
    "DurationMetric", "TemporalAnalytics", "VisualizationContract",
    "TemporalAuditRecord", "TemporalVersion", "TemporalRegistryRecord",
    "EventSourceView", "TimelineEngine", "HistoryEngine", "EvolutionEngine",
    "TemporalAnalyticsEngine", "make_temporal_audit_log", "TemporalRegistry",
    "TemporalGovernanceGate", "TemporalValidator", "TemporalValidationError",
    "TemporalIntelligenceService",
]
