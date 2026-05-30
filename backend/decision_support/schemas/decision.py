"""Decision-support artifact schemas.

All artifacts are :class:`VersionedArtifact` subclasses (frozen, content-hashed,
referenceable), reusing the shared identity foundation from the intelligence
layer. They embed only *references* and *derived* values — never source records —
so the decision layer cannot alter clinical truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Mapping

from backend.multi_case_intelligence.schemas.base import (
    ArtifactKind,
    ArtifactRef,
    VersionedArtifact,
)

DECISION_SCHEMA_VERSION = "v2.p6.1"


# --------------------------------------------------------------------------- #
# Decision context
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, kw_only=True)
class DecisionContext(VersionedArtifact):
    """A deterministic, fully-referenced aggregation of one case's context.

    ``population_context`` optionally embeds derived intelligence (e.g. how a
    finding category's frequency compares across the population) — by *value*,
    never by mutating the intelligence artifact.
    """

    patient_ref: ArtifactRef
    case_ref: ArtifactRef
    review_refs: tuple[ArtifactRef, ...] = ()
    finding_refs: tuple[ArtifactRef, ...] = ()
    interpretation_refs: tuple[ArtifactRef, ...] = ()
    knowledge_refs: tuple[ArtifactRef, ...] = ()
    evidence_refs: tuple[ArtifactRef, ...] = ()
    completeness: Mapping[str, float] = field(default_factory=dict)
    counts: Mapping[str, int] = field(default_factory=dict)
    population_context: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = DECISION_SCHEMA_VERSION

    KIND: ClassVar[ArtifactKind] = ArtifactKind.DECISION_CONTEXT

    def all_source_refs(self) -> tuple[ArtifactRef, ...]:
        return (
            (self.patient_ref, self.case_ref)
            + self.review_refs
            + self.finding_refs
            + self.interpretation_refs
            + self.knowledge_refs
            + self.evidence_refs
        )


# --------------------------------------------------------------------------- #
# Evidence bundling
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class EvidenceSummary:
    """A single ranked evidence item summary (the evidence is never hidden)."""

    evidence_ref: ArtifactRef
    finding_id: str | None
    modality: str
    confidence: float
    abstained: bool
    rank: int


@dataclass(frozen=True, kw_only=True)
class EvidenceBundle(VersionedArtifact):
    """All evidence for a context, deterministically ranked."""

    context_ref: ArtifactRef
    items: tuple[EvidenceSummary, ...] = ()
    ranking: tuple[str, ...] = ()  # evidence ids in ranked order
    schema_version: str = DECISION_SCHEMA_VERSION

    KIND: ClassVar[ArtifactKind] = ArtifactKind.EVIDENCE_BUNDLE

    @property
    def size(self) -> int:
        return len(self.items)


# --------------------------------------------------------------------------- #
# Risk context
# --------------------------------------------------------------------------- #
class RiskBand(str, Enum):
    """Decision-support risk banding (review attention, NOT clinical risk)."""

    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"


@dataclass(frozen=True, slots=True)
class RiskComponent:
    """One explainable risk component with its basis."""

    name: str
    value: float  # [0, 1]
    basis: str


@dataclass(frozen=True, kw_only=True)
class RiskContext(VersionedArtifact):
    """Aggregated, explainable risk context for a decision context."""

    context_ref: ArtifactRef
    components: tuple[RiskComponent, ...] = ()
    aggregate: float = 0.0
    band: RiskBand = RiskBand.LOW
    schema_version: str = DECISION_SCHEMA_VERSION

    KIND: ClassVar[ArtifactKind] = ArtifactKind.RISK_CONTEXT

    def component(self, name: str) -> RiskComponent | None:
        for c in self.components:
            if c.name == name:
                return c
        return None


# --------------------------------------------------------------------------- #
# Prioritization
# --------------------------------------------------------------------------- #
class PriorityLevel(str, Enum):
    """Review-priority levels (ordering of reviewer attention, not triage orders)."""

    ROUTINE = "routine"
    ELEVATED = "elevated"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class PriorityFactor:
    """A single explainable contributor to a priority score."""

    name: str
    contribution: float
    detail: str


@dataclass(frozen=True, kw_only=True)
class PrioritizationRecord(VersionedArtifact):
    """An explainable review-priority assignment for a context."""

    context_ref: ArtifactRef
    level: PriorityLevel
    score: float
    reason: str
    factors: tuple[PriorityFactor, ...] = ()
    supporting_evidence: tuple[ArtifactRef, ...] = ()
    risk_context_ref: ArtifactRef | None = None
    knowledge_refs: tuple[ArtifactRef, ...] = ()
    schema_version: str = DECISION_SCHEMA_VERSION

    KIND: ClassVar[ArtifactKind] = ArtifactKind.PRIORITIZATION


# --------------------------------------------------------------------------- #
# Guidance
# --------------------------------------------------------------------------- #
class GuidanceCategory(str, Enum):
    """Permitted guidance categories. Diagnosis/treatment are intentionally absent."""

    REVIEW = "review"
    EVIDENCE = "evidence"
    KNOWLEDGE = "knowledge"
    INVESTIGATION = "investigation"
    RISK = "risk"


@dataclass(frozen=True, slots=True)
class GuidanceItem:
    """A single explainable guidance statement with references."""

    category: GuidanceCategory
    message: str
    rationale: str
    references: tuple[ArtifactRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.category, GuidanceCategory):
            object.__setattr__(self, "category", GuidanceCategory(self.category))


@dataclass(frozen=True, kw_only=True)
class GuidanceRecord(VersionedArtifact):
    """A set of review/evidence/knowledge/investigation/risk guidance items."""

    context_ref: ArtifactRef
    items: tuple[GuidanceItem, ...] = ()
    schema_version: str = DECISION_SCHEMA_VERSION

    KIND: ClassVar[ArtifactKind] = ArtifactKind.GUIDANCE


# --------------------------------------------------------------------------- #
# Decision support record + version
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, kw_only=True)
class DecisionSupportRecord(VersionedArtifact):
    """The top-level bundle tying together all decision-support artifacts."""

    patient_ref: ArtifactRef
    case_ref: ArtifactRef
    context_ref: ArtifactRef
    evidence_bundle_ref: ArtifactRef
    risk_context_ref: ArtifactRef
    prioritization_ref: ArtifactRef
    guidance_ref: ArtifactRef
    explanation: str = ""
    schema_version: str = DECISION_SCHEMA_VERSION

    KIND: ClassVar[ArtifactKind] = ArtifactKind.DECISION_SUPPORT

    def component_refs(self) -> tuple[ArtifactRef, ...]:
        return (
            self.context_ref,
            self.evidence_bundle_ref,
            self.risk_context_ref,
            self.prioritization_ref,
            self.guidance_ref,
        )


@dataclass(frozen=True, slots=True)
class DecisionVersion:
    """A versioning record for a decision artifact (the ``DecisionVersion`` entity).

    Captures the content hash of a revision plus the prior revision's hash so a
    consumer can reconstruct the revision history of any decision artifact.
    """

    subject: ArtifactRef
    version: int
    content_hash: str
    prev_content_hash: str | None = None


@dataclass(frozen=True, kw_only=True)
class DecisionReport(VersionedArtifact):
    """A human-readable, fully-referenced decision-support report."""

    report_type: str  # decision_support | guidance | evidence | risk | prioritization | validation
    title: str
    sections: Mapping[str, Any] = field(default_factory=dict)
    referenced: tuple[ArtifactRef, ...] = ()
    schema_version: str = DECISION_SCHEMA_VERSION

    KIND: ClassVar[ArtifactKind] = ArtifactKind.DECISION_REPORT
