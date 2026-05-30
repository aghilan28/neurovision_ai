"""Policy taxonomy + constraint vocabulary + lifecycle + evaluation outputs (V4-P2).

Closed, versioned vocabularies. Every policy declares a category from
``POLICY_CATEGORIES``; every constraint declares a ``ConstraintType`` and a
``ConstraintCategory``; every evaluation yields one ``EvaluationOutcome``. The
validator rejects anything outside these sets. The taxonomy is intentionally
extensible (add a category) while keeping policy meaning stable and auditable.
"""

from __future__ import annotations

from enum import Enum

from ..version import POLICY_TAXONOMY_VERSION


class PolicyCategory:
    PERMISSION = "permission"
    PROHIBITION = "prohibition"
    OBLIGATION = "obligation"
    ESCALATION = "escalation"
    RISK = "risk"
    GOVERNANCE = "governance"
    QUALITY = "quality"
    WORKFLOW = "workflow"


POLICY_CATEGORIES: frozenset[str] = frozenset(
    v for k, v in vars(PolicyCategory).items() if not k.startswith("_"))

# Illustrative policy exemplars (from the directive).
POLICY_EXAMPLES: dict[str, tuple[str, ...]] = {
    PolicyCategory.ESCALATION: ("Must Escalate High Risk Findings",),
    PolicyCategory.PROHIBITION: ("Cannot Activate Unapproved Goals",
                                 "Cannot Execute Suspended Plans"),
    PolicyCategory.OBLIGATION: ("Requires Governance Approval", "Requires Audit Trail"),
}


class ConstraintType(str, Enum):
    ALLOWED = "allowed"
    FORBIDDEN = "forbidden"
    REQUIRED = "required"
    ESCALATED = "escalated"
    DEFERRED = "deferred"
    CONDITIONAL = "conditional"


CONSTRAINT_TYPES: frozenset[str] = frozenset(t.value for t in ConstraintType)


class ConstraintCategory:
    """The domain a constraint governs (parallels the policy categories)."""

    PERMISSION = "permission"
    PROHIBITION = "prohibition"
    OBLIGATION = "obligation"
    ESCALATION = "escalation"
    RISK = "risk"
    GOVERNANCE = "governance"
    QUALITY = "quality"
    WORKFLOW = "workflow"


CONSTRAINT_CATEGORIES: frozenset[str] = frozenset(
    v for k, v in vars(ConstraintCategory).items() if not k.startswith("_"))


class PolicyLifecycleState(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"


POLICY_LIFECYCLE_STATES: frozenset[str] = frozenset(s.value for s in PolicyLifecycleState)


class EvaluationOutcome(str, Enum):
    PERMITTED = "permitted"
    DENIED = "denied"
    REQUIRES_REVIEW = "requires_review"
    ESCALATED = "escalated"
    CONDITIONAL_APPROVAL = "conditional_approval"


EVALUATION_OUTCOMES: frozenset[str] = frozenset(o.value for o in EvaluationOutcome)


class TaxonomyError(ValueError):
    """Raised when a policy/constraint/outcome value is not in its vocabulary."""


def is_policy_category(category: str) -> bool:
    return category in POLICY_CATEGORIES


def validate_policy_category(category: str) -> None:
    if not is_policy_category(category):
        raise TaxonomyError(f"unknown policy category {category!r}")


def is_constraint_type(ctype: str) -> bool:
    return ctype in CONSTRAINT_TYPES


def validate_constraint_type(ctype: str) -> None:
    if not is_constraint_type(ctype):
        raise TaxonomyError(f"unknown constraint type {ctype!r}")


def is_constraint_category(category: str) -> bool:
    return category in CONSTRAINT_CATEGORIES


def is_outcome(outcome: str) -> bool:
    return outcome in EVALUATION_OUTCOMES


def to_dict() -> dict:
    return {"policy_taxonomy_version": POLICY_TAXONOMY_VERSION,
            "policy_categories": sorted(POLICY_CATEGORIES),
            "constraint_types": sorted(CONSTRAINT_TYPES),
            "constraint_categories": sorted(CONSTRAINT_CATEGORIES),
            "policy_lifecycle_states": sorted(POLICY_LIFECYCLE_STATES),
            "evaluation_outcomes": sorted(EVALUATION_OUTCOMES)}
