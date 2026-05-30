"""Intelligence artifact schemas (V2-P5 outputs).

All of these are :class:`VersionedArtifact` subclasses: versioned, content
hashed, referenceable, and (because they are ``frozen``) immutable once minted.
None of them embed source records — only *references* and derived statistics —
so they cannot alter source truth.
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


# --------------------------------------------------------------------------- #
# Cohorts
# --------------------------------------------------------------------------- #
class Combinator(str, Enum):
    AND = "and"
    OR = "or"


@dataclass(frozen=True, slots=True)
class Criterion:
    """A single deterministic, serializable selection predicate.

    ``field`` is a key into the *normalized* projection of a source record (see
    ``cohorts.builder``); ``op`` is one of a closed, explainable set.
    """

    field: str
    op: str  # eq | ne | in | gte | lte | exists | contains
    value: Any = None

    VALID_OPS: ClassVar[frozenset[str]] = frozenset(
        {"eq", "ne", "in", "gte", "lte", "exists", "contains"}
    )

    def __post_init__(self) -> None:
        if self.op not in self.VALID_OPS:
            raise ValueError(f"unsupported op {self.op!r}; valid: {sorted(self.VALID_OPS)}")


@dataclass(frozen=True, slots=True)
class SelectionCriteria:
    """The reproducible definition of *who is in* a cohort."""

    member_kind: ArtifactKind
    clauses: tuple[Criterion, ...] = ()
    combinator: Combinator = Combinator.AND
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.member_kind, ArtifactKind):
            object.__setattr__(self, "member_kind", ArtifactKind(self.member_kind))
        if not isinstance(self.combinator, Combinator):
            object.__setattr__(self, "combinator", Combinator(self.combinator))


@dataclass(frozen=True, kw_only=True)
class Cohort(VersionedArtifact):
    """A versioned set of source-artifact members selected by criteria."""

    member_kind: ArtifactKind
    criteria: SelectionCriteria
    members: tuple[str, ...]  # sorted member ids (selection result)
    member_refs: tuple[ArtifactRef, ...] = ()

    KIND: ClassVar[ArtifactKind] = ArtifactKind.COHORT

    @property
    def size(self) -> int:
        return len(self.members)


# --------------------------------------------------------------------------- #
# Population analytics
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class Distribution:
    """A categorical distribution over a single field."""

    field: str
    counts: tuple[tuple[str, int], ...]  # (category, count), sorted by category
    total: int


@dataclass(frozen=True, slots=True)
class StatisticBlock:
    """Statistics for one population of a single subject kind."""

    subject_kind: ArtifactKind
    count: int
    distributions: tuple[Distribution, ...] = ()
    coverage: Mapping[str, float] = field(default_factory=dict)
    variability: Mapping[str, float] = field(default_factory=dict)
    frequency: Mapping[str, float] = field(default_factory=dict)
    confidence: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class PopulationAnalytics(VersionedArtifact):
    """A versioned bundle of statistic blocks for a scope (cohort or whole pop)."""

    scope: str
    cohort_ref: ArtifactRef | None = None
    blocks: tuple[StatisticBlock, ...] = ()

    KIND: ClassVar[ArtifactKind] = ArtifactKind.ANALYTICS

    def block(self, kind: ArtifactKind) -> StatisticBlock | None:
        for b in self.blocks:
            if b.subject_kind == kind:
                return b
        return None


# --------------------------------------------------------------------------- #
# Trends
# --------------------------------------------------------------------------- #
class TrendDirection(str, Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    FLAT = "flat"
    INSUFFICIENT = "insufficient_data"


@dataclass(frozen=True, slots=True)
class TrendPoint:
    """A single ordered observation in a trend series."""

    bucket: str  # deterministic ordinal bucket label (never a wall-clock time)
    value: float
    count: int


@dataclass(frozen=True, slots=True)
class TrendSeries:
    """An ordered series for one metric over a deterministic ordinal dimension."""

    metric: str
    subject_kind: ArtifactKind
    points: tuple[TrendPoint, ...]
    direction: TrendDirection
    delta: float  # value(last) - value(first), quantized


@dataclass(frozen=True, kw_only=True)
class Trend(VersionedArtifact):
    """A versioned bundle of trend series."""

    scope: str
    series: tuple[TrendSeries, ...] = ()
    cohort_ref: ArtifactRef | None = None

    KIND: ClassVar[ArtifactKind] = ArtifactKind.TREND


# --------------------------------------------------------------------------- #
# Quality analytics
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class QualityMetric:
    """A single explainable quality metric (a ratio with its numerator/denom)."""

    name: str
    value: float  # in [0, 1]
    numerator: int
    denominator: int
    description: str = ""


@dataclass(frozen=True, kw_only=True)
class QualityReport(VersionedArtifact):
    """A versioned bundle of quality metrics across review/finding/evidence/etc."""

    scope: str
    metrics: tuple[QualityMetric, ...] = ()
    cohort_ref: ArtifactRef | None = None

    KIND: ClassVar[ArtifactKind] = ArtifactKind.QUALITY

    def metric(self, name: str) -> QualityMetric | None:
        for m in self.metrics:
            if m.name == name:
                return m
        return None


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, kw_only=True)
class IntelligenceReport(VersionedArtifact):
    """A human-readable, fully-referenced report rolling up other artifacts."""

    report_type: str  # cohort | analytics | trend | population | quality | validation
    title: str
    sections: Mapping[str, Any] = field(default_factory=dict)
    referenced: tuple[ArtifactRef, ...] = ()

    KIND: ClassVar[ArtifactKind] = ArtifactKind.REPORT
