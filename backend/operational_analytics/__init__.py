"""``backend/operational_analytics`` — Operational Analytics Layer (V3-P5).

Creates platform-wide **operational intelligence**: the ability to understand
operational behavior, performance, quality, trends, risks, and system health. This
phase creates **intelligence only** — not recommendations, not actions, not
dashboards (those are out of scope; recommendations are V3-P6).

All analytics is **derived intelligence**: it is computed strictly from the
already-governed upstream artifacts — events (V3-P1), temporal intelligence
(V3-P2), workflows (V3-P3) and the operational graph (V3-P4). Analytics never
becomes a source of truth. Every analytics artifact is versioned, traceable,
auditable, lineage-tracked, deterministic, and governed; its lineage parents are
the upstream nodes it summarizes, so ``verify_chain`` spans Patient -> ... -> Event
-> Workflow -> Graph -> Analytics. Shares the platform's single
``ml.lineage.LineageTracker`` and the shared ``ImmutableAuditLog`` — no parallel
lineage/audit.

Engines: metrics (counts/rates/distributions/coverage/throughput/velocity), health
(explainable [0,1] health scores), performance (completion/transition/workflow/
review performance, latency + velocity in logical steps), quality (workflow/review/
finding/knowledge quality + graph/analytics integrity), trend (temporal/workflow/
review/finding/knowledge/operational trends derived from the ordered event stream),
and risk (workflow/operational/quality/knowledge/dependency/bottleneck risk scores).

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and the
sibling V3 subsystems it derives from; never imports ``frontend``. Scope is strictly
V3-P5 — no recommendations, no dashboards, no realtime, no FHIR/HL7/EMR, no V4. See
``.gcc/decisions/ADR-0009``.
"""

from __future__ import annotations

from .version import (
    OPERATIONAL_ANALYTICS_VERSION, ANALYTICS_DOMAIN_VERSION, ANALYTICS_IDENTITY_VERSION,
    ANALYTICS_METRIC_VERSION, ANALYTICS_CATEGORY_VERSION, ANALYTICS_REGISTRY_VERSION,
    ANALYTICS_AUDIT_VERSION, ANALYTICS_LINEAGE_VERSION, ANALYTICS_VALIDATION_VERSION,
    ANALYTICS_REPORT_VERSION,
)
from .identity import (
    AnalyticsIdentity, AnalyticsIdentityError, mint_analytics, validate_identity,
)
from .models import (
    AnalyticsCategory, AnalyticsCategoryError, is_category, validate_category, categories,
    AnalyticsMetric, AnalyticsSourceRef, AnalyticsRecord,
    AnalyticsAuditRecord, AnalyticsVersion, AnalyticsLineageRecord, AnalyticsRegistryRecord,
)
from .models.source import AnalyticsSourceView
from .metrics import MetricsEngine
from .health import HealthEngine
from .performance import PerformanceEngine
from .quality import QualityEngine
from .trends import TrendEngine
from .risk import RiskEngine
from .engine import AnalyticsBuilder
from .audit import make_analytics_audit_log
from .registry import AnalyticsRegistry
from .validation import AnalyticsGovernanceGate, AnalyticsValidator, AnalyticsValidationError
from .service import OperationalAnalyticsService

__all__ = [
    "OPERATIONAL_ANALYTICS_VERSION", "ANALYTICS_DOMAIN_VERSION", "ANALYTICS_IDENTITY_VERSION",
    "ANALYTICS_METRIC_VERSION", "ANALYTICS_CATEGORY_VERSION", "ANALYTICS_REGISTRY_VERSION",
    "ANALYTICS_AUDIT_VERSION", "ANALYTICS_LINEAGE_VERSION", "ANALYTICS_VALIDATION_VERSION",
    "ANALYTICS_REPORT_VERSION",
    "AnalyticsIdentity", "AnalyticsIdentityError", "mint_analytics", "validate_identity",
    "AnalyticsCategory", "AnalyticsCategoryError", "is_category", "validate_category", "categories",
    "AnalyticsMetric", "AnalyticsSourceRef", "AnalyticsRecord", "AnalyticsAuditRecord",
    "AnalyticsVersion", "AnalyticsLineageRecord", "AnalyticsRegistryRecord", "AnalyticsSourceView",
    "MetricsEngine", "HealthEngine", "PerformanceEngine", "QualityEngine", "TrendEngine",
    "RiskEngine", "AnalyticsBuilder", "make_analytics_audit_log", "AnalyticsRegistry",
    "AnalyticsGovernanceGate", "AnalyticsValidator", "AnalyticsValidationError",
    "OperationalAnalyticsService",
]
