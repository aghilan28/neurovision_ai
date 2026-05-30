"""``backend/task_intelligence`` — Task Intelligence Layer (V4-P4).

Introduces **Tasks as first-class governed work entities** — the atomic units of
*future* execution. A Task **describes work; it does not perform work**. It is not an
agent, an execution, a job, or a process.

Every task is versioned, traceable, auditable, lineage-tracked, governed,
deterministic, and recoverable. A task moves through a governed lifecycle (PROPOSED
-> DRAFT -> UNDER_REVIEW -> APPROVED -> READY -> {BLOCKED, COMPLETED} -> ARCHIVED);
forbidden transitions are blocked, and a task cannot become READY without
policy-governed approval (V4-P2 integration). BLOCKED is a non-governed operational
dependency state. **Every task derives from a ready plan** (V4-P3 integration), so a
task traces back through the plan -> goal -> operational intelligence to the patient
via the platform's single ``ml.lineage.LineageTracker``; every change is recorded in
the shared ``ImmutableAuditLog`` — no parallel lineage/audit/governance systems.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and
sibling ``backend`` subsystems; never imports ``frontend``. Scope is strictly V4-P4
— no agents, execution, monitoring, simulation, or autonomous action. See
``.gcc/decisions/ADR-0012``.
"""

from __future__ import annotations

from .version import (
    TASK_INTELLIGENCE_VERSION, TASK_DOMAIN_VERSION, TASK_IDENTITY_VERSION,
    TASK_TAXONOMY_VERSION, TASK_LIFECYCLE_VERSION, TASK_RELATIONSHIP_VERSION,
    TASK_GOVERNANCE_VERSION, TASK_REGISTRY_VERSION, TASK_AUDIT_VERSION,
    TASK_LINEAGE_VERSION, TASK_VALIDATION_VERSION, TASK_REPORT_VERSION,
)
from .identity import (
    TaskIdentity, TaskIdentityError, mint_task, mint_relationship,
    validate_identity, validate_relationship_identity,
)
from .taxonomy import (
    TaskCategory, TaskPriority, TaskRelationType, TaxonomyError,
    TASK_CATEGORIES, TASK_PRIORITIES, TASK_RELATION_TYPES, RELATION_TARGET_KINDS,
    is_category, validate_category, parent_of, ancestry, is_priority, priority_rank,
    is_relation, validate_relation,
)
from .lifecycle import (
    TaskLifecycleState, TaskLifecycle, TaskLifecycleError, TaskTransitionRecord,
    TASK_TRANSITIONS, GOVERNED_TRANSITIONS,
)
from .models import (
    TaskMetadata, TaskConstraintReference, TaskVersion, TaskAuditRecord, TaskDependency,
    TaskRelationship, TaskGovernanceRecord, TaskLineageRecord, TaskRegistryRecord, TaskRecord,
)
from .governance import TaskGovernanceGate, TaskGovernanceError
from .registry import TaskRegistry
from .validation import TaskValidator
from .audit import make_task_audit_log
from .dependencies import has_cycle, topological_order, dependency_summary
from .service import TaskService, TaskDerivationError

__all__ = [
    "TASK_INTELLIGENCE_VERSION", "TASK_DOMAIN_VERSION", "TASK_IDENTITY_VERSION",
    "TASK_TAXONOMY_VERSION", "TASK_LIFECYCLE_VERSION", "TASK_RELATIONSHIP_VERSION",
    "TASK_GOVERNANCE_VERSION", "TASK_REGISTRY_VERSION", "TASK_AUDIT_VERSION",
    "TASK_LINEAGE_VERSION", "TASK_VALIDATION_VERSION", "TASK_REPORT_VERSION",
    "TaskIdentity", "TaskIdentityError", "mint_task", "mint_relationship",
    "validate_identity", "validate_relationship_identity",
    "TaskCategory", "TaskPriority", "TaskRelationType", "TaxonomyError",
    "TASK_CATEGORIES", "TASK_PRIORITIES", "TASK_RELATION_TYPES", "RELATION_TARGET_KINDS",
    "is_category", "validate_category", "parent_of", "ancestry", "is_priority",
    "priority_rank", "is_relation", "validate_relation",
    "TaskLifecycleState", "TaskLifecycle", "TaskLifecycleError", "TaskTransitionRecord",
    "TASK_TRANSITIONS", "GOVERNED_TRANSITIONS",
    "TaskMetadata", "TaskConstraintReference", "TaskVersion", "TaskAuditRecord",
    "TaskDependency", "TaskRelationship", "TaskGovernanceRecord", "TaskLineageRecord",
    "TaskRegistryRecord", "TaskRecord", "TaskGovernanceGate", "TaskGovernanceError",
    "TaskRegistry", "TaskValidator", "make_task_audit_log", "has_cycle", "topological_order",
    "dependency_summary", "TaskService", "TaskDerivationError",
]
