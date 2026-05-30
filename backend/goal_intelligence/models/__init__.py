"""Goal domain model package (V4-P1)."""

from __future__ import annotations

from .domain import (
    GoalMetadata, GoalConstraintReference, GoalVersion, GoalAuditRecord,
    GoalGovernance, GoalRelationship, GoalLineageRecord, GoalRegistryRecord, GoalRecord,
)

__all__ = [
    "GoalMetadata", "GoalConstraintReference", "GoalVersion", "GoalAuditRecord",
    "GoalGovernance", "GoalRelationship", "GoalLineageRecord", "GoalRegistryRecord",
    "GoalRecord",
]
