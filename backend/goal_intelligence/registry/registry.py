"""The goal registry: governed, versioned, traceable goals + relationships (V4-P1).

No goal may exist outside the registry. Re-registering the same id + version with
different content is a forbidden silent overwrite. The registry tracks goals (type,
status, priority, version, dependencies, constraints, audit + lineage refs) and the
versioned goal relationships.
"""

from __future__ import annotations

from ..version import GOAL_REGISTRY_VERSION
from ..models.domain import GoalRegistryRecord, GoalRelationship


class GoalRegistry:
    """In-memory registry keyed by ``goal_id`` (+ a relationship store)."""

    def __init__(self) -> None:
        self._records: dict[str, GoalRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}
        self._relationships: dict[str, GoalRelationship] = {}

    # --- goals ----------------------------------------------------------------
    def register(self, record: GoalRegistryRecord) -> GoalRegistryRecord:
        key = (record.goal_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"goal {record.goal_id} version {record.version} already registered "
                "with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.goal_id] = record
        return record

    def get(self, goal_id: str) -> GoalRegistryRecord:
        if goal_id not in self._records:
            raise KeyError(f"goal {goal_id!r} not in registry")
        return self._records[goal_id]

    def exists(self, goal_id: str) -> bool:
        return goal_id in self._records

    def list_goals(self) -> list[str]:
        return sorted(self._records)

    def by_category(self, category: str) -> list[str]:
        return sorted(gid for gid, r in self._records.items() if r.category == category)

    def by_state(self, state: str) -> list[str]:
        return sorted(gid for gid, r in self._records.items() if r.state == state)

    # --- relationships --------------------------------------------------------
    def register_relationship(self, rel: GoalRelationship) -> GoalRelationship:
        existing = self._relationships.get(rel.relationship_id)
        if existing is not None and existing.state_signature() != rel.state_signature():
            raise ValueError(f"relationship {rel.relationship_id} already registered with "
                             "different content (silent overwrite forbidden)")
        self._relationships[rel.relationship_id] = rel
        return rel

    def relationship(self, relationship_id: str) -> GoalRelationship:
        if relationship_id not in self._relationships:
            raise KeyError(f"relationship {relationship_id!r} not in registry")
        return self._relationships[relationship_id]

    def list_relationships(self) -> list[str]:
        return sorted(self._relationships)

    def relationships_for(self, goal_id: str) -> list[GoalRelationship]:
        return [r for r in self._relationships.values() if r.source_goal_id == goal_id]

    def to_dict(self) -> dict:
        return {"goal_registry_version": GOAL_REGISTRY_VERSION,
                "n_goals": len(self._records), "n_relationships": len(self._relationships),
                "goals": {gid: r.to_dict() for gid, r in sorted(self._records.items())},
                "relationships": {rid: r.to_dict()
                                  for rid, r in sorted(self._relationships.items())}}
