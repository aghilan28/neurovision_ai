"""Immutable, versioned artifact base types.

Every artifact produced by the intelligence layer (and, via reuse, the decision
layer) carries a stable identity, a content hash, and a monotonic version. All
artifact dataclasses are ``frozen`` so that, once minted, an artifact cannot be
mutated in place — a precondition for auditability (AP-8) and traceability
(AP-5/NR-11).

Artifact dataclasses use ``kw_only=True`` so that subclasses may add required
fields without colliding with the base class's defaulted fields.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, ClassVar, Mapping

from backend.multi_case_intelligence.schemas.determinism import (
    content_hash,
    deterministic_id,
)


class ArtifactKind(str, Enum):
    """Every kind of artifact tracked by the registry/lineage/audit systems."""

    # --- Source (upstream) kinds: never produced here, only referenced. ---
    PATIENT = "patient"
    CASE = "case"
    STUDY = "study"
    REVIEW = "review"
    EVIDENCE = "evidence"
    FINDING = "finding"
    INTERPRETATION = "interpretation"
    KNOWLEDGE = "knowledge"

    # --- Intelligence (V2-P5) kinds. ---
    COHORT = "cohort"
    ANALYTICS = "analytics"
    TREND = "trend"
    QUALITY = "quality"
    REPORT = "report"

    # --- Decision support (V2-P6) kinds. ---
    DECISION_CONTEXT = "decision_context"
    EVIDENCE_BUNDLE = "evidence_bundle"
    RISK_CONTEXT = "risk_context"
    PRIORITIZATION = "prioritization"
    GUIDANCE = "guidance"
    DECISION_SUPPORT = "decision_support"
    DECISION_REPORT = "decision_report"


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    """A stable, comparable reference to an artifact: ``(kind, id)``.

    Optionally pins a ``content_hash`` and ``version`` so a consumer can prove it
    is pointing at an exact revision.
    """

    kind: ArtifactKind
    id: str
    content_hash: str | None = None
    version: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ArtifactKind):
            object.__setattr__(self, "kind", ArtifactKind(self.kind))
        if not self.id:
            raise ValueError("ArtifactRef.id must be non-empty")

    @property
    def key(self) -> tuple[str, str]:
        """Registry key: ``(kind, id)``."""
        return (self.kind.value, self.id)


@dataclass(frozen=True, kw_only=True)
class VersionedArtifact:
    """Base class for every intelligence/decision artifact.

    Subclasses add their own payload fields. ``version`` is a monotonic integer
    assigned by the registry when a new revision of the same logical id is
    admitted; it is excluded from the content hash so identical content keeps a
    stable hash across versions.
    """

    id: str
    version: int = 1
    schema_version: str = "v2.p5.1"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    KIND: ClassVar[ArtifactKind] = ArtifactKind.REPORT

    def payload(self) -> Mapping[str, Any]:
        """The content-bearing fields used for hashing (everything but version)."""
        data = dict(asdict(self))
        data.pop("version", None)
        return data

    def compute_hash(self) -> str:
        """Reproducible content hash of this artifact."""
        return content_hash({"kind": self.KIND.value, "payload": self.payload()})

    def ref(self) -> ArtifactRef:
        """A reference pinned to this artifact's exact revision."""
        return ArtifactRef(
            kind=self.KIND,
            id=self.id,
            content_hash=self.compute_hash(),
            version=self.version,
        )

    @classmethod
    def mint_id(cls, *parts: Any) -> str:
        """Mint a content-addressed id for this artifact kind."""
        return deterministic_id(cls.KIND.value, *parts)
