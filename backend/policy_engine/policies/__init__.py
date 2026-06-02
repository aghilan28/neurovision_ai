"""Policy taxonomy + lifecycle package (V4-P2)."""

from __future__ import annotations

from .taxonomy import (
    PolicyCategory, ConstraintType, ConstraintCategory, PolicyLifecycleState,
    EvaluationOutcome, TaxonomyError, POLICY_CATEGORIES, CONSTRAINT_TYPES,
    CONSTRAINT_CATEGORIES, EVALUATION_OUTCOMES, POLICY_LIFECYCLE_STATES, POLICY_EXAMPLES,
    is_policy_category, validate_policy_category, is_constraint_type, validate_constraint_type,
    is_constraint_category, is_outcome,
)
from .lifecycle import (
    PolicyLifecycle, PolicyLifecycleError, PolicyTransitionRecord, POLICY_TRANSITIONS,
    GOVERNED_TRANSITIONS, is_allowed_transition,
)

__all__ = [
    "PolicyCategory", "ConstraintType", "ConstraintCategory", "PolicyLifecycleState",
    "EvaluationOutcome", "TaxonomyError", "POLICY_CATEGORIES", "CONSTRAINT_TYPES",
    "CONSTRAINT_CATEGORIES", "EVALUATION_OUTCOMES", "POLICY_LIFECYCLE_STATES", "POLICY_EXAMPLES",
    "is_policy_category", "validate_policy_category", "is_constraint_type",
    "validate_constraint_type", "is_constraint_category", "is_outcome",
    "PolicyLifecycle", "PolicyLifecycleError", "PolicyTransitionRecord", "POLICY_TRANSITIONS",
    "GOVERNED_TRANSITIONS", "is_allowed_transition",
]
