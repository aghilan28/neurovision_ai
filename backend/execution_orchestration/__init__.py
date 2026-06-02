"""``backend/execution_orchestration`` — Execution Orchestration Layer (V4-P6).

Introduces **Execution as a governed first-class entity** — the *governed
progression of approved work*. Execution is **not** autonomous action, self-directed
operation, or agent freedom: it does not bypass policy or governance, coordinates
already-approved artifacts deterministically, and never performs autonomous planning.

Every execution is versioned, traceable, auditable, lineage-tracked, governed,
deterministic, and recoverable. An execution moves through a governed lifecycle
(PROPOSED -> QUEUED -> AUTHORIZED -> ACTIVE -> {PAUSED, BLOCKED, COMPLETED,
TERMINATED} -> ARCHIVED); forbidden transitions are blocked, and an execution cannot
become ACTIVE without authorization (policy-governed). **Every execution references
an approved agent assignment** (Agent <-> Execution integration); coordination binds
the approved goal/plan/task/agent/assignment it progresses. **Monitoring observes
execution; it never modifies it** (a deterministic, state-derived status snapshot).
Shares the platform's single ``ml.lineage.LineageTracker`` and the shared
``ImmutableAuditLog`` — no parallel lineage/audit/governance.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and
sibling ``backend`` subsystems; never imports ``frontend``. Scope is strictly V4-P6
— no autonomous action, no autonomous planning, no simulation/scenario engines. See
``.gcc/decisions/ADR-0013``.
"""

from __future__ import annotations

from .version import (
    EXECUTION_ORCHESTRATION_VERSION, EXECUTION_DOMAIN_VERSION, EXECUTION_IDENTITY_VERSION,
    EXECUTION_LIFECYCLE_VERSION, EXECUTION_CONTEXT_VERSION, EXECUTION_STATUS_VERSION,
    EXECUTION_RELATIONSHIP_VERSION, EXECUTION_GOVERNANCE_VERSION, EXECUTION_REGISTRY_VERSION,
    EXECUTION_AUDIT_VERSION, EXECUTION_LINEAGE_VERSION, EXECUTION_MONITORING_VERSION,
    EXECUTION_VALIDATION_VERSION, EXECUTION_REPORT_VERSION,
)
from .identity import (
    ExecutionIdentity, ExecutionIdentityError, mint_execution, mint_relationship,
    validate_identity, validate_relationship_identity,
)
from .lifecycle import (
    ExecutionLifecycleState, ExecutionLifecycle, ExecutionLifecycleError,
    ExecutionTransitionRecord, EXECUTION_TRANSITIONS, GOVERNED_TRANSITIONS,
)
from .models import (
    ExecutionMetadata, ExecutionContext, ExecutionStatus, ExecutionAssignment, ExecutionVersion,
    ExecutionAuditRecord, ExecutionRelationship, ExecutionGovernanceRecord,
    ExecutionLineageRecord, ExecutionRegistryRecord, ExecutionRecord,
)
from .coordination import context_complete, assignment_consistent, coordination_summary
from .monitoring import observe, monitoring_summary
from .governance import ExecutionGovernanceGate, ExecutionGovernanceError
from .registry import ExecutionRegistry
from .validation import ExecutionValidator
from .audit import make_execution_audit_log
from .service import ExecutionService, ExecutionCoordinationError

__all__ = [
    "EXECUTION_ORCHESTRATION_VERSION", "EXECUTION_DOMAIN_VERSION", "EXECUTION_IDENTITY_VERSION",
    "EXECUTION_LIFECYCLE_VERSION", "EXECUTION_CONTEXT_VERSION", "EXECUTION_STATUS_VERSION",
    "EXECUTION_RELATIONSHIP_VERSION", "EXECUTION_GOVERNANCE_VERSION", "EXECUTION_REGISTRY_VERSION",
    "EXECUTION_AUDIT_VERSION", "EXECUTION_LINEAGE_VERSION", "EXECUTION_MONITORING_VERSION",
    "EXECUTION_VALIDATION_VERSION", "EXECUTION_REPORT_VERSION",
    "ExecutionIdentity", "ExecutionIdentityError", "mint_execution", "mint_relationship",
    "validate_identity", "validate_relationship_identity",
    "ExecutionLifecycleState", "ExecutionLifecycle", "ExecutionLifecycleError",
    "ExecutionTransitionRecord", "EXECUTION_TRANSITIONS", "GOVERNED_TRANSITIONS",
    "ExecutionMetadata", "ExecutionContext", "ExecutionStatus", "ExecutionAssignment",
    "ExecutionVersion", "ExecutionAuditRecord", "ExecutionRelationship",
    "ExecutionGovernanceRecord", "ExecutionLineageRecord", "ExecutionRegistryRecord",
    "ExecutionRecord", "context_complete", "assignment_consistent", "coordination_summary",
    "observe", "monitoring_summary", "ExecutionGovernanceGate", "ExecutionGovernanceError",
    "ExecutionRegistry", "ExecutionValidator", "make_execution_audit_log", "ExecutionService",
    "ExecutionCoordinationError",
]
