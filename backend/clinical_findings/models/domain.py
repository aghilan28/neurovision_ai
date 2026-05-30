"""Clinical finding domain entities (V2-P3).

Pure data + ``to_dict`` + ``signature``. The lifecycle machine lives in
``lifecycle/``, evidence in ``evidence/``, interpretation in ``interpretation/``,
the immutable log in ``audit/``, and orchestration in ``service.py``. This module
owns only the entity *shapes*.

Design guardrails (the directive's hard limits):
  * A ``Finding`` is a structured **observation linked to evidence** — it carries
    no diagnosis, recommendation, probability, or prediction field.
  * ``FindingInterpretation`` is a **separate** entity; the finding references
    interpretation ids but never embeds interpretation content.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    FINDING_DOMAIN_VERSION, FINDING_EVIDENCE_VERSION, FINDING_INTERPRETATION_VERSION,
    FINDING_REGISTRY_VERSION, DETERMINISTIC_EPOCH,
)


class FindingStatus(str, Enum):
    """The canonical finding lifecycle states (the machine lives in lifecycle/)."""

    CREATED = "created"
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    CONFIRMED = "confirmed"
    REVISED = "revised"
    SUPERSEDED = "superseded"
    CLOSED = "closed"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class FindingIdentity:
    """A finding identity, derived from a review identity."""

    finding_id: str
    review_id: str
    case_id: str
    study_id: Optional[str]
    identity_version: str
    domain_version: str = FINDING_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {"finding_id": self.finding_id, "review_id": self.review_id, "case_id": self.case_id,
                "study_id": self.study_id, "identity_version": self.identity_version,
                "domain_version": self.domain_version}


@dataclass(frozen=True)
class FindingRecord:
    """The structured observation. Descriptive only — no diagnosis/recommendation.

    ``category`` is a controlled descriptive label (e.g. an EEG pattern term such as
    "rhythmic_delta"), ideally mapped to a knowledge concept (V2-P4). ``region`` is
    an optional spatial descriptor. It contains no inference of disease or action.
    """

    observation: str
    category: str = "unspecified"
    region: Optional[str] = None
    notes: str = ""
    domain_version: str = FINDING_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {"observation": self.observation, "category": self.category, "region": self.region,
                "notes": self.notes, "domain_version": self.domain_version}


@dataclass(frozen=True)
class FindingMetadata:
    author: str = ""
    priority: str = "routine"
    tags: tuple[str, ...] = ()
    modality: str = "EEG"
    deidentified: bool = True

    def to_dict(self) -> dict:
        return {"author": self.author, "priority": self.priority, "tags": list(self.tags),
                "modality": self.modality, "deidentified": self.deidentified}


@dataclass(frozen=True)
class FindingEvidence:
    """A single evidence link. A finding must never exist without >= 1 of these.

    ``evidence_source`` references a registered V1/V2 artifact (e.g. an inference
    id, an artifact name + checksum, a report name, or a review action).
    ``evidence_confidence`` is a *recorded* value (e.g. a calibrated confidence or
    coverage figure) — never computed/assumed by the findings layer.
    """

    evidence_id: str
    finding_id: str
    evidence_type: str        # inference|calibration|conformal|coverage|risk|artifact|report|review_action
    evidence_source: str      # id / artifact name / report name
    evidence_version: str     # contract version / checksum
    evidence_confidence: Optional[float] = None
    lineage_id: Optional[str] = None
    notes: str = ""
    evidence_version_tag: str = FINDING_EVIDENCE_VERSION

    def signature(self) -> str:
        return hash_obj({"evidence_id": self.evidence_id, "finding_id": self.finding_id,
                         "evidence_type": self.evidence_type, "evidence_source": self.evidence_source,
                         "evidence_version": self.evidence_version})

    def to_dict(self) -> dict:
        return {"evidence_id": self.evidence_id, "finding_id": self.finding_id,
                "evidence_type": self.evidence_type, "evidence_source": self.evidence_source,
                "evidence_version": self.evidence_version, "evidence_confidence": self.evidence_confidence,
                "lineage_id": self.lineage_id, "notes": self.notes,
                "evidence_version_tag": self.evidence_version_tag, "signature": self.signature()}


@dataclass(frozen=True)
class FindingInterpretation:
    """A structured interpretation — a SEPARATE entity from the finding.

    Interpretations must remain separate from findings (the directive forbids
    merging). An interpretation references supporting evidence + review and carries
    a *recorded* qualitative confidence level (never a computed probability).
    """

    interpretation_id: str
    finding_id: str
    interpretation_text: str
    interpretation_type: str = "descriptive"     # descriptive|contextual|differential-note
    interpretation_status: str = "draft"          # draft|confirmed|withdrawn
    supporting_evidence: tuple[str, ...] = ()
    confidence_level: Optional[str] = None         # qualitative: low|moderate|high (recorded)
    review_references: tuple[str, ...] = ()
    concept_refs: tuple[str, ...] = ()             # knowledge concepts (V2-P4 links)
    lineage_id: Optional[str] = None
    version: str = FINDING_INTERPRETATION_VERSION

    def signature(self) -> str:
        return hash_obj({"interpretation_id": self.interpretation_id, "finding_id": self.finding_id,
                         "interpretation_text": self.interpretation_text,
                         "interpretation_type": self.interpretation_type,
                         "interpretation_status": self.interpretation_status,
                         "supporting_evidence": list(self.supporting_evidence),
                         "confidence_level": self.confidence_level})

    def to_dict(self) -> dict:
        return {"interpretation_id": self.interpretation_id, "finding_id": self.finding_id,
                "interpretation_text": self.interpretation_text,
                "interpretation_type": self.interpretation_type,
                "interpretation_status": self.interpretation_status,
                "supporting_evidence": list(self.supporting_evidence),
                "confidence_level": self.confidence_level,
                "review_references": list(self.review_references),
                "concept_refs": list(self.concept_refs),
                "lineage_id": self.lineage_id, "version": self.version, "signature": self.signature()}


@dataclass(frozen=True)
class FindingVersion:
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
class FindingAuditRecord:
    """An immutable audit event in the hash-chained finding audit log.

    Field-compatible with ``CaseAuditRecord`` so it reuses ``ImmutableAuditLog``.
    """

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
class FindingLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass
class FindingRegistryRecord:
    finding_id: str
    case_id: str
    study_id: Optional[str]
    review_id: str
    status: FindingStatus
    version: str
    owner: str
    evidence_ids: tuple[str, ...]
    interpretation_ids: tuple[str, ...]
    lineage_id: str
    audit_state: str
    finding_registry_version: str = FINDING_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"finding_id": self.finding_id, "case_id": self.case_id,
                         "review_id": self.review_id, "version": self.version,
                         "evidence_ids": list(self.evidence_ids),
                         "interpretation_ids": list(self.interpretation_ids),
                         "lineage_id": self.lineage_id})

    def to_dict(self) -> dict:
        return {"finding_id": self.finding_id, "case_id": self.case_id, "study_id": self.study_id,
                "review_id": self.review_id, "status": self.status.value, "version": self.version,
                "owner": self.owner, "evidence_ids": list(self.evidence_ids),
                "interpretation_ids": list(self.interpretation_ids), "lineage_id": self.lineage_id,
                "audit_state": self.audit_state,
                "finding_registry_version": self.finding_registry_version,
                "content_signature": self.content_signature()}


@dataclass
class Finding:
    """The Finding aggregate — a structured, evidence-linked clinical observation."""

    identity: FindingIdentity
    record: FindingRecord
    metadata: FindingMetadata
    status: FindingStatus
    version: FindingVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    evidence: tuple[FindingEvidence, ...] = ()
    interpretation_ids: tuple[str, ...] = ()
    transition_count: int = 0
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    review_lineage_id: Optional[str] = None
    inference_lineage_id: Optional[str] = None
    domain_version: str = FINDING_DOMAIN_VERSION

    @property
    def finding_id(self) -> str:
        return self.identity.finding_id

    @property
    def case_id(self) -> str:
        return self.identity.case_id

    @property
    def study_id(self) -> Optional[str]:
        return self.identity.study_id

    @property
    def review_id(self) -> str:
        return self.identity.review_id

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(e.evidence_id for e in self.evidence)

    def state_signature(self) -> str:
        return hash_obj({
            "finding_id": self.finding_id, "review_id": self.review_id, "case_id": self.case_id,
            "study_id": self.study_id, "record": self.record.to_dict(),
            "status": self.status.value, "evidence": [e.signature() for e in self.evidence],
            "interpretation_ids": list(self.interpretation_ids),
        })

    def to_dict(self) -> dict:
        return {
            "domain_version": self.domain_version,
            "identity": self.identity.to_dict(),
            "record": self.record.to_dict(),
            "metadata": self.metadata.to_dict(),
            "status": self.status.value,
            "version": self.version.to_dict(),
            "owner": self.owner, "created_at": self.created_at,
            "evidence": [e.to_dict() for e in self.evidence],
            "interpretation_ids": list(self.interpretation_ids),
            "transition_count": self.transition_count,
            "lineage_id": self.lineage_id, "audit_head": self.audit_head,
            "review_lineage_id": self.review_lineage_id,
            "inference_lineage_id": self.inference_lineage_id,
            "state_signature": self.state_signature(),
        }
