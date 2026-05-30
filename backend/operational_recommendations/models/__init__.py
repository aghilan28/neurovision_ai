"""Recommendation domain model package (V3-P6)."""

from __future__ import annotations

from .kinds import (
    RecommendationKind, RecommendationKindError, RECOMMENDATION_KINDS,
    PriorityLevel, PRIORITY_RANK, PRIORITY_LEVELS,
    is_kind, validate_kind, is_priority, priority_rank,
)
from .domain import (
    RecommendationEvidence, RecommendationContext, RecommendationPriority, RecommendationRecord,
    RecommendationAuditRecord, RecommendationVersion, RecommendationLineageRecord,
    RecommendationRegistryRecord,
)

__all__ = [
    "RecommendationKind", "RecommendationKindError", "RECOMMENDATION_KINDS",
    "PriorityLevel", "PRIORITY_RANK", "PRIORITY_LEVELS",
    "is_kind", "validate_kind", "is_priority", "priority_rank",
    "RecommendationEvidence", "RecommendationContext", "RecommendationPriority",
    "RecommendationRecord", "RecommendationAuditRecord", "RecommendationVersion",
    "RecommendationLineageRecord", "RecommendationRegistryRecord",
]
