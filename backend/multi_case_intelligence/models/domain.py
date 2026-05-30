"""Multi-case intelligence domain entities (V2-P5).

Pure data + ``to_dict`` + ``signature``. These shapes describe *intelligence about
populations* — cohorts, population analytics, trends, quality reports, summary
reports. They are derived, descriptive artifacts: they reference source ids and
carry computed statistics, and they encode **no** diagnosis, prediction, or
decision logic (those are forbidden / V2-P6+ scope).

Every artifact is versioned (a per-artifact hash chain), lineage-tracked, and
audited; the orchestration that produces them lives in ``service.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    INTEL_DOMAIN_VERSION, INTEL_COHORT_VERSION, INTEL_ANALYTICS_VERSION,
    INTEL_TREND_VERSION, INTEL_QUALITY_VERSION, INTEL_REGISTRY_VERSION,
    DETERMINISTIC_EPOCH,
)


class CohortKind(str, Enum):
    """The source-artifact kinds a cohort can be built over."""

    CASE = "case"
    REVIEW = "review"
    FINDING = "finding"
    INTERPRETATION = "interpretation"
    CONCEPT = "concept"


# --- cohorts ------------------------------------------------------------------
@dataclass(frozen=True)
class CohortCriterion:
    """A single deterministic, serializable selection predicate."""

    field: str
    op: str            # eq|ne|in|gte|lte|exists|contains
    value: object = None

    VALID_OPS = frozenset({"eq", "ne", "in", "gte", "lte", "exists", "contains"})

    def __post_init__(self) -> None:
        if self.op not in self.VALID_OPS:
            raise ValueError(f"unsupported cohort op {self.op!r}")

    def to_dict(self) -> dict:
        return {"field": self.field, "op": self.op, "value": self.value}


@dataclass(frozen=True)
class CohortDefinition:
    """The reproducible definition of *who is in* a cohort."""

    member_kind: CohortKind
    criteria: tuple[CohortCriterion, ...] = ()
    combinator: str = "and"     # and|or
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.member_kind, CohortKind):
            object.__setattr__(self, "member_kind", CohortKind(self.member_kind))
        if self.combinator not in ("and", "or"):
            raise ValueError("combinator must be 'and' or 'or'")

    def signature(self) -> str:
        return hash_obj(self.to_dict())

    def to_dict(self) -> dict:
        return {"member_kind": self.member_kind.value,
                "criteria": [c.to_dict() for c in self.criteria],
                "combinator": self.combinator, "description": self.description}


@dataclass(frozen=True)
class Cohort:
    """A versioned set of source-artifact members selected by a definition."""

    cohort_id: str
    definition: CohortDefinition
    members: tuple[str, ...]
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = INTEL_COHORT_VERSION

    @property
    def member_kind(self) -> str:
        return self.definition.member_kind.value

    @property
    def size(self) -> int:
        return len(self.members)

    def state_signature(self) -> str:
        return hash_obj({"cohort_id": self.cohort_id, "definition": self.definition.to_dict(),
                         "members": list(self.members)})

    def to_dict(self) -> dict:
        return {"cohort_id": self.cohort_id, "member_kind": self.member_kind,
                "definition": self.definition.to_dict(), "members": list(self.members),
                "size": self.size, "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state, "domain_version": self.domain_version,
                "state_signature": self.state_signature()}


# --- population analytics -----------------------------------------------------
@dataclass(frozen=True)
class StatisticBlock:
    """Statistics for one population of a single subject kind."""

    subject_kind: str
    count: int
    distributions: dict = field(default_factory=dict)   # field -> {counts, total}
    coverage: dict = field(default_factory=dict)         # name -> {ratio,num,den}
    variability: dict = field(default_factory=dict)      # name -> float
    frequency: dict = field(default_factory=dict)        # category -> float
    confidence: dict = field(default_factory=dict)       # name -> float

    def to_dict(self) -> dict:
        return {"subject_kind": self.subject_kind, "count": self.count,
                "distributions": self.distributions, "coverage": self.coverage,
                "variability": self.variability, "frequency": self.frequency,
                "confidence": self.confidence}


@dataclass(frozen=True)
class PopulationAnalytics:
    """A versioned bundle of statistic blocks for a scope (population or cohort)."""

    analytics_id: str
    scope: str
    blocks: tuple[StatisticBlock, ...] = ()
    cohort_id: Optional[str] = None
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = INTEL_ANALYTICS_VERSION

    def block(self, subject_kind: str) -> Optional[StatisticBlock]:
        for b in self.blocks:
            if b.subject_kind == subject_kind:
                return b
        return None

    def state_signature(self) -> str:
        return hash_obj({"analytics_id": self.analytics_id, "scope": self.scope,
                         "cohort_id": self.cohort_id,
                         "blocks": [b.to_dict() for b in self.blocks]})

    def to_dict(self) -> dict:
        return {"analytics_id": self.analytics_id, "scope": self.scope,
                "cohort_id": self.cohort_id, "blocks": [b.to_dict() for b in self.blocks],
                "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state, "domain_version": self.domain_version,
                "state_signature": self.state_signature()}


# --- trends -------------------------------------------------------------------
@dataclass(frozen=True)
class TrendPoint:
    """A single ordered observation (over a deterministic ordinal dimension)."""

    bucket: str
    value: float
    n: int

    def to_dict(self) -> dict:
        return {"bucket": self.bucket, "value": self.value, "n": self.n}


@dataclass(frozen=True)
class TrendSeries:
    metric: str
    subject_kind: str
    dimension: str                 # the deterministic ordering dimension
    points: tuple[TrendPoint, ...]
    direction: str                 # increasing|decreasing|flat|insufficient_data
    delta: float

    def to_dict(self) -> dict:
        return {"metric": self.metric, "subject_kind": self.subject_kind,
                "dimension": self.dimension, "points": [p.to_dict() for p in self.points],
                "direction": self.direction, "delta": self.delta}


@dataclass(frozen=True)
class Trend:
    trend_id: str
    scope: str
    series: tuple[TrendSeries, ...] = ()
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = INTEL_TREND_VERSION

    def state_signature(self) -> str:
        return hash_obj({"trend_id": self.trend_id, "scope": self.scope,
                         "series": [s.to_dict() for s in self.series]})

    def to_dict(self) -> dict:
        return {"trend_id": self.trend_id, "scope": self.scope,
                "series": [s.to_dict() for s in self.series], "version": self.version,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "domain_version": self.domain_version, "state_signature": self.state_signature()}


# --- quality ------------------------------------------------------------------
@dataclass(frozen=True)
class QualityMetric:
    name: str
    value: float
    numerator: int
    denominator: int
    description: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "value": self.value, "numerator": self.numerator,
                "denominator": self.denominator, "description": self.description}


@dataclass(frozen=True)
class QualityReport:
    quality_id: str
    scope: str
    metrics: tuple[QualityMetric, ...] = ()
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = INTEL_QUALITY_VERSION

    def metric(self, name: str) -> Optional[QualityMetric]:
        for m in self.metrics:
            if m.name == name:
                return m
        return None

    def state_signature(self) -> str:
        return hash_obj({"quality_id": self.quality_id, "scope": self.scope,
                         "metrics": [m.to_dict() for m in self.metrics]})

    def to_dict(self) -> dict:
        return {"quality_id": self.quality_id, "scope": self.scope,
                "metrics": [m.to_dict() for m in self.metrics], "version": self.version,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "domain_version": self.domain_version, "state_signature": self.state_signature()}


# --- summary report -----------------------------------------------------------
@dataclass(frozen=True)
class IntelligenceReport:
    report_id: str
    report_type: str
    scope: str
    sections: dict = field(default_factory=dict)
    references: tuple[str, ...] = ()
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = INTEL_DOMAIN_VERSION

    def state_signature(self) -> str:
        return hash_obj({"report_id": self.report_id, "report_type": self.report_type,
                         "scope": self.scope, "sections": self.sections,
                         "references": list(self.references)})

    def to_dict(self) -> dict:
        return {"report_id": self.report_id, "report_type": self.report_type, "scope": self.scope,
                "sections": self.sections, "references": list(self.references),
                "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state, "domain_version": self.domain_version,
                "state_signature": self.state_signature()}


# --- audit / version / lineage / registry projections ------------------------
@dataclass(frozen=True)
class IntelAuditRecord:
    """An immutable audit event; field-compatible with ``CaseAuditRecord``."""

    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload,
                "prev_hash": self.prev_hash, "event_hash": self.event_hash,
                "created_at": self.created_at}


@dataclass(frozen=True)
class IntelVersion:
    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous, "reason": self.reason,
                "created_at": self.created_at}


@dataclass(frozen=True)
class IntelLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass
class IntelRegistryRecord:
    """The registry entry shape for any intelligence artifact."""

    artifact_id: str
    artifact_kind: str          # cohort|analytics|trend|quality|intel_report
    scope: str
    version: str
    lineage_id: str
    audit_state: str
    content_signature_value: str
    intel_registry_version: str = INTEL_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"artifact_id": self.artifact_id, "artifact_kind": self.artifact_kind,
                         "version": self.version, "lineage_id": self.lineage_id,
                         "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"artifact_id": self.artifact_id, "artifact_kind": self.artifact_kind,
                "scope": self.scope, "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state,
                "content_signature_value": self.content_signature_value,
                "intel_registry_version": self.intel_registry_version,
                "content_signature": self.content_signature()}



# --- artifact id / kind resolution (type-based, not attribute-order) ---------
_ARTIFACT_ID_ATTR = {
    Cohort: ("cohort_id", "cohort"),
    PopulationAnalytics: ("analytics_id", "analytics"),
    Trend: ("trend_id", "trend"),
    QualityReport: ("quality_id", "quality"),
    IntelligenceReport: ("report_id", "intel_report"),
}


def artifact_id_of(artifact) -> str:
    """Return the logical id of an intelligence artifact (type-based)."""
    spec = _ARTIFACT_ID_ATTR.get(type(artifact))
    if spec is None:
        raise ValueError(f"unrecognised intelligence artifact type {type(artifact)!r}")
    return getattr(artifact, spec[0])


def artifact_kind_of(artifact) -> str:
    """Return the identity kind of an intelligence artifact (type-based)."""
    spec = _ARTIFACT_ID_ATTR.get(type(artifact))
    if spec is None:
        raise ValueError(f"unrecognised intelligence artifact type {type(artifact)!r}")
    return spec[1]
