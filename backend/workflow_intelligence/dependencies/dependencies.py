"""Dependency engine (V3-P3).

Derives directed dependencies between operational entities from their *recorded*
relationships (the V2 structural links carried on the events' source entities). A
case "owns" its reviews; a review "produces" findings; findings link to knowledge.
The engine only reports dependencies it can observe from supplied entity refs — it
invents nothing.

Each dependency is classified with one of the mandated relations:
upstream | downstream | blocked | waiting | completed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..models.domain import WorkflowDependency


def _dep_id(from_entity: str, to_entity: str, relation: str) -> str:
    return f"workflowdep+{hash_obj({'f': from_entity, 't': to_entity, 'r': relation})}"


@dataclass(frozen=True)
class EntityRef:
    """A minimal, read-only reference to a V2/V3 entity for dependency derivation."""

    entity_id: str
    kind: str                       # case|review|finding|knowledge|decision|workflow
    parent_id: Optional[str] = None  # the upstream entity it depends on, if any
    completed: bool = False


def derive_dependencies(refs: Sequence[EntityRef]) -> list[WorkflowDependency]:
    """Build dependency edges from parent links among the supplied refs.

    For each ref with a ``parent_id`` present in the set we emit a downstream edge
    (parent -> child) and an upstream edge (child -> parent). The edge relation is
    ``completed`` when the child is done, else ``waiting`` (the child waits on its
    parent), and ``blocked`` when the parent is not completed but the child exists.
    """
    by_id = {r.entity_id: r for r in refs}
    deps: list[WorkflowDependency] = []
    for r in refs:
        if not r.parent_id or r.parent_id not in by_id:
            continue
        parent = by_id[r.parent_id]
        # downstream: parent -> child
        down_rel = "completed" if r.completed else ("blocked" if not parent.completed else "downstream")
        deps.append(WorkflowDependency(
            dependency_id=_dep_id(parent.entity_id, r.entity_id, down_rel),
            from_entity=parent.entity_id, from_kind=parent.kind,
            to_entity=r.entity_id, to_kind=r.kind, relation=down_rel))
        # upstream: child -> parent
        up_rel = "completed" if parent.completed else "waiting"
        deps.append(WorkflowDependency(
            dependency_id=_dep_id(r.entity_id, parent.entity_id, up_rel),
            from_entity=r.entity_id, from_kind=r.kind,
            to_entity=parent.entity_id, to_kind=parent.kind, relation=up_rel))
    deps.sort(key=lambda d: (d.from_entity, d.to_entity, d.relation))
    return deps
