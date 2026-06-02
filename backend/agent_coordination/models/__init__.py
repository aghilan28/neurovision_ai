"""Agent domain model package (V4-P5)."""

from __future__ import annotations

from .domain import (
    AgentMetadata, AgentCapability, AgentAssignment, AgentConstraintReference, AgentVersion,
    AgentAuditRecord, AgentRelationship, AgentGovernanceRecord, AgentLineageRecord,
    AgentRegistryRecord, AgentRecord,
)

__all__ = [
    "AgentMetadata", "AgentCapability", "AgentAssignment", "AgentConstraintReference",
    "AgentVersion", "AgentAuditRecord", "AgentRelationship", "AgentGovernanceRecord",
    "AgentLineageRecord", "AgentRegistryRecord", "AgentRecord",
]
