"""Constraint engine (V4-P2).

Builds explicit, versioned, explainable :class:`ConstraintRecord` artifacts. Each
constraint declares one of the six constraint types (ALLOWED / FORBIDDEN / REQUIRED
/ ESCALATED / DEFERRED / CONDITIONAL), the artifact kind it governs, and the
declarative rules that decide when it applies. The engine mints the deterministic
constraint id and stamps a content-addressed version — it adds no hidden logic.
"""

from __future__ import annotations

from typing import Sequence

from ..identity import mint_constraint
from ..policies.taxonomy import (
    validate_constraint_type, is_constraint_category, ConstraintType, TaxonomyError,
)
from ..models.domain import PolicyRule, ConstraintRecord, PolicyVersion


class ConstraintEngine:
    """Creates explicit, versioned constraints (deterministic + explainable)."""

    def build(self, *, constraint_type: str, category: str, subject_kind: str,
              constraint_key: str, rules: Sequence[PolicyRule] = (),
              explanation: str = "") -> ConstraintRecord:
        validate_constraint_type(constraint_type)
        if not is_constraint_category(category):
            raise TaxonomyError(f"unknown constraint category {category!r}")
        cid = mint_constraint(constraint_type, subject_kind, constraint_key)
        rules = tuple(rules)
        # content-addressed version (deterministic; chained from None at creation)
        provisional = ConstraintRecord(
            constraint_id=cid, constraint_type=constraint_type, category=category,
            subject_kind=subject_kind, constraint_key=constraint_key, rules=rules,
            explanation=explanation)
        version = PolicyVersion.compute(provisional.state_signature(), None)
        return ConstraintRecord(
            constraint_id=cid, constraint_type=constraint_type, category=category,
            subject_kind=subject_kind, constraint_key=constraint_key, rules=rules,
            explanation=explanation, version=version)

    @staticmethod
    def is_blocking(constraint: ConstraintRecord) -> bool:
        """FORBIDDEN constraints deny; REQUIRED constraints must be satisfied."""
        return constraint.constraint_type in (ConstraintType.FORBIDDEN.value,
                                              ConstraintType.REQUIRED.value)
