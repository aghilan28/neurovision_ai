"""Decision-support domain entities (V2-P6).

Pure data + ``to_dict`` + ``state_signature``. These shapes describe *decision
support* — context aggregation, evidence bundling, risk context, prioritization,
and guidance. They are **explainable** (carry their factors/reason), reference
source ids only, and contain **no diagnosis, treatment, medication, or clinical
order** (forbidden — enforced by the scope guard). The clinician remains the
decision-maker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    DECISION_CONTEXT_VERSION, DECISION_EVIDENCE_VERSION, DECISION_RISK_VERSION,
    DECISION_PRIORITIZATION_VERSION, DECISION_GUIDANCE_VERSION, DECISION_DOMAIN_VERSION,
    DECISION_REGISTRY_VERSION, DETERMINISTIC_EPOCH,
)


class RiskBand(str, Enum):
    """Decision-support review-attention banding (NOT a clinical risk score)."""

    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"


class PriorityLevel(str, Enum):
    """Review-priority levels (ordering of reviewer attention, not clinical triage)."""

    ROUTINE = "routine"
    ELEVATED = "elevated"
    HIGH = "high"


class GuidanceCategory(str, Enum):
    """Permitted guidance categories. Diagnosis/treatment are intentionally absent."""

    REVIEW = "review"
    EVIDENCE = "evidence"
    KNOWLEDGE = "knowledge"
    INVESTIGATION = "investigation"
    RISK = "risk"


# --- decision context ---------------------------------------------------------
@dataclass(frozen=True)
class DecisionContext:
    context_id: str
    case_id: str
    patient_id: str
    review_ids: tuple[str, ...] = ()
    finding_ids: tuple[str, ...] = ()
    interpretation_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    concept_ids: tuple[str, ...] = ()
    completeness: dict = field(default_factory=dict)
    counts: dict = field(default_factory=dict)
    population_context: dict = field(default_factory=dict)
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = DECISION_CONTEXT_VERSION

    def state_signature(self) -> str:
        return hash_obj({"context_id": self.context_id, "case_id": self.case_id,
                         "patient_id": self.patient_id, "review_ids": list(self.review_ids),
                         "finding_ids": list(self.finding_ids),
                         "interpretation_ids": list(self.interpretation_ids),
                         "evidence_ids": list(self.evidence_ids), "concept_ids": list(self.concept_ids),
                         "completeness": self.completeness, "counts": self.counts,
                         "population_context": self.population_context})

    def to_dict(self) -> dict:
        return {"context_id": self.context_id, "case_id": self.case_id, "patient_id": self.patient_id,
                "review_ids": list(self.review_ids), "finding_ids": list(self.finding_ids),
                "interpretation_ids": list(self.interpretation_ids),
                "evidence_ids": list(self.evidence_ids), "concept_ids": list(self.concept_ids),
                "completeness": self.completeness, "counts": self.counts,
                "population_context": self.population_context, "version": self.version,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "domain_version": self.domain_version, "state_signature": self.state_signature()}


# --- evidence bundle ----------------------------------------------------------
@dataclass(frozen=True)
class EvidenceSummary:
    evidence_id: str
    finding_id: str
    evidence_type: str
    confidence: Optional[float]
    rank: int

    def to_dict(self) -> dict:
        return {"evidence_id": self.evidence_id, "finding_id": self.finding_id,
                "evidence_type": self.evidence_type, "confidence": self.confidence, "rank": self.rank}


@dataclass(frozen=True)
class EvidenceBundle:
    bundle_id: str
    context_id: str
    items: tuple[EvidenceSummary, ...] = ()
    ranking: tuple[str, ...] = ()
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = DECISION_EVIDENCE_VERSION

    @property
    def size(self) -> int:
        return len(self.items)

    def state_signature(self) -> str:
        return hash_obj({"bundle_id": self.bundle_id, "context_id": self.context_id,
                         "items": [i.to_dict() for i in self.items], "ranking": list(self.ranking)})

    def to_dict(self) -> dict:
        return {"bundle_id": self.bundle_id, "context_id": self.context_id,
                "items": [i.to_dict() for i in self.items], "ranking": list(self.ranking),
                "size": self.size, "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state, "domain_version": self.domain_version,
                "state_signature": self.state_signature()}


# --- risk context -------------------------------------------------------------
@dataclass(frozen=True)
class RiskComponent:
    name: str
    value: float
    basis: str

    def to_dict(self) -> dict:
        return {"name": self.name, "value": self.value, "basis": self.basis}


@dataclass(frozen=True)
class RiskContext:
    risk_id: str
    context_id: str
    components: tuple[RiskComponent, ...] = ()
    aggregate: float = 0.0
    band: RiskBand = RiskBand.LOW
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = DECISION_RISK_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.band, RiskBand):
            object.__setattr__(self, "band", RiskBand(self.band))

    def component(self, name: str) -> Optional[RiskComponent]:
        for c in self.components:
            if c.name == name:
                return c
        return None

    def state_signature(self) -> str:
        return hash_obj({"risk_id": self.risk_id, "context_id": self.context_id,
                         "components": [c.to_dict() for c in self.components],
                         "aggregate": self.aggregate, "band": self.band.value})

    def to_dict(self) -> dict:
        return {"risk_id": self.risk_id, "context_id": self.context_id,
                "components": [c.to_dict() for c in self.components], "aggregate": self.aggregate,
                "band": self.band.value, "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state, "domain_version": self.domain_version,
                "state_signature": self.state_signature()}


# --- prioritization -----------------------------------------------------------
@dataclass(frozen=True)
class PriorityFactor:
    name: str
    contribution: float
    detail: str

    def to_dict(self) -> dict:
        return {"name": self.name, "contribution": self.contribution, "detail": self.detail}


@dataclass(frozen=True)
class PrioritizationRecord:
    priority_id: str
    context_id: str
    level: PriorityLevel
    score: float
    reason: str
    factors: tuple[PriorityFactor, ...] = ()
    supporting_evidence: tuple[str, ...] = ()
    risk_id: Optional[str] = None
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = DECISION_PRIORITIZATION_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.level, PriorityLevel):
            object.__setattr__(self, "level", PriorityLevel(self.level))

    def state_signature(self) -> str:
        return hash_obj({"priority_id": self.priority_id, "context_id": self.context_id,
                         "level": self.level.value, "score": self.score, "reason": self.reason,
                         "factors": [f.to_dict() for f in self.factors],
                         "supporting_evidence": list(self.supporting_evidence), "risk_id": self.risk_id})

    def to_dict(self) -> dict:
        return {"priority_id": self.priority_id, "context_id": self.context_id, "level": self.level.value,
                "score": self.score, "reason": self.reason, "factors": [f.to_dict() for f in self.factors],
                "supporting_evidence": list(self.supporting_evidence), "risk_id": self.risk_id,
                "version": self.version, "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "domain_version": self.domain_version, "state_signature": self.state_signature()}


# --- guidance -----------------------------------------------------------------
@dataclass(frozen=True)
class GuidanceItem:
    category: GuidanceCategory
    message: str
    rationale: str
    references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.category, GuidanceCategory):
            object.__setattr__(self, "category", GuidanceCategory(self.category))

    def to_dict(self) -> dict:
        return {"category": self.category.value, "message": self.message,
                "rationale": self.rationale, "references": list(self.references)}


@dataclass(frozen=True)
class GuidanceRecord:
    guidance_id: str
    context_id: str
    items: tuple[GuidanceItem, ...] = ()
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = DECISION_GUIDANCE_VERSION

    def state_signature(self) -> str:
        return hash_obj({"guidance_id": self.guidance_id, "context_id": self.context_id,
                         "items": [i.to_dict() for i in self.items]})

    def to_dict(self) -> dict:
        return {"guidance_id": self.guidance_id, "context_id": self.context_id,
                "items": [i.to_dict() for i in self.items], "version": self.version,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "domain_version": self.domain_version, "state_signature": self.state_signature()}


# --- decision support record --------------------------------------------------
@dataclass(frozen=True)
class DecisionSupportRecord:
    record_id: str
    case_id: str
    patient_id: str
    context_id: str
    evidence_bundle_id: str
    risk_id: str
    prioritization_id: str
    guidance_id: str
    explanation: str = ""
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = DECISION_DOMAIN_VERSION

    def component_ids(self) -> tuple[str, ...]:
        return (self.context_id, self.evidence_bundle_id, self.risk_id,
                self.prioritization_id, self.guidance_id)

    def state_signature(self) -> str:
        return hash_obj({"record_id": self.record_id, "case_id": self.case_id,
                         "patient_id": self.patient_id, "context_id": self.context_id,
                         "evidence_bundle_id": self.evidence_bundle_id, "risk_id": self.risk_id,
                         "prioritization_id": self.prioritization_id, "guidance_id": self.guidance_id,
                         "explanation": self.explanation})

    def to_dict(self) -> dict:
        return {"record_id": self.record_id, "case_id": self.case_id, "patient_id": self.patient_id,
                "context_id": self.context_id, "evidence_bundle_id": self.evidence_bundle_id,
                "risk_id": self.risk_id, "prioritization_id": self.prioritization_id,
                "guidance_id": self.guidance_id, "explanation": self.explanation,
                "version": self.version, "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "domain_version": self.domain_version, "state_signature": self.state_signature()}


@dataclass(frozen=True)
class DecisionReport:
    report_id: str
    report_type: str
    scope: str
    sections: dict = field(default_factory=dict)
    references: tuple[str, ...] = ()
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = DECISION_DOMAIN_VERSION

    def state_signature(self) -> str:
        return hash_obj({"report_id": self.report_id, "report_type": self.report_type,
                         "scope": self.scope, "sections": self.sections,
                         "references": list(self.references)})

    def to_dict(self) -> dict:
        return {"report_id": self.report_id, "report_type": self.report_type, "scope": self.scope,
                "sections": self.sections, "references": list(self.references), "version": self.version,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "domain_version": self.domain_version, "state_signature": self.state_signature()}


# --- audit / version / lineage / registry projections ------------------------
@dataclass(frozen=True)
class DecisionAuditRecord:
    """An immutable audit event; field-compatible with ``CaseAuditRecord``."""

    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload,
                "prev_hash": self.prev_hash, "event_hash": self.event_hash, "created_at": self.created_at}


@dataclass(frozen=True)
class DecisionVersion:
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
class DecisionLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass
class DecisionRegistryRecord:
    artifact_id: str
    artifact_kind: str
    case_id: str
    version: str
    lineage_id: str
    audit_state: str
    content_signature_value: str
    decision_registry_version: str = DECISION_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"artifact_id": self.artifact_id, "artifact_kind": self.artifact_kind,
                         "version": self.version, "lineage_id": self.lineage_id,
                         "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"artifact_id": self.artifact_id, "artifact_kind": self.artifact_kind,
                "case_id": self.case_id, "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state, "content_signature_value": self.content_signature_value,
                "decision_registry_version": self.decision_registry_version,
                "content_signature": self.content_signature()}


# --- artifact id / kind resolution (type-based) ------------------------------
_ARTIFACT_SPEC = {
    DecisionContext: ("context_id", "decision_context"),
    EvidenceBundle: ("bundle_id", "evidence_bundle"),
    RiskContext: ("risk_id", "risk_context"),
    PrioritizationRecord: ("priority_id", "prioritization"),
    GuidanceRecord: ("guidance_id", "guidance"),
    DecisionSupportRecord: ("record_id", "decision_support"),
    DecisionReport: ("report_id", "decision_report"),
}


def artifact_id_of(artifact) -> str:
    spec = _ARTIFACT_SPEC.get(type(artifact))
    if spec is None:
        raise ValueError(f"unrecognised decision artifact type {type(artifact)!r}")
    return getattr(artifact, spec[0])


def artifact_kind_of(artifact) -> str:
    spec = _ARTIFACT_SPEC.get(type(artifact))
    if spec is None:
        raise ValueError(f"unrecognised decision artifact type {type(artifact)!r}")
    return spec[1]
