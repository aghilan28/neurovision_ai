"""Version identities for the Operational Recommendation Layer (V3-P6).

Every recommendation artifact records the versions that produced it, so it is
reproducible and auditable for its whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).

Recommendations are **explainable, evidence-linked, analytics-linked** outputs
derived strictly from operational/workflow/system intelligence — never from
clinical data. They are computed deterministically and never executed
autonomously, so they never depend on wall-clock time and never take action.
"""

from __future__ import annotations

OPERATIONAL_RECOMMENDATIONS_VERSION: str = "operational-recommendations@1.0.0"

RECOMMENDATION_DOMAIN_VERSION: str = "recommendation-domain@1.0.0"
RECOMMENDATION_IDENTITY_VERSION: str = "recommendation-identity@1.0.0"
RECOMMENDATION_CONTEXT_VERSION: str = "recommendation-context@1.0.0"
RECOMMENDATION_EVIDENCE_VERSION: str = "recommendation-evidence@1.0.0"
RECOMMENDATION_PRIORITY_VERSION: str = "recommendation-priority@1.0.0"
RECOMMENDATION_CONTEXT_ENGINE_VERSION: str = "recommendation-context-engine@1.0.0"
RECOMMENDATION_GUIDANCE_ENGINE_VERSION: str = "recommendation-guidance-engine@1.0.0"
RECOMMENDATION_PRIORITIZATION_ENGINE_VERSION: str = "recommendation-prioritization-engine@1.0.0"
RECOMMENDATION_OPTIMIZATION_ENGINE_VERSION: str = "recommendation-optimization-engine@1.0.0"
RECOMMENDATION_ESCALATION_ENGINE_VERSION: str = "recommendation-escalation-engine@1.0.0"
RECOMMENDATION_REGISTRY_VERSION: str = "recommendation-registry@1.0.0"
RECOMMENDATION_AUDIT_VERSION: str = "recommendation-audit@1.0.0"
RECOMMENDATION_LINEAGE_VERSION: str = "recommendation-lineage@1.0.0"
RECOMMENDATION_VALIDATION_VERSION: str = "recommendation-validation@1.0.0"
RECOMMENDATION_REPORT_VERSION: str = "recommendation-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
