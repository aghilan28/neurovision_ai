"""The agent registry: governed, versioned, traceable agents + assignments (V4-P5).

No agent may exist outside the registry. Re-registering the same id + version with
different content is a forbidden silent overwrite. The registry tracks agents (type,
status, priority, capabilities, policy references, audit + lineage refs), the
versioned agent assignments, and the versioned agent relationships.
"""

from __future__ import annotations

from ..version import AGENT_REGISTRY_VERSION
from ..models.domain import AgentRegistryRecord, AgentAssignment, AgentRelationship


class AgentRegistry:
    """In-memory registry keyed by ``agent_id`` (+ assignment + relationship stores)."""

    def __init__(self) -> None:
        self._records: dict[str, AgentRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}
        self._assignments: dict[str, AgentAssignment] = {}
        self._relationships: dict[str, AgentRelationship] = {}

    # --- agents ---------------------------------------------------------------
    def register(self, record: AgentRegistryRecord) -> AgentRegistryRecord:
        key = (record.agent_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"agent {record.agent_id} version {record.version} already registered "
                "with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.agent_id] = record
        return record

    def get(self, agent_id: str) -> AgentRegistryRecord:
        if agent_id not in self._records:
            raise KeyError(f"agent {agent_id!r} not in registry")
        return self._records[agent_id]

    def exists(self, agent_id: str) -> bool:
        return agent_id in self._records

    def list_agents(self) -> list[str]:
        return sorted(self._records)

    def by_category(self, category: str) -> list[str]:
        return sorted(aid for aid, r in self._records.items() if r.category == category)

    def by_state(self, state: str) -> list[str]:
        return sorted(aid for aid, r in self._records.items() if r.state == state)

    # --- assignments ----------------------------------------------------------
    def register_assignment(self, a: AgentAssignment) -> AgentAssignment:
        # An assignment may be re-registered at a NEW version when its state evolves
        # (assigned -> completed/revoked). Re-registering the SAME version with
        # different content is a forbidden silent overwrite.
        existing = self._assignments.get(a.assignment_id)
        if existing is not None and existing.version == a.version \
                and existing.state_signature() != a.state_signature():
            raise ValueError(f"assignment {a.assignment_id} version {a.version} already "
                             "registered with different content (silent overwrite forbidden)")
        self._assignments[a.assignment_id] = a
        return a

    def assignment(self, assignment_id: str) -> AgentAssignment:
        if assignment_id not in self._assignments:
            raise KeyError(f"assignment {assignment_id!r} not in registry")
        return self._assignments[assignment_id]

    def list_assignments(self) -> list[str]:
        return sorted(self._assignments)

    def assignments_for(self, agent_id: str) -> list[AgentAssignment]:
        return [a for a in self._assignments.values() if a.agent_id == agent_id]

    def assignments_for_target(self, target_id: str) -> list[AgentAssignment]:
        return [a for a in self._assignments.values() if a.target_id == target_id]

    # --- relationships --------------------------------------------------------
    def register_relationship(self, rel: AgentRelationship) -> AgentRelationship:
        existing = self._relationships.get(rel.relationship_id)
        if existing is not None and existing.state_signature() != rel.state_signature():
            raise ValueError(f"relationship {rel.relationship_id} already registered with "
                             "different content (silent overwrite forbidden)")
        self._relationships[rel.relationship_id] = rel
        return rel

    def relationship(self, relationship_id: str) -> AgentRelationship:
        if relationship_id not in self._relationships:
            raise KeyError(f"relationship {relationship_id!r} not in registry")
        return self._relationships[relationship_id]

    def list_relationships(self) -> list[str]:
        return sorted(self._relationships)

    def to_dict(self) -> dict:
        return {"agent_registry_version": AGENT_REGISTRY_VERSION,
                "n_agents": len(self._records), "n_assignments": len(self._assignments),
                "n_relationships": len(self._relationships),
                "agents": {aid: r.to_dict() for aid, r in sorted(self._records.items())},
                "assignments": {aid: a.to_dict()
                                for aid, a in sorted(self._assignments.items())},
                "relationships": {rid: r.to_dict()
                                  for rid, r in sorted(self._relationships.items())}}
