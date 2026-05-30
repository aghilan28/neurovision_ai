"""Plan taxonomy (V4-P3).

A closed, versioned, **hierarchical** vocabulary of plan categories, plus the plan
priority levels and the set of relationship types. Every plan declares a category
that exists here; the validator rejects anything else (taxonomy integrity).

``STRATEGIC`` is the apex; the remaining categories refine it. The structure is a
fixed mapping so a plan's meaning is stable and auditable, but it is intentionally
easy to extend (add a category + its parent) for future expansion.
"""

from __future__ import annotations

from ..version import PLAN_TAXONOMY_VERSION


class PlanCategory:
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"
    WORKFLOW = "workflow"
    GOVERNANCE = "governance"
    QUALITY = "quality"
    RISK = "risk"
    KNOWLEDGE = "knowledge"
    ANALYTICS = "analytics"


# category -> parent category (the apex STRATEGIC has no parent).
PLAN_HIERARCHY: dict[str, str | None] = {
    PlanCategory.STRATEGIC: None,
    PlanCategory.OPERATIONAL: PlanCategory.STRATEGIC,
    PlanCategory.WORKFLOW: PlanCategory.OPERATIONAL,
    PlanCategory.GOVERNANCE: PlanCategory.STRATEGIC,
    PlanCategory.QUALITY: PlanCategory.OPERATIONAL,
    PlanCategory.RISK: PlanCategory.GOVERNANCE,
    PlanCategory.KNOWLEDGE: PlanCategory.OPERATIONAL,
    PlanCategory.ANALYTICS: PlanCategory.OPERATIONAL,
}

PLAN_CATEGORIES: frozenset[str] = frozenset(PLAN_HIERARCHY)


class PlanPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


PRIORITY_RANK: dict[str, int] = {
    PlanPriority.LOW: 0, PlanPriority.MEDIUM: 1, PlanPriority.HIGH: 2, PlanPriority.CRITICAL: 3,
}
PLAN_PRIORITIES: frozenset[str] = frozenset(PRIORITY_RANK)


class PlanRelationType:
    DEPENDS_ON = "depends_on"
    SUPPORTS = "supports"
    BLOCKS = "blocks"
    REQUIRES = "requires"
    DERIVED_FROM = "derived_from"
    INFLUENCES = "influences"


PLAN_RELATION_TYPES: frozenset[str] = frozenset(
    v for k, v in vars(PlanRelationType).items() if not k.startswith("_"))

# the kinds of entity a plan relationship may target (Plan -> X).
RELATION_TARGET_KINDS: frozenset[str] = frozenset({"plan", "goal", "policy", "constraint"})


class TaxonomyError(ValueError):
    """Raised when a plan category / priority / relation is not in the taxonomy."""


def is_category(category: str) -> bool:
    return category in PLAN_CATEGORIES


def validate_category(category: str) -> None:
    if not is_category(category):
        raise TaxonomyError(f"unknown plan category {category!r}")


def parent_of(category: str) -> str | None:
    validate_category(category)
    return PLAN_HIERARCHY[category]


def ancestry(category: str) -> tuple[str, ...]:
    """The chain from this category up to the apex (inclusive)."""
    validate_category(category)
    chain, cur = [], category
    while cur is not None:
        chain.append(cur)
        cur = PLAN_HIERARCHY[cur]
    return tuple(chain)


def is_priority(level: str) -> bool:
    return level in PLAN_PRIORITIES


def priority_rank(level: str) -> int:
    return PRIORITY_RANK.get(level, -1)


def is_relation(relation: str) -> bool:
    return relation in PLAN_RELATION_TYPES


def validate_relation(relation: str, target_kind: str) -> None:
    if not is_relation(relation):
        raise TaxonomyError(f"unknown plan relation {relation!r}")
    if target_kind not in RELATION_TARGET_KINDS:
        raise TaxonomyError(f"unknown relation target kind {target_kind!r}")


def to_dict() -> dict:
    return {"plan_taxonomy_version": PLAN_TAXONOMY_VERSION,
            "n_categories": len(PLAN_CATEGORIES),
            "hierarchy": dict(sorted((k, v) for k, v in PLAN_HIERARCHY.items())),
            "priorities": sorted(PLAN_PRIORITIES, key=lambda p: PRIORITY_RANK[p]),
            "relation_types": sorted(PLAN_RELATION_TYPES),
            "relation_target_kinds": sorted(RELATION_TARGET_KINDS)}
