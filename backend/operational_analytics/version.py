"""Version identities for the Operational Analytics Layer (V3-P5).

Every analytics artifact records the versions that produced it, so it is
reproducible and auditable for its whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).

Operational analytics is **derived intelligence**: it is computed strictly from
already-governed artifacts — events (V3-P1), temporal intelligence (V3-P2),
workflows (V3-P3) and the operational graph (V3-P4) — and ordered by the events'
deterministic logical clock, so it never depends on wall-clock time and never
becomes a source of truth.
"""

from __future__ import annotations

OPERATIONAL_ANALYTICS_VERSION: str = "operational-analytics@1.0.0"

ANALYTICS_DOMAIN_VERSION: str = "analytics-domain@1.0.0"
ANALYTICS_IDENTITY_VERSION: str = "analytics-identity@1.0.0"
ANALYTICS_METRIC_VERSION: str = "analytics-metric@1.0.0"
ANALYTICS_CATEGORY_VERSION: str = "analytics-category@1.0.0"
ANALYTICS_METRICS_ENGINE_VERSION: str = "analytics-metrics-engine@1.0.0"
ANALYTICS_HEALTH_ENGINE_VERSION: str = "analytics-health-engine@1.0.0"
ANALYTICS_PERFORMANCE_ENGINE_VERSION: str = "analytics-performance-engine@1.0.0"
ANALYTICS_QUALITY_ENGINE_VERSION: str = "analytics-quality-engine@1.0.0"
ANALYTICS_TREND_ENGINE_VERSION: str = "analytics-trend-engine@1.0.0"
ANALYTICS_RISK_ENGINE_VERSION: str = "analytics-risk-engine@1.0.0"
ANALYTICS_REGISTRY_VERSION: str = "analytics-registry@1.0.0"
ANALYTICS_AUDIT_VERSION: str = "analytics-audit@1.0.0"
ANALYTICS_LINEAGE_VERSION: str = "analytics-lineage@1.0.0"
ANALYTICS_VALIDATION_VERSION: str = "analytics-validation@1.0.0"
ANALYTICS_REPORT_VERSION: str = "analytics-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
