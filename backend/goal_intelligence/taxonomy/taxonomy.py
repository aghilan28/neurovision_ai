"""Goal taxonomy (V4-P1).

A closed, versioned, **hierarchical** vocabulary of goal categories, plus the goal
priority levels and the set of relationship types. Every goal declares a category
that exists here; the validator rejects anything else (taxonomy integrity).

The taxonomy is hierarchical: ``STRATEGIC`` is the apex; the remaining categories
(operational, workflow, quality, governance, knowledge, analytics, risk) refine it.
The structure is a fixed mapping so a goal's meaning is stable and auditable, but it
is intentionally easy to extend (add a category + its parent) for future expansion.
"""

from __future__ import annotations

from ..version import GOAL_TAXONOMY_VERSION


class GoalCategory:
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"
    WORKFLOW = "workflow"
    QUALITY = "quality"
    GOVERNANCE = "governance"
    KNOWLEDGE = "knowledge"
    ANALYTICS = "analytics"
    RISK = "risk"


# category -> parent category (the apex STRATEGIC has no parent).
GOAL_HIERARCHY: dict[str, str | None] = {
    GoalCategory.STRATEGIC: None,
    GoalCategory.OPERATIONAL: GoalCategory.STRATEGIC,
    GoalCategory.WORKFLOW: GoalCategory.OPERATIONAL,
    GoalCategory.QUALITY: GoalCategory.OPERATIONAL,
    GoalCategory.GOVERNANCE: GoalCategory.STRATEGIC,
    GoalCategory.KNOWLEDGE: GoalCategory.OPERATIONAL,
    GoalCategory.ANALYTICS: GoalCategory.OPERATIONAL,
    GoalCategory.RISK: GoalCategory.GOVERNANCE,
}

GOAL_CATEGORIES: frozenset[str] = frozenset(GOAL_HIERARCHY)

# Illustrative goal definitions per category (examples from the directive). These
# are reference exemplars, not an exhaustive closed set of goal statements.
GOAL_EXAMPLES: dict[str, tuple[str, ...]] = {
    GoalCategory.WORKFLOW: ("Reduce Review Latency", "Increase Workflow Throughput"),
    GoalCategory.KNOWLEDGE: ("Improve Knowledge Coverage",),
    GoalCategory.RISK: ("Reduce Bottleneck Risk",),
    GoalCategory.QUALITY: ("Improve Data Quality",),
    GoalCategory.GOVERNANCE: ("Strengthen Governance Compliance",),
}


class GoalPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


PRIORITY_RANK: dict[str, int] = {
    GoalPriority.LOW: 0, GoalPriority.MEDIUM: 1, GoalPriority.HIGH: 2, GoalPriority.CRITICAL: 3,
}
GOAL_PRIORITIES: frozenset[str] = frozenset(PRIORITY_RANK)


class GoalRelationType:
    DEPENDS_ON = "depends_on"
    SUPPORTS = "supports"
    CONFLICTS_WITH = "conflicts_with"
    DERIVED_FROM = "derived_from"
    INFLUENCES = "influences"
    BLOCKED_BY = "blocked_by"


GOAL_RELATION_TYPES: frozenset[str] = frozenset(
    v for k, v in vars(GoalRelationType).items() if not k.startswith("_"))

# the kinds of entity a goal relationship may target (Goal -> X).
RELATION_TARGET_KINDS: frozenset[str] = frozenset(
    {"goal", "workflow", "analytics", "recommendation", "risk", "governance"})


class TaxonomyError(ValueError):
    """Raised when a goal category / priority / relation is not in the taxonomy."""


def is_category(category: str) -> bool:
    return category in GOAL_CATEGORIES


def validate_category(category: str) -> None:
    if not is_category(category):
        raise TaxonomyError(f"unknown goal category {category!r}")


def parent_of(category: str) -> str | None:
    validate_category(category)
    return GOAL_HIERARCHY[category]


def ancestry(category: str) -> tuple[str, ...]:
    """The chain from this category up to the apex (inclusive)."""
    validate_category(category)
    chain, cur = [], category
    while cur is not None:
        chain.append(cur)
        cur = GOAL_HIERARCHY[cur]
    return tuple(chain)


def is_priority(level: str) -> bool:
    return level in GOAL_PRIORITIES


def priority_rank(level: str) -> int:
    return PRIORITY_RANK.get(level, -1)


def is_relation(relation: str) -> bool:
    return relation in GOAL_RELATION_TYPES


def validate_relation(relation: str, target_kind: str) -> None:
    if not is_relation(relation):
        raise TaxonomyError(f"unknown goal relation {relation!r}")
    if target_kind not in RELATION_TARGET_KINDS:
        raise TaxonomyError(f"unknown relation target kind {target_kind!r}")


def to_dict() -> dict:
    return {"goal_taxonomy_version": GOAL_TAXONOMY_VERSION,
            "n_categories": len(GOAL_CATEGORIES),
            "hierarchy": dict(sorted((k, v) for k, v in GOAL_HIERARCHY.items())),
            "priorities": sorted(GOAL_PRIORITIES, key=lambda p: PRIORITY_RANK[p]),
            "relation_types": sorted(GOAL_RELATION_TYPES),
            "relation_target_kinds": sorted(RELATION_TARGET_KINDS)}
