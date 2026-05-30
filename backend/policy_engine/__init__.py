"""``backend/policy_engine`` — Policy & Constraint Engine (V4-P2).

Creates explicit **governance boundaries**: the platform now understands what is
ALLOWED / FORBIDDEN / REQUIRED / ESCALATED before any planning or execution can ever
exist. Policies are the **safety system** of Version 4.

Every policy and constraint is versioned, traceable, auditable, lineage-tracked,
governed, deterministic, and **explainable** — policies never contain hidden logic
and every evaluation records exactly which rules and constraints fired and why.
Constraint types are ALLOWED/FORBIDDEN/REQUIRED/ESCALATED/DEFERRED/CONDITIONAL;
evaluation outcomes are PERMITTED/DENIED/REQUIRES_REVIEW/ESCALATED/
CONDITIONAL_APPROVAL. A policy only evaluates while ACTIVE and never becomes ACTIVE
without governance approval. Shares the platform's single
``ml.lineage.LineageTracker`` and the shared ``ImmutableAuditLog`` — no parallel
lineage/audit/governance.

Goal<->Policy integration: the engine exposes a goal policy decider
(``goal_policy_decider``) so a goal cannot become ACTIVE (or approved/suspended/
completed) without a policy-governed decision.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and
sibling ``backend`` subsystems; never imports ``frontend``. Scope is strictly V4-P2
— no planning, tasks, agents, execution, simulation, or autonomous action. See
``.gcc/decisions/ADR-0011``.
"""

from __future__ import annotations

from .version import (
    POLICY_ENGINE_VERSION, POLICY_DOMAIN_VERSION, POLICY_IDENTITY_VERSION,
    POLICY_TAXONOMY_VERSION, POLICY_RULE_VERSION, CONSTRAINT_VERSION,
    POLICY_EVALUATION_VERSION, POLICY_GOVERNANCE_VERSION, POLICY_REGISTRY_VERSION,
    POLICY_AUDIT_VERSION, POLICY_LINEAGE_VERSION, POLICY_VALIDATION_VERSION,
    POLICY_REPORT_VERSION,
)
from .identity import (
    PolicyIdentity, PolicyIdentityError, mint_policy, mint_constraint, mint_evaluation,
    validate_identity, validate_constraint_identity, validate_evaluation_identity,
)
from .policies import (
    PolicyCategory, ConstraintType, ConstraintCategory, PolicyLifecycleState, EvaluationOutcome,
    TaxonomyError, POLICY_CATEGORIES, CONSTRAINT_TYPES, CONSTRAINT_CATEGORIES,
    EVALUATION_OUTCOMES, POLICY_LIFECYCLE_STATES, is_policy_category, validate_policy_category,
    is_constraint_type, is_outcome, PolicyLifecycle, PolicyLifecycleError, POLICY_TRANSITIONS,
)
from .models import (
    PolicyRule, ConstraintRecord, PolicyRecord, PolicyEvaluation, PolicyVersion,
    PolicyAuditRecord, PolicyLineageRecord, PolicyRegistryRecord,
)
from .constraints import ConstraintEngine
from .evaluation import PolicyEvaluationEngine
from .governance import PolicyGovernanceGate, PolicyGovernanceError
from .registry import PolicyRegistry
from .validation import PolicyValidator
from .audit import make_policy_audit_log
from .service import PolicyService
from .integration import goal_policy_decider, install_default_goal_policies

__all__ = [
    "POLICY_ENGINE_VERSION", "POLICY_DOMAIN_VERSION", "POLICY_IDENTITY_VERSION",
    "POLICY_TAXONOMY_VERSION", "POLICY_RULE_VERSION", "CONSTRAINT_VERSION",
    "POLICY_EVALUATION_VERSION", "POLICY_GOVERNANCE_VERSION", "POLICY_REGISTRY_VERSION",
    "POLICY_AUDIT_VERSION", "POLICY_LINEAGE_VERSION", "POLICY_VALIDATION_VERSION",
    "POLICY_REPORT_VERSION",
    "PolicyIdentity", "PolicyIdentityError", "mint_policy", "mint_constraint", "mint_evaluation",
    "validate_identity", "validate_constraint_identity", "validate_evaluation_identity",
    "PolicyCategory", "ConstraintType", "ConstraintCategory", "PolicyLifecycleState",
    "EvaluationOutcome", "TaxonomyError", "POLICY_CATEGORIES", "CONSTRAINT_TYPES",
    "CONSTRAINT_CATEGORIES", "EVALUATION_OUTCOMES", "POLICY_LIFECYCLE_STATES",
    "is_policy_category", "validate_policy_category", "is_constraint_type", "is_outcome",
    "PolicyLifecycle", "PolicyLifecycleError", "POLICY_TRANSITIONS",
    "PolicyRule", "ConstraintRecord", "PolicyRecord", "PolicyEvaluation", "PolicyVersion",
    "PolicyAuditRecord", "PolicyLineageRecord", "PolicyRegistryRecord",
    "ConstraintEngine", "PolicyEvaluationEngine", "PolicyGovernanceGate", "PolicyGovernanceError",
    "PolicyRegistry", "PolicyValidator", "make_policy_audit_log", "PolicyService",
    "goal_policy_decider", "install_default_goal_policies",
]
