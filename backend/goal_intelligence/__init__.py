"""``backend/goal_intelligence`` — Goal Intelligence Foundation (V4-P1).

Introduces **Goals as first-class platform entities**. A Goal is *intent* — a
desired outcome — and is the foundation for later phases (plans, tasks, agents,
execution, governance). A Goal is **not** a recommendation, a task, a plan, or
execution, and **never directly performs actions**.

Every goal is versioned, traceable, auditable, lineage-tracked, governed,
deterministic, and recoverable. A goal moves through a governed lifecycle
(PROPOSED -> DRAFT -> UNDER_REVIEW -> APPROVED -> ACTIVE -> {SUSPENDED, COMPLETED}
-> ARCHIVED); forbidden transitions are blocked, and a goal cannot become ACTIVE
without policy-governed approval (V4-P2 integration). Goals trace back through the
operational intelligence they derive from to the patient via the platform's single
``ml.lineage.LineageTracker``; every change is recorded in the shared
``ImmutableAuditLog`` — no parallel lineage/audit/governance systems.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and
sibling ``backend`` subsystems; never imports ``frontend``. Scope is strictly V4-P1
— no planning, tasks, agents, execution, simulation, or autonomous action. See
``.gcc/decisions/ADR-0011``.
"""

from __future__ import annotations

from .version import (
    GOAL_INTELLIGENCE_VERSION, GOAL_DOMAIN_VERSION, GOAL_IDENTITY_VERSION,
    GOAL_TAXONOMY_VERSION, GOAL_LIFECYCLE_VERSION, GOAL_RELATIONSHIP_VERSION,
    GOAL_GOVERNANCE_VERSION, GOAL_REGISTRY_VERSION, GOAL_AUDIT_VERSION,
    GOAL_LINEAGE_VERSION, GOAL_VALIDATION_VERSION, GOAL_REPORT_VERSION,
)
from .identity import (
    GoalIdentity, GoalIdentityError, mint_goal, mint_relationship,
    validate_identity, validate_relationship_identity,
)
from .taxonomy import (
    GoalCategory, GoalPriority, GoalRelationType, TaxonomyError,
    GOAL_CATEGORIES, GOAL_PRIORITIES, GOAL_RELATION_TYPES, RELATION_TARGET_KINDS,
    is_category, validate_category, parent_of, ancestry, is_priority, priority_rank,
    is_relation, validate_relation,
)
from .lifecycle import (
    GoalLifecycleState, GoalLifecycle, GoalLifecycleError, GoalTransitionRecord,
    GOAL_TRANSITIONS, GOVERNED_TRANSITIONS,
)
from .models import (
    GoalMetadata, GoalConstraintReference, GoalVersion, GoalAuditRecord, GoalGovernance,
    GoalRelationship, GoalLineageRecord, GoalRegistryRecord, GoalRecord,
)
from .governance import GoalGovernanceGate, GoalGovernanceError
from .registry import GoalRegistry
from .validation import GoalValidator
from .audit import make_goal_audit_log
from .service import GoalService

__all__ = [
    "GOAL_INTELLIGENCE_VERSION", "GOAL_DOMAIN_VERSION", "GOAL_IDENTITY_VERSION",
    "GOAL_TAXONOMY_VERSION", "GOAL_LIFECYCLE_VERSION", "GOAL_RELATIONSHIP_VERSION",
    "GOAL_GOVERNANCE_VERSION", "GOAL_REGISTRY_VERSION", "GOAL_AUDIT_VERSION",
    "GOAL_LINEAGE_VERSION", "GOAL_VALIDATION_VERSION", "GOAL_REPORT_VERSION",
    "GoalIdentity", "GoalIdentityError", "mint_goal", "mint_relationship",
    "validate_identity", "validate_relationship_identity",
    "GoalCategory", "GoalPriority", "GoalRelationType", "TaxonomyError",
    "GOAL_CATEGORIES", "GOAL_PRIORITIES", "GOAL_RELATION_TYPES", "RELATION_TARGET_KINDS",
    "is_category", "validate_category", "parent_of", "ancestry", "is_priority",
    "priority_rank", "is_relation", "validate_relation",
    "GoalLifecycleState", "GoalLifecycle", "GoalLifecycleError", "GoalTransitionRecord",
    "GOAL_TRANSITIONS", "GOVERNED_TRANSITIONS",
    "GoalMetadata", "GoalConstraintReference", "GoalVersion", "GoalAuditRecord",
    "GoalGovernance", "GoalRelationship", "GoalLineageRecord", "GoalRegistryRecord",
    "GoalRecord", "GoalGovernanceGate", "GoalGovernanceError", "GoalRegistry",
    "GoalValidator", "make_goal_audit_log", "GoalService",
]
