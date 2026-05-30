"""Agent taxonomy package (V4-P5)."""

from __future__ import annotations

from .taxonomy import (
    AgentCategory, AgentPriority, AgentRelationType, CapabilityRisk, CapabilityMode,
    AssignmentState, TaxonomyError,
    AGENT_CATEGORIES, AGENT_HIERARCHY, AGENT_PRIORITIES, PRIORITY_RANK, AGENT_RELATION_TYPES,
    RELATION_TARGET_KINDS, CAPABILITY_RISK_LEVELS, CAPABILITY_RISK_RANK, CAPABILITY_MODES,
    ASSIGNMENT_STATES, ASSIGNMENT_TARGET_KINDS,
    is_category, validate_category, parent_of, ancestry, is_priority, priority_rank,
    is_relation, validate_relation, is_capability_risk, is_capability_mode,
    is_assignment_state, is_assignment_target, to_dict,
)

__all__ = [
    "AgentCategory", "AgentPriority", "AgentRelationType", "CapabilityRisk", "CapabilityMode",
    "AssignmentState", "TaxonomyError",
    "AGENT_CATEGORIES", "AGENT_HIERARCHY", "AGENT_PRIORITIES", "PRIORITY_RANK",
    "AGENT_RELATION_TYPES", "RELATION_TARGET_KINDS", "CAPABILITY_RISK_LEVELS",
    "CAPABILITY_RISK_RANK", "CAPABILITY_MODES", "ASSIGNMENT_STATES", "ASSIGNMENT_TARGET_KINDS",
    "is_category", "validate_category", "parent_of", "ancestry", "is_priority", "priority_rank",
    "is_relation", "validate_relation", "is_capability_risk", "is_capability_mode",
    "is_assignment_state", "is_assignment_target", "to_dict",
]
