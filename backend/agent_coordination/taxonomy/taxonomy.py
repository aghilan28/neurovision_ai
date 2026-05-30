"""Agent taxonomy (V4-P5).

A closed, versioned, **hierarchical** vocabulary of agent categories, plus the agent
priority levels, the relationship types, the capability risk levels, and the
assignment states. Every agent declares a category that exists here; the validator
rejects anything else (taxonomy integrity).

``PARTICIPANT`` is the apex (every agent is a governed participant); the concrete
agent kinds (human/system/service/...) refine it. The structure is a fixed mapping
so an agent's meaning is stable and auditable, but it is intentionally easy to
extend for future expansion (e.g. future AI agents).
"""

from __future__ import annotations

from ..version import AGENT_TAXONOMY_VERSION


class AgentCategory:
    PARTICIPANT = "participant"      # apex (a governed participant)
    HUMAN = "human"
    SYSTEM = "system"
    SERVICE = "service"
    VALIDATION = "validation"
    GOVERNANCE = "governance"
    ANALYTICS = "analytics"
    KNOWLEDGE = "knowledge"
    COORDINATION = "coordination"


# category -> parent category (the apex PARTICIPANT has no parent).
AGENT_HIERARCHY: dict[str, str | None] = {
    AgentCategory.PARTICIPANT: None,
    AgentCategory.HUMAN: AgentCategory.PARTICIPANT,
    AgentCategory.SYSTEM: AgentCategory.PARTICIPANT,
    AgentCategory.SERVICE: AgentCategory.SYSTEM,
    AgentCategory.VALIDATION: AgentCategory.SYSTEM,
    AgentCategory.GOVERNANCE: AgentCategory.PARTICIPANT,
    AgentCategory.ANALYTICS: AgentCategory.SYSTEM,
    AgentCategory.KNOWLEDGE: AgentCategory.SYSTEM,
    AgentCategory.COORDINATION: AgentCategory.PARTICIPANT,
}

AGENT_CATEGORIES: frozenset[str] = frozenset(AGENT_HIERARCHY)


class AgentPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


PRIORITY_RANK: dict[str, int] = {
    AgentPriority.LOW: 0, AgentPriority.MEDIUM: 1, AgentPriority.HIGH: 2, AgentPriority.CRITICAL: 3,
}
AGENT_PRIORITIES: frozenset[str] = frozenset(PRIORITY_RANK)


class AgentRelationType:
    SUPPORTS = "supports"
    DEPENDS_ON = "depends_on"
    COORDINATES = "coordinates"
    DERIVED_FROM = "derived_from"
    INFLUENCES = "influences"


AGENT_RELATION_TYPES: frozenset[str] = frozenset(
    v for k, v in vars(AgentRelationType).items() if not k.startswith("_"))

# the kinds of entity an agent relationship may target (Agent -> X).
RELATION_TARGET_KINDS: frozenset[str] = frozenset({"agent", "goal", "policy", "plan"})


class CapabilityRisk:
    """The governed risk level of a capability (drives capability approval)."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


CAPABILITY_RISK_RANK: dict[str, int] = {
    CapabilityRisk.LOW: 0, CapabilityRisk.MODERATE: 1, CapabilityRisk.HIGH: 2,
    CapabilityRisk.CRITICAL: 3,
}
CAPABILITY_RISK_LEVELS: frozenset[str] = frozenset(CAPABILITY_RISK_RANK)


class CapabilityMode:
    """Whether a capability is allowed, restricted, or required for the agent."""

    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    REQUIRED = "required"


CAPABILITY_MODES: frozenset[str] = frozenset(
    v for k, v in vars(CapabilityMode).items() if not k.startswith("_"))


class AssignmentState:
    ASSIGNED = "assigned"
    PENDING = "pending"
    BLOCKED = "blocked"
    REVOKED = "revoked"
    COMPLETED = "completed"


ASSIGNMENT_STATES: frozenset[str] = frozenset(
    v for k, v in vars(AssignmentState).items() if not k.startswith("_"))

# the kinds of entity an assignment may target (Agent -> X). An assignment never
# implies execution; it records that an agent is associated with a unit of work.
ASSIGNMENT_TARGET_KINDS: frozenset[str] = frozenset({"task", "plan", "goal", "policy"})


class TaxonomyError(ValueError):
    """Raised when an agent category / priority / relation / capability value is unknown."""


def is_category(category: str) -> bool:
    return category in AGENT_CATEGORIES


def validate_category(category: str) -> None:
    if not is_category(category):
        raise TaxonomyError(f"unknown agent category {category!r}")


def parent_of(category: str) -> str | None:
    validate_category(category)
    return AGENT_HIERARCHY[category]


def ancestry(category: str) -> tuple[str, ...]:
    validate_category(category)
    chain, cur = [], category
    while cur is not None:
        chain.append(cur)
        cur = AGENT_HIERARCHY[cur]
    return tuple(chain)


def is_priority(level: str) -> bool:
    return level in AGENT_PRIORITIES


def priority_rank(level: str) -> int:
    return PRIORITY_RANK.get(level, -1)


def is_relation(relation: str) -> bool:
    return relation in AGENT_RELATION_TYPES


def validate_relation(relation: str, target_kind: str) -> None:
    if not is_relation(relation):
        raise TaxonomyError(f"unknown agent relation {relation!r}")
    if target_kind not in RELATION_TARGET_KINDS:
        raise TaxonomyError(f"unknown relation target kind {target_kind!r}")


def is_capability_risk(level: str) -> bool:
    return level in CAPABILITY_RISK_LEVELS


def is_capability_mode(mode: str) -> bool:
    return mode in CAPABILITY_MODES


def is_assignment_state(state: str) -> bool:
    return state in ASSIGNMENT_STATES


def is_assignment_target(kind: str) -> bool:
    return kind in ASSIGNMENT_TARGET_KINDS


def to_dict() -> dict:
    return {"agent_taxonomy_version": AGENT_TAXONOMY_VERSION,
            "n_categories": len(AGENT_CATEGORIES),
            "hierarchy": dict(sorted((k, v) for k, v in AGENT_HIERARCHY.items())),
            "priorities": sorted(AGENT_PRIORITIES, key=lambda p: PRIORITY_RANK[p]),
            "relation_types": sorted(AGENT_RELATION_TYPES),
            "relation_target_kinds": sorted(RELATION_TARGET_KINDS),
            "capability_risk_levels": sorted(CAPABILITY_RISK_LEVELS,
                                             key=lambda r: CAPABILITY_RISK_RANK[r]),
            "capability_modes": sorted(CAPABILITY_MODES),
            "assignment_states": sorted(ASSIGNMENT_STATES),
            "assignment_target_kinds": sorted(ASSIGNMENT_TARGET_KINDS)}
