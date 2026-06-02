"""Lineage schema structures (data-layer provenance graph).

Lineage makes **every artifact traceable** (AP-5, NR-11). A :class:`LineageRecord`
is a node describing how one artifact was produced: its type, the operation and
operation version that created it, the inputs it derived from (edges), and a
fingerprint of the parameters used. Records compose into a directed acyclic
provenance graph (raw file -> validation -> metadata -> dataset version -> ...
future preprocessing artifacts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class LineageEdge:
    """A typed dependency from a produced artifact to one of its inputs."""

    input_id: str
    input_type: str
    relation: str = "derived_from"

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_id": self.input_id,
            "input_type": self.input_type,
            "relation": self.relation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LineageEdge:
        return cls(
            input_id=data["input_id"],
            input_type=data["input_type"],
            relation=data.get("relation", "derived_from"),
        )


@dataclass(frozen=True, slots=True)
class LineageRecord:
    """One node in the provenance DAG.

    ``params_fingerprint`` is a content fingerprint of the parameters/config the
    operation used; together with ``operation_version`` it is what lets a reviewer
    confirm an artifact was produced exactly as claimed (reproducibility, AP-6).
    """

    artifact_id: str
    artifact_type: str
    operation: str
    operation_version: str
    inputs: tuple[LineageEdge, ...] = ()
    params_fingerprint: str | None = None
    content_fingerprint: str | None = None
    recorded_at: str | None = None  # provenance only
    attributes: dict[str, Any] = field(default_factory=dict)

    def input_ids(self) -> tuple[str, ...]:
        return tuple(e.input_id for e in self.inputs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "operation": self.operation,
            "operation_version": self.operation_version,
            "inputs": [e.to_dict() for e in self.inputs],
            "params_fingerprint": self.params_fingerprint,
            "content_fingerprint": self.content_fingerprint,
            "recorded_at": self.recorded_at,
            "attributes": self.attributes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LineageRecord:
        return cls(
            artifact_id=data["artifact_id"],
            artifact_type=data["artifact_type"],
            operation=data["operation"],
            operation_version=data["operation_version"],
            inputs=tuple(LineageEdge.from_dict(e) for e in data.get("inputs", [])),
            params_fingerprint=data.get("params_fingerprint"),
            content_fingerprint=data.get("content_fingerprint"),
            recorded_at=data.get("recorded_at"),
            attributes=dict(data.get("attributes", {})),
        )
