"""``backend/planning_foundation`` — Planning Foundation (V4-P3).

Introduces **Plans as first-class platform entities** — the bridge between an
approved Goal and Tasks. A Plan defines *how a goal may be achieved*. It is an
**intent structure**, not an execution structure: it never executes, never completes
work, never describes agent behavior, and never performs autonomous action.

Every plan is versioned, traceable, auditable, lineage-tracked, governed,
deterministic, and recoverable. A plan moves through a governed lifecycle (PROPOSED
-> DRAFT -> UNDER_REVIEW -> APPROVED -> READY -> {SUSPENDED, COMPLETED} -> ARCHIVED);
forbidden transitions are blocked, and a plan cannot become READY without
policy-governed approval (V4-P2 integration). **Every plan derives from an approved
goal**, so a plan traces back through the goal — and the operational intelligence the
goal derived from — to the patient via the platform's single
``ml.lineage.LineageTracker``; every change is recorded in the shared
``ImmutableAuditLog`` — no parallel lineage/audit/governance systems.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and
sibling ``backend`` subsystems; never imports ``frontend``. Scope is strictly V4-P3
— no agents, execution, simulation, or autonomous action. See
``.gcc/decisions/ADR-0012``.
"""

from __future__ import annotations

from .version import (
    PLANNING_FOUNDATION_VERSION, PLAN_DOMAIN_VERSION, PLAN_IDENTITY_VERSION,
    PLAN_TAXONOMY_VERSION, PLAN_LIFECYCLE_VERSION, PLAN_RELATIONSHIP_VERSION,
    PLAN_GOVERNANCE_VERSION, PLAN_REGISTRY_VERSION, PLAN_AUDIT_VERSION,
    PLAN_LINEAGE_VERSION, PLAN_VALIDATION_VERSION, PLAN_REPORT_VERSION,
)
from .identity import (
    PlanIdentity, PlanIdentityError, mint_plan, mint_relationship,
    validate_identity, validate_relationship_identity,
)
from .taxonomy import (
    PlanCategory, PlanPriority, PlanRelationType, TaxonomyError,
    PLAN_CATEGORIES, PLAN_PRIORITIES, PLAN_RELATION_TYPES, RELATION_TARGET_KINDS,
    is_category, validate_category, parent_of, ancestry, is_priority, priority_rank,
    is_relation, validate_relation,
)
from .lifecycle import (
    PlanLifecycleState, PlanLifecycle, PlanLifecycleError, PlanTransitionRecord,
    PLAN_TRANSITIONS, GOVERNED_TRANSITIONS,
)
from .models import (
    PlanMetadata, PlanConstraintReference, PlanVersion, PlanAuditRecord, PlanDependency,
    PlanRelationship, PlanGovernanceRecord, PlanLineageRecord, PlanRegistryRecord, PlanRecord,
)
from .governance import PlanGovernanceGate, PlanGovernanceError
from .registry import PlanRegistry
from .validation import PlanValidator
from .audit import make_plan_audit_log
from .dependencies import has_cycle, topological_order, dependency_summary
from .service import PlanService, PlanDerivationError

__all__ = [
    "PLANNING_FOUNDATION_VERSION", "PLAN_DOMAIN_VERSION", "PLAN_IDENTITY_VERSION",
    "PLAN_TAXONOMY_VERSION", "PLAN_LIFECYCLE_VERSION", "PLAN_RELATIONSHIP_VERSION",
    "PLAN_GOVERNANCE_VERSION", "PLAN_REGISTRY_VERSION", "PLAN_AUDIT_VERSION",
    "PLAN_LINEAGE_VERSION", "PLAN_VALIDATION_VERSION", "PLAN_REPORT_VERSION",
    "PlanIdentity", "PlanIdentityError", "mint_plan", "mint_relationship",
    "validate_identity", "validate_relationship_identity",
    "PlanCategory", "PlanPriority", "PlanRelationType", "TaxonomyError",
    "PLAN_CATEGORIES", "PLAN_PRIORITIES", "PLAN_RELATION_TYPES", "RELATION_TARGET_KINDS",
    "is_category", "validate_category", "parent_of", "ancestry", "is_priority",
    "priority_rank", "is_relation", "validate_relation",
    "PlanLifecycleState", "PlanLifecycle", "PlanLifecycleError", "PlanTransitionRecord",
    "PLAN_TRANSITIONS", "GOVERNED_TRANSITIONS",
    "PlanMetadata", "PlanConstraintReference", "PlanVersion", "PlanAuditRecord",
    "PlanDependency", "PlanRelationship", "PlanGovernanceRecord", "PlanLineageRecord",
    "PlanRegistryRecord", "PlanRecord", "PlanGovernanceGate", "PlanGovernanceError",
    "PlanRegistry", "PlanValidator", "make_plan_audit_log", "has_cycle", "topological_order",
    "dependency_summary", "PlanService", "PlanDerivationError",
]
