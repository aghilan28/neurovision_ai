"""Recommendation kind + priority vocabularies (V3-P6).

Closed, versioned sets of recommendation **kinds** (the categories of explainable
operational output the platform may produce) and **priority levels**. Every
recommendation declares a kind from this set; the validator rejects anything else
(kind integrity).

These are strictly *operational* outputs — guidance, prioritization, optimization
suggestions, and escalation candidates. They are **not** clinical decision support,
medical advice, diagnosis, or treatment.
"""

from __future__ import annotations

from ..version import RECOMMENDATION_DOMAIN_VERSION


class RecommendationKind:
    GUIDANCE = "guidance"
    PRIORITIZATION = "prioritization"
    OPTIMIZATION = "optimization"
    ESCALATION = "escalation"


RECOMMENDATION_KINDS: frozenset[str] = frozenset(
    v for k, v in vars(RecommendationKind).items() if not k.startswith("_"))


class PriorityLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Deterministic ordering for comparisons/sorting (higher rank = more urgent).
PRIORITY_RANK: dict[str, int] = {
    PriorityLevel.LOW: 0, PriorityLevel.MEDIUM: 1, PriorityLevel.HIGH: 2,
    PriorityLevel.CRITICAL: 3,
}
PRIORITY_LEVELS: frozenset[str] = frozenset(PRIORITY_RANK)


class RecommendationKindError(ValueError):
    """Raised when a recommendation kind is not in the closed vocabulary."""


def is_kind(kind: str) -> bool:
    return kind in RECOMMENDATION_KINDS


def validate_kind(kind: str) -> None:
    if not is_kind(kind):
        raise RecommendationKindError(f"unknown recommendation kind {kind!r}")


def is_priority(level: str) -> bool:
    return level in PRIORITY_LEVELS


def priority_rank(level: str) -> int:
    return PRIORITY_RANK.get(level, -1)


def to_dict() -> dict:
    return {"recommendation_domain_version": RECOMMENDATION_DOMAIN_VERSION,
            "kinds": sorted(RECOMMENDATION_KINDS),
            "priority_levels": sorted(PRIORITY_LEVELS, key=lambda p: PRIORITY_RANK[p])}
