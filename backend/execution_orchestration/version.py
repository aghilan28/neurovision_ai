"""Version identities for the Execution Orchestration Layer (V4-P6).

Every execution artifact records the versions that produced it, so it is reproducible
and auditable for its whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).

An **Execution** is a first-class *governed* entity representing the **governed
progression of approved work**. Execution is **not** autonomous action,
self-directed operation, or agent freedom: it does not bypass policy or governance,
it coordinates already-approved artifacts deterministically, and it never performs
autonomous planning. An execution only becomes ACTIVE through authorization
(policy-governed), references an approved agent assignment, and is observed by
monitoring (which never modifies it).
"""

from __future__ import annotations

EXECUTION_ORCHESTRATION_VERSION: str = "execution-orchestration@1.0.0"

EXECUTION_DOMAIN_VERSION: str = "execution-domain@1.0.0"
EXECUTION_IDENTITY_VERSION: str = "execution-identity@1.0.0"
EXECUTION_LIFECYCLE_VERSION: str = "execution-lifecycle@1.0.0"
EXECUTION_CONTEXT_VERSION: str = "execution-context@1.0.0"
EXECUTION_STATUS_VERSION: str = "execution-status@1.0.0"
EXECUTION_RELATIONSHIP_VERSION: str = "execution-relationship@1.0.0"
EXECUTION_GOVERNANCE_VERSION: str = "execution-governance@1.0.0"
EXECUTION_REGISTRY_VERSION: str = "execution-registry@1.0.0"
EXECUTION_AUDIT_VERSION: str = "execution-audit@1.0.0"
EXECUTION_LINEAGE_VERSION: str = "execution-lineage@1.0.0"
EXECUTION_MONITORING_VERSION: str = "execution-monitoring@1.0.0"
EXECUTION_VALIDATION_VERSION: str = "execution-validation@1.0.0"
EXECUTION_REPORT_VERSION: str = "execution-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
