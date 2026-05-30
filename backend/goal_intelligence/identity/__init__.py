"""Goal identity package (V4-P1)."""

from __future__ import annotations

from .identity import (
    GoalIdentity, GoalIdentityError, mint_goal, mint_relationship,
    validate_identity, validate_relationship_identity,
)

__all__ = [
    "GoalIdentity", "GoalIdentityError", "mint_goal", "mint_relationship",
    "validate_identity", "validate_relationship_identity",
]
