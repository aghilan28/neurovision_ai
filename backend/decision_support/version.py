"""Version identities for the Decision Support Layer (V2-P6).

Every decision-support artifact (context, evidence bundle, risk context,
prioritization, guidance, decision-support record, report) records the versions
that produced it, so it is reproducible and auditable for its whole lifetime
(AP-5/AP-6/AP-9, NR-10/NR-11).
"""

from __future__ import annotations

DECISION_SUPPORT_VERSION: str = "decision-support@1.0.0"

DECISION_DOMAIN_VERSION: str = "decision-domain@1.0.0"
DECISION_IDENTITY_VERSION: str = "decision-identity@1.0.0"
DECISION_CONTEXT_VERSION: str = "decision-context@1.0.0"
DECISION_EVIDENCE_VERSION: str = "decision-evidence@1.0.0"
DECISION_RISK_VERSION: str = "decision-risk@1.0.0"
DECISION_PRIORITIZATION_VERSION: str = "decision-prioritization@1.0.0"
DECISION_GUIDANCE_VERSION: str = "decision-guidance@1.0.0"
DECISION_REGISTRY_VERSION: str = "decision-registry@1.0.0"
DECISION_AUDIT_VERSION: str = "decision-audit@1.0.0"
DECISION_LINEAGE_VERSION: str = "decision-lineage@1.0.0"
DECISION_VALIDATION_VERSION: str = "decision-validation@1.0.0"
DECISION_REPORT_VERSION: str = "decision-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
