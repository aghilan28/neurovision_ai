"""Version identities for the Policy & Constraint Engine (V4-P2).

Every policy artifact records the versions that produced it, so it is reproducible
and auditable for its whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).

Policies are the **safety system** of Version 4: they make explicit what is
ALLOWED / FORBIDDEN / REQUIRED / ESCALATED before any planning or execution can ever
exist. Every policy and every evaluation is deterministic and **explainable** —
policies never contain hidden logic and always produce an explainable outcome.
"""

from __future__ import annotations

POLICY_ENGINE_VERSION: str = "policy-engine@1.0.0"

POLICY_DOMAIN_VERSION: str = "policy-domain@1.0.0"
POLICY_IDENTITY_VERSION: str = "policy-identity@1.0.0"
POLICY_TAXONOMY_VERSION: str = "policy-taxonomy@1.0.0"
POLICY_RULE_VERSION: str = "policy-rule@1.0.0"
CONSTRAINT_VERSION: str = "policy-constraint@1.0.0"
POLICY_EVALUATION_VERSION: str = "policy-evaluation@1.0.0"
POLICY_GOVERNANCE_VERSION: str = "policy-governance@1.0.0"
POLICY_REGISTRY_VERSION: str = "policy-registry@1.0.0"
POLICY_AUDIT_VERSION: str = "policy-audit@1.0.0"
POLICY_LINEAGE_VERSION: str = "policy-lineage@1.0.0"
POLICY_VALIDATION_VERSION: str = "policy-validation@1.0.0"
POLICY_REPORT_VERSION: str = "policy-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
