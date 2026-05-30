"""Version identities for the Governance Intelligence Layer (V4-P7).

Every governance-intelligence artifact records the versions that produced it, so it
is reproducible and auditable for its whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).

Governance intelligence makes governance **observable, analyzable, auditable, and
explainable**. It creates *intelligence about governance* — it does **not** create
new governance rules, modify governance state, or bypass policy/approval workflows.
It is derived deterministically (no wall-clock) from already-governed artifacts
(goals, policies, constraints, plans, tasks, agents, executions); every governance
metric/risk/violation/escalation it surfaces traces, through lineage, back to those
artifacts and onward to the patient.
"""

from __future__ import annotations

GOVERNANCE_INTELLIGENCE_VERSION: str = "governance-intelligence@1.0.0"

GOVERNANCE_DOMAIN_VERSION: str = "governance-intel-domain@1.0.0"
GOVERNANCE_IDENTITY_VERSION: str = "governance-intel-identity@1.0.0"
GOVERNANCE_OBSERVATION_VERSION: str = "governance-intel-observation@1.0.0"
GOVERNANCE_APPROVAL_VERSION: str = "governance-intel-approval@1.0.0"
GOVERNANCE_VIOLATION_VERSION: str = "governance-intel-violation@1.0.0"
GOVERNANCE_ESCALATION_VERSION: str = "governance-intel-escalation@1.0.0"
GOVERNANCE_RISK_VERSION: str = "governance-intel-risk@1.0.0"
GOVERNANCE_ANALYTICS_VERSION: str = "governance-intel-analytics@1.0.0"
GOVERNANCE_METRIC_VERSION: str = "governance-intel-metric@1.0.0"
GOVERNANCE_GOVERNANCE_VERSION: str = "governance-intel-governance@1.0.0"
GOVERNANCE_REGISTRY_VERSION: str = "governance-intel-registry@1.0.0"
GOVERNANCE_AUDIT_VERSION: str = "governance-intel-audit@1.0.0"
GOVERNANCE_LINEAGE_VERSION: str = "governance-intel-lineage@1.0.0"
GOVERNANCE_VALIDATION_VERSION: str = "governance-intel-validation@1.0.0"
GOVERNANCE_REPORT_VERSION: str = "governance-intel-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
