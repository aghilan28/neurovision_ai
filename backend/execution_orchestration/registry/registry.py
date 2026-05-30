"""The execution registry: governed, versioned, traceable executions (V4-P6).

No execution may exist outside the registry. Re-registering the same id + version
with different content is a forbidden silent overwrite. The registry tracks
executions (source task, assignment, status, policy references, audit + lineage
refs) and the versioned execution relationships.
"""

from __future__ import annotations

from ..version import EXECUTION_REGISTRY_VERSION
from ..models.domain import ExecutionRegistryRecord, ExecutionRelationship


class ExecutionRegistry:
    """In-memory registry keyed by ``execution_id`` (+ a relationship store)."""

    def __init__(self) -> None:
        self._records: dict[str, ExecutionRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}
        self._relationships: dict[str, ExecutionRelationship] = {}

    # --- executions -----------------------------------------------------------
    def register(self, record: ExecutionRegistryRecord) -> ExecutionRegistryRecord:
        key = (record.execution_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"execution {record.execution_id} version {record.version} already registered "
                "with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.execution_id] = record
        return record

    def get(self, execution_id: str) -> ExecutionRegistryRecord:
        if execution_id not in self._records:
            raise KeyError(f"execution {execution_id!r} not in registry")
        return self._records[execution_id]

    def exists(self, execution_id: str) -> bool:
        return execution_id in self._records

    def list_executions(self) -> list[str]:
        return sorted(self._records)

    def by_state(self, state: str) -> list[str]:
        return sorted(eid for eid, r in self._records.items() if r.state == state)

    def for_task(self, task_id: str) -> list[str]:
        return sorted(eid for eid, r in self._records.items() if r.source_task_id == task_id)

    def for_assignment(self, assignment_id: str) -> list[str]:
        return sorted(eid for eid, r in self._records.items()
                      if r.assignment_id == assignment_id)

    # --- relationships --------------------------------------------------------
    def register_relationship(self, rel: ExecutionRelationship) -> ExecutionRelationship:
        existing = self._relationships.get(rel.relationship_id)
        if existing is not None and existing.state_signature() != rel.state_signature():
            raise ValueError(f"relationship {rel.relationship_id} already registered with "
                             "different content (silent overwrite forbidden)")
        self._relationships[rel.relationship_id] = rel
        return rel

    def relationship(self, relationship_id: str) -> ExecutionRelationship:
        if relationship_id not in self._relationships:
            raise KeyError(f"relationship {relationship_id!r} not in registry")
        return self._relationships[relationship_id]

    def list_relationships(self) -> list[str]:
        return sorted(self._relationships)

    def to_dict(self) -> dict:
        return {"execution_registry_version": EXECUTION_REGISTRY_VERSION,
                "n_executions": len(self._records), "n_relationships": len(self._relationships),
                "executions": {eid: r.to_dict() for eid, r in sorted(self._records.items())},
                "relationships": {rid: r.to_dict()
                                  for rid, r in sorted(self._relationships.items())}}
