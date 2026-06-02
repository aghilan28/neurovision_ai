"""Version identities for the Temporal Intelligence Layer (V3-P2).

Every temporal artifact (timeline, history, evolution record, analytics, report)
records the versions that produced it, so it is reproducible and auditable for its
whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).

Temporal intelligence is derived **from events** (V3-P1) — never by reconstructing
hidden state — and ordered by the events' deterministic logical clock, so it never
depends on wall-clock time.
"""

from __future__ import annotations

TEMPORAL_INTELLIGENCE_VERSION: str = "temporal-intelligence@1.0.0"

TEMPORAL_DOMAIN_VERSION: str = "temporal-domain@1.0.0"
TEMPORAL_IDENTITY_VERSION: str = "temporal-identity@1.0.0"
TEMPORAL_TIMELINE_VERSION: str = "temporal-timeline@1.0.0"
TEMPORAL_HISTORY_VERSION: str = "temporal-history@1.0.0"
TEMPORAL_EVOLUTION_VERSION: str = "temporal-evolution@1.0.0"
TEMPORAL_ANALYTICS_VERSION: str = "temporal-analytics@1.0.0"
TEMPORAL_REGISTRY_VERSION: str = "temporal-registry@1.0.0"
TEMPORAL_AUDIT_VERSION: str = "temporal-audit@1.0.0"
TEMPORAL_LINEAGE_VERSION: str = "temporal-lineage@1.0.0"
TEMPORAL_VALIDATION_VERSION: str = "temporal-validation@1.0.0"
TEMPORAL_REPORT_VERSION: str = "temporal-report@1.0.0"
TEMPORAL_VIZ_VERSION: str = "temporal-viz@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
