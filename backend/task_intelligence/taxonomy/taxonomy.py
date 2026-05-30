"""Task taxonomy (V4-P4).

A closed, versioned, **hierarchical** vocabulary of task categories, plus the task
priority levels and the set of relationship types. Every task declares a category
that exists here; the validator rejects anything else (taxonomy integrity).

``OPERATIONAL`` is the apex (tasks are operational units of work); the remaining
categories refine it. The structure is a fixed mapping so a task's meaning is stable
and auditable, but it is intentionally easy to extend for future expansion.
"""

from __future__ import annotations

from ..version import TASK_TAXONOMY_VERSION


class TaskCategory:
    OPERATIONAL = "operational"
    WORKFLOW = "workflow"
    GOVERNANCE = "governance"
    QUALITY = "quality"
    KNOWLEDGE = "knowledge"
    ANALYTICS = "analytics"
    RISK = "risk"
    VALIDATION = "validation"


# category -> parent category (the apex OPERATIONAL has no parent).
TASK_HIERARCHY: dict[str, str | None] = {
    TaskCategory.OPERATIONAL: None,
    TaskCategory.WORKFLOW: TaskCategory.OPERATIONAL,
    TaskCategory.GOVERNANCE: TaskCategory.OPERATIONAL,
    TaskCategory.QUALITY: TaskCategory.OPERATIONAL,
    TaskCategory.KNOWLEDGE: TaskCategory.OPERATIONAL,
    TaskCategory.ANALYTICS: TaskCategory.OPERATIONAL,
    TaskCategory.RISK: TaskCategory.GOVERNANCE,
    TaskCategory.VALIDATION: TaskCategory.QUALITY,
}

TASK_CATEGORIES: frozenset[str] = frozenset(TASK_HIERARCHY)


class TaskPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


PRIORITY_RANK: dict[str, int] = {
    TaskPriority.LOW: 0, TaskPriority.MEDIUM: 1, TaskPriority.HIGH: 2, TaskPriority.CRITICAL: 3,
}
TASK_PRIORITIES: frozenset[str] = frozenset(PRIORITY_RANK)


class TaskRelationType:
    DEPENDS_ON = "depends_on"
    BLOCKS = "blocks"
    SUPPORTS = "supports"
    REQUIRES = "requires"
    DERIVED_FROM = "derived_from"
    INFLUENCES = "influences"


TASK_RELATION_TYPES: frozenset[str] = frozenset(
    v for k, v in vars(TaskRelationType).items() if not k.startswith("_"))

# the kinds of entity a task relationship may target (Task -> X).
RELATION_TARGET_KINDS: frozenset[str] = frozenset({"task", "plan", "goal", "policy"})


class TaxonomyError(ValueError):
    """Raised when a task category / priority / relation is not in the taxonomy."""


def is_category(category: str) -> bool:
    return category in TASK_CATEGORIES


def validate_category(category: str) -> None:
    if not is_category(category):
        raise TaxonomyError(f"unknown task category {category!r}")


def parent_of(category: str) -> str | None:
    validate_category(category)
    return TASK_HIERARCHY[category]


def ancestry(category: str) -> tuple[str, ...]:
    """The chain from this category up to the apex (inclusive)."""
    validate_category(category)
    chain, cur = [], category
    while cur is not None:
        chain.append(cur)
        cur = TASK_HIERARCHY[cur]
    return tuple(chain)


def is_priority(level: str) -> bool:
    return level in TASK_PRIORITIES


def priority_rank(level: str) -> int:
    return PRIORITY_RANK.get(level, -1)


def is_relation(relation: str) -> bool:
    return relation in TASK_RELATION_TYPES


def validate_relation(relation: str, target_kind: str) -> None:
    if not is_relation(relation):
        raise TaxonomyError(f"unknown task relation {relation!r}")
    if target_kind not in RELATION_TARGET_KINDS:
        raise TaxonomyError(f"unknown relation target kind {target_kind!r}")


def to_dict() -> dict:
    return {"task_taxonomy_version": TASK_TAXONOMY_VERSION,
            "n_categories": len(TASK_CATEGORIES),
            "hierarchy": dict(sorted((k, v) for k, v in TASK_HIERARCHY.items())),
            "priorities": sorted(TASK_PRIORITIES, key=lambda p: PRIORITY_RANK[p]),
            "relation_types": sorted(TASK_RELATION_TYPES),
            "relation_target_kinds": sorted(RELATION_TARGET_KINDS)}
