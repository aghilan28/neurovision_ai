"""Version identities for the Planning Foundation (V4-P3).

Every plan artifact records the versions that produced it, so it is reproducible and
auditable for its whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).

A **Plan** is the bridge between a Goal and Tasks: it defines *how an approved goal
may be achieved*. It is an **intent structure**, not an execution structure. A plan
never executes, never completes work, and never performs autonomous action. Plans
are computed and governed deterministically (no wall-clock); a plan only becomes
READY through policy-governed approval (V4-P2 integration), and every plan derives
from an APPROVED goal.
"""

from __future__ import annotations

PLANNING_FOUNDATION_VERSION: str = "planning-foundation@1.0.0"

PLAN_DOMAIN_VERSION: str = "plan-domain@1.0.0"
PLAN_IDENTITY_VERSION: str = "plan-identity@1.0.0"
PLAN_TAXONOMY_VERSION: str = "plan-taxonomy@1.0.0"
PLAN_LIFECYCLE_VERSION: str = "plan-lifecycle@1.0.0"
PLAN_RELATIONSHIP_VERSION: str = "plan-relationship@1.0.0"
PLAN_GOVERNANCE_VERSION: str = "plan-governance@1.0.0"
PLAN_REGISTRY_VERSION: str = "plan-registry@1.0.0"
PLAN_AUDIT_VERSION: str = "plan-audit@1.0.0"
PLAN_LINEAGE_VERSION: str = "plan-lineage@1.0.0"
PLAN_VALIDATION_VERSION: str = "plan-validation@1.0.0"
PLAN_REPORT_VERSION: str = "plan-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
