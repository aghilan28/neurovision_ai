"""Clinical case domain entities (V2-P1).

These dataclasses are the canonical, versioned shapes of every clinical-case
record. They are pure data + ``to_dict`` (JSON-able, canonical) + ``signature``
(content hash) — no I/O, no orchestration. Identities are minted by the identity
system; lifecycle transitions are governed by the lifecycle state machine; audit
events are appended to the immutable audit log; lineage nodes are recorded via the
shared lineage tracker. This module owns only the *shapes*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import CASE_DOMAIN_VERSION, DETERMINISTIC_EPOCH


class CaseStatus(str, Enum):
    """The canonical case lifecycle states (the transition machine lives in lifecycle/)."""

    CREATED = "created"
    INGESTED = "ingested"
    PROCESSING = "processing"
    READY_FOR_REVIEW = "ready_for_review"
    UNDER_REVIEW = "under_review"
    REVIEWED = "reviewed"
    CLOSED = "closed"
    ARCHIVED = "archived"


# --- identity projections ------------------------------------------------------
@dataclass(frozen=True)
class PatientIdentity:
    """A patient as a first-class, deidentified, content-addressed identity."""

    patient_id: str
    identity_version: str
    domain_version: str = CASE_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {"patient_id": self.patient_id, "identity_version": self.identity_version,
                "domain_version": self.domain_version}


@dataclass(frozen=True)
class CaseIdentity:
    """A case identity, derived from a patient identity."""

    case_id: str
    patient_id: str
    identity_version: str
    domain_version: str = CASE_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "patient_id": self.patient_id,
                "identity_version": self.identity_version, "domain_version": self.domain_version}


@dataclass(frozen=True)
class StudyIdentity:
    """A study (EEG recording session) identity, derived from a case identity.

    A study links the clinical object graph to V1: ``inference_id`` /
    ``inference_lineage_id`` reference the registered V1 inference that produced the
    intelligence artifacts for this study.
    """

    study_id: str
    case_id: str
    identity_version: str
    inference_id: Optional[str] = None
    inference_lineage_id: Optional[str] = None
    dataset_version: Optional[str] = None
    artifact_refs: dict = field(default_factory=dict)
    domain_version: str = CASE_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {
            "study_id": self.study_id, "case_id": self.case_id,
            "identity_version": self.identity_version,
            "inference_id": self.inference_id,
            "inference_lineage_id": self.inference_lineage_id,
            "dataset_version": self.dataset_version,
            "artifact_refs": self.artifact_refs,
            "domain_version": self.domain_version,
        }


# --- metadata / state ----------------------------------------------------------
@dataclass(frozen=True)
class CaseMetadata:
    """Deidentified case metadata. Never contains raw PHI or filenames."""

    title: str = ""
    modality: str = "EEG"
    priority: str = "routine"
    tags: tuple[str, ...] = ()
    notes: str = ""
    deidentified: bool = True

    def to_dict(self) -> dict:
        return {"title": self.title, "modality": self.modality, "priority": self.priority,
                "tags": list(self.tags), "notes": self.notes, "deidentified": self.deidentified}


@dataclass(frozen=True)
class CaseState:
    """The current lifecycle state of a case + when it was entered."""

    status: CaseStatus
    entered_at: str = DETERMINISTIC_EPOCH
    transition_count: int = 0

    def to_dict(self) -> dict:
        return {"status": self.status.value, "entered_at": self.entered_at,
                "transition_count": self.transition_count}


# --- audit / lineage / version projections -------------------------------------
@dataclass(frozen=True)
class CaseAuditRecord:
    """An immutable audit event in the hash-chained case audit log."""

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
class CaseLineageRecord:
    """A projection of a lineage node attached to a case (id + kind + parents)."""

    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass(frozen=True)
class CaseVersion:
    """A content-addressed case version (bumped on every governed mutation).

    The version *chains* the current state signature with the previous version, so a
    case returning to a logically-identical state still receives a unique version
    (versions form a per-case hash chain, like the audit log).
    """

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


# --- registry record -----------------------------------------------------------
@dataclass
class CaseRegistryRecord:
    """The registry entry shape (mutated only via governed registry methods)."""

    case_id: str
    patient_id: str
    study_ids: tuple[str, ...]
    status: CaseStatus
    version: str
    owner: str
    creation_date: str
    review_state: str
    audit_state: str            # the audit-log head hash (tamper-evident)
    dependencies: tuple[str, ...]
    lineage_id: str
    case_registry_version: str

    def content_signature(self) -> str:
        return hash_obj({
            "case_id": self.case_id, "patient_id": self.patient_id,
            "study_ids": list(self.study_ids), "version": self.version,
            "owner": self.owner, "lineage_id": self.lineage_id,
        })

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id, "patient_id": self.patient_id,
            "study_ids": list(self.study_ids), "status": self.status.value,
            "version": self.version, "owner": self.owner, "creation_date": self.creation_date,
            "review_state": self.review_state, "audit_state": self.audit_state,
            "dependencies": list(self.dependencies), "lineage_id": self.lineage_id,
            "case_registry_version": self.case_registry_version,
            "content_signature": self.content_signature(),
        }


# --- the aggregate -------------------------------------------------------------
@dataclass
class Case:
    """The Case aggregate — the platform's primary organizational object.

    Permanent, versioned, auditable, lineage-tracked, recoverable, reviewable. It
    references its patient, its studies (each linked to a V1 inference), its current
    lifecycle state, its version, owner, lineage node, and audit-log head.
    """

    identity: CaseIdentity
    patient: PatientIdentity
    metadata: CaseMetadata
    state: CaseState
    version: CaseVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    studies: tuple[StudyIdentity, ...] = ()
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    dependencies: tuple[str, ...] = ()
    domain_version: str = CASE_DOMAIN_VERSION

    @property
    def case_id(self) -> str:
        return self.identity.case_id

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id

    @property
    def study_ids(self) -> tuple[str, ...]:
        return tuple(s.study_id for s in self.studies)

    def state_signature(self) -> str:
        """Content hash of the mutable case state (basis of CaseVersion)."""
        return hash_obj({
            "case_id": self.case_id,
            "patient_id": self.patient_id,
            "studies": [s.to_dict() for s in self.studies],
            "metadata": self.metadata.to_dict(),
            "status": self.state.status.value,
            "dependencies": list(self.dependencies),
        })

    def to_dict(self) -> dict:
        return {
            "domain_version": self.domain_version,
            "identity": self.identity.to_dict(),
            "patient": self.patient.to_dict(),
            "metadata": self.metadata.to_dict(),
            "state": self.state.to_dict(),
            "version": self.version.to_dict(),
            "owner": self.owner,
            "created_at": self.created_at,
            "studies": [s.to_dict() for s in self.studies],
            "lineage_id": self.lineage_id,
            "audit_head": self.audit_head,
            "dependencies": list(self.dependencies),
            "state_signature": self.state_signature(),
        }
