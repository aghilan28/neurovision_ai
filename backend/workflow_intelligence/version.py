"""Version identities for the Workflow Intelligence Layer (V3-P3).

Every workflow artifact records the versions that produced it, so it is
reproducible and auditable for its whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).

Workflow intelligence is derived **from events (V3-P1) and temporal intelligence
(V3-P2)** — never from hidden workflow state — and ordered by the events'
deterministic logical clock, so it never depends on wall-clock time.
"""

from __future__ import annotations

WORKFLOW_INTELLIGENCE_VERSION: str = "workflow-intelligence@1.0.0"

WORKFLOW_DOMAIN_VERSION: str = "workflow-domain@1.0.0"
WORKFLOW_IDENTITY_VERSION: str = "workflow-identity@1.0.0"
WORKFLOW_TRANSITION_VERSION: str = "workflow-transition@1.0.0"
WORKFLOW_DEPENDENCY_VERSION: str = "workflow-dependency@1.0.0"
WORKFLOW_METRIC_VERSION: str = "workflow-metric@1.0.0"
WORKFLOW_REGISTRY_VERSION: str = "workflow-registry@1.0.0"
WORKFLOW_AUDIT_VERSION: str = "workflow-audit@1.0.0"
WORKFLOW_LINEAGE_VERSION: str = "workflow-lineage@1.0.0"
WORKFLOW_VALIDATION_VERSION: str = "workflow-validation@1.0.0"
WORKFLOW_REPORT_VERSION: str = "workflow-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
