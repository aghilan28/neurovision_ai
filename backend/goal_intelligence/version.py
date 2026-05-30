"""Version identities for the Goal Intelligence Foundation (V4-P1).

Every goal artifact records the versions that produced it, so it is reproducible and
auditable for its whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).

A **Goal** is *intent* — a desired outcome. It is **not** a recommendation, a task,
a plan, or execution. Goals never directly perform actions. They are computed and
governed deterministically (no wall-clock), and an ACTIVE goal must be policy
governed (V4-P2 integration).
"""

from __future__ import annotations

GOAL_INTELLIGENCE_VERSION: str = "goal-intelligence@1.0.0"

GOAL_DOMAIN_VERSION: str = "goal-domain@1.0.0"
GOAL_IDENTITY_VERSION: str = "goal-identity@1.0.0"
GOAL_TAXONOMY_VERSION: str = "goal-taxonomy@1.0.0"
GOAL_LIFECYCLE_VERSION: str = "goal-lifecycle@1.0.0"
GOAL_RELATIONSHIP_VERSION: str = "goal-relationship@1.0.0"
GOAL_GOVERNANCE_VERSION: str = "goal-governance@1.0.0"
GOAL_REGISTRY_VERSION: str = "goal-registry@1.0.0"
GOAL_AUDIT_VERSION: str = "goal-audit@1.0.0"
GOAL_LINEAGE_VERSION: str = "goal-lineage@1.0.0"
GOAL_VALIDATION_VERSION: str = "goal-validation@1.0.0"
GOAL_REPORT_VERSION: str = "goal-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
