"""Version identities for the Task Intelligence Layer (V4-P4).

Every task artifact records the versions that produced it, so it is reproducible and
auditable for its whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).

A **Task** is a first-class governed unit of work — the atomic unit of *future*
execution. A Task **defines work; it does not perform work**. It is not an agent, an
execution, a job, or a process. Tasks are computed and governed deterministically (no
wall-clock); a task only becomes READY through policy-governed approval (V4-P2
integration), and every task derives from a READY plan (V4-P3 integration).
"""

from __future__ import annotations

TASK_INTELLIGENCE_VERSION: str = "task-intelligence@1.0.0"

TASK_DOMAIN_VERSION: str = "task-domain@1.0.0"
TASK_IDENTITY_VERSION: str = "task-identity@1.0.0"
TASK_TAXONOMY_VERSION: str = "task-taxonomy@1.0.0"
TASK_LIFECYCLE_VERSION: str = "task-lifecycle@1.0.0"
TASK_RELATIONSHIP_VERSION: str = "task-relationship@1.0.0"
TASK_GOVERNANCE_VERSION: str = "task-governance@1.0.0"
TASK_REGISTRY_VERSION: str = "task-registry@1.0.0"
TASK_AUDIT_VERSION: str = "task-audit@1.0.0"
TASK_LINEAGE_VERSION: str = "task-lineage@1.0.0"
TASK_VALIDATION_VERSION: str = "task-validation@1.0.0"
TASK_REPORT_VERSION: str = "task-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
