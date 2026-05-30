"""Immutable audit-event and lineage-record models.

These models are shared in spirit by both V2-P5 and V2-P6 (each subsystem keeps
its own log/tracker instances, but the record shapes are identical so that audit
and lineage trails are uniform across the platform).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from backend.multi_case_intelligence.schemas.base import ArtifactRef
from backend.multi_case_intelligence.schemas.determinism import (
    GENESIS_HASH,
    content_hash,
    hash_chain,
)


class AuditAction(str, Enum):
    """The closed set of auditable actions.

    Note the *absence* of any ``UPDATE``/``DELETE`` of source data: source
    clinical artifacts are immutable and are never written by these subsystems.
    """

    CREATE = "create"
    REGISTER = "register"
    VERSION = "version"
    VALIDATE = "validate"
    REPORT = "report"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """A single immutable entry in an append-only, hash-chained audit log.

    ``sequence`` is a *logical* clock (a monotonically increasing integer
    assigned by the log) — never a wall-clock timestamp — so the log is fully
    deterministic and reproducible. ``prev_hash``/``entry_hash`` form a
    tamper-evident chain (altering any earlier entry changes all later hashes).
    """

    sequence: int
    action: AuditAction
    subject: ArtifactRef
    summary: str
    details: Mapping[str, Any] = field(default_factory=dict)
    prev_hash: str = GENESIS_HASH
    entry_hash: str = ""

    def computed_hash(self) -> str:
        """Recompute this entry's chain hash from its content + ``prev_hash``."""
        return hash_chain(
            self.prev_hash,
            {
                "sequence": self.sequence,
                "action": self.action.value,
                "subject": {
                    "kind": self.subject.kind.value,
                    "id": self.subject.id,
                    "content_hash": self.subject.content_hash,
                    "version": self.subject.version,
                },
                "summary": self.summary,
                "details": dict(self.details),
            },
        )

    def is_valid(self) -> bool:
        """True iff the stored ``entry_hash`` matches the recomputed hash."""
        return bool(self.entry_hash) and self.entry_hash == self.computed_hash()


@dataclass(frozen=True, slots=True)
class LineageEdge:
    """A directed provenance edge: ``child`` was derived from ``parent``."""

    child: ArtifactRef
    parent: ArtifactRef
    relation: str = "derived_from"


@dataclass(frozen=True, slots=True)
class LineageRecord:
    """The complete provenance of one artifact.

    ``roots`` are the upstream source artifacts (patients/cases/...) the artifact
    ultimately traces to; ``edges`` are the immediate parent relationships. The
    record is content-hashed so it is itself versioned and tamper-evident.
    """

    subject: ArtifactRef
    edges: tuple[LineageEdge, ...] = ()
    roots: tuple[ArtifactRef, ...] = ()

    def parents(self) -> tuple[ArtifactRef, ...]:
        """Immediate parents of the subject."""
        return tuple(edge.parent for edge in self.edges)

    def record_hash(self) -> str:
        """Reproducible content hash of this lineage record."""
        return content_hash(
            {
                "subject": (self.subject.kind.value, self.subject.id),
                "edges": [
                    (e.child.key, e.parent.key, e.relation) for e in self.edges
                ],
                "roots": [r.key for r in self.roots],
            }
        )
