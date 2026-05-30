"""Clinical review domain entities (V2-P2).

Pure data + ``to_dict`` + ``signature``. The review state machine lives in
``workflow/``, sessions in ``sessions/``, assignments in ``assignment/``, tracking
in ``tracking/``, the immutable log in ``audit/``, and orchestration in
``service.py``. This module owns only the entity *shapes*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    REVIEW_DOMAIN_VERSION, REVIEW_SESSION_VERSION, REVIEW_ASSIGNMENT_VERSION,
    REVIEW_REGISTRY_VERSION, DETERMINISTIC_EPOCH,
)


class ReviewStatus(str, Enum):
    """The canonical review lifecycle states (the machine lives in workflow/)."""

    CREATED = "created"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING_CONFIRMATION = "pending_confirmation"
    COMPLETED = "completed"
    REOPENED = "reopened"
    CLOSED = "closed"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class ReviewIdentity:
    """A review identity, derived from a case identity."""

    review_id: str
    case_id: str
    identity_version: str
    domain_version: str = REVIEW_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {"review_id": self.review_id, "case_id": self.case_id,
                "identity_version": self.identity_version, "domain_version": self.domain_version}


@dataclass(frozen=True)
class ReviewSession:
    """A single review sitting: who reviewed what, what they viewed, the outcome.

    ``session_end is None`` while the session is open. ``session_version`` is a
    content hash of the session's recorded state.
    """

    session_id: str
    review_id: str
    reviewer: str
    case_id: str
    study_id: Optional[str]
    session_start: str
    session_end: Optional[str] = None
    artifacts_viewed: tuple[str, ...] = ()
    reports_viewed: tuple[str, ...] = ()
    actions_taken: tuple[str, ...] = ()
    review_outcome: Optional[str] = None
    review_notes: str = ""
    session_version: str = REVIEW_SESSION_VERSION

    @property
    def is_open(self) -> bool:
        return self.session_end is None

    def signature(self) -> str:
        return hash_obj({
            "session_id": self.session_id, "review_id": self.review_id, "reviewer": self.reviewer,
            "study_id": self.study_id, "artifacts_viewed": list(self.artifacts_viewed),
            "reports_viewed": list(self.reports_viewed), "actions_taken": list(self.actions_taken),
            "review_outcome": self.review_outcome, "session_end": self.session_end,
        })

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id, "review_id": self.review_id, "reviewer": self.reviewer,
            "case_id": self.case_id, "study_id": self.study_id,
            "session_start": self.session_start, "session_end": self.session_end,
            "is_open": self.is_open,
            "artifacts_viewed": list(self.artifacts_viewed),
            "reports_viewed": list(self.reports_viewed),
            "actions_taken": list(self.actions_taken),
            "review_outcome": self.review_outcome, "review_notes": self.review_notes,
            "session_version": self.session_version, "signature": self.signature(),
        }


@dataclass(frozen=True)
class ReviewAssignment:
    """An assignment of a review to an assignee."""

    assignment_id: str
    review_id: str
    case_id: str
    assignee: str
    assignment_date: str
    priority: str
    status: str            # "active" | "reassigned" | "completed"
    reason: str = ""
    escalation_level: int = 0   # future escalation hook (inert in V2)
    assignment_version: str = REVIEW_ASSIGNMENT_VERSION

    def to_dict(self) -> dict:
        return {
            "assignment_id": self.assignment_id, "review_id": self.review_id, "case_id": self.case_id,
            "assignee": self.assignee, "assignment_date": self.assignment_date,
            "priority": self.priority, "status": self.status, "reason": self.reason,
            "escalation_level": self.escalation_level, "assignment_version": self.assignment_version,
        }


@dataclass(frozen=True)
class ReviewHistory:
    """An ordered, append-only projection of review status changes."""

    entries: tuple = ()

    def appended(self, entry: dict) -> "ReviewHistory":
        return ReviewHistory(entries=self.entries + (entry,))

    def to_dict(self) -> dict:
        return {"n_entries": len(self.entries), "entries": list(self.entries)}


@dataclass(frozen=True)
class ReviewAuditRecord:
    """An immutable audit event in the hash-chained review audit log.

    Field-compatible with ``CaseAuditRecord`` so both share ``ImmutableAuditLog``.
    """

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
class ReviewLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass(frozen=True)
class ReviewVersion:
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


@dataclass
class ReviewRegistryRecord:
    review_id: str
    case_id: str
    reviewer: Optional[str]
    version: str
    status: ReviewStatus
    assignment_ids: tuple[str, ...]
    artifact_refs: tuple[str, ...]
    audit_state: str
    lineage_id: str
    review_registry_version: str = REVIEW_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({
            "review_id": self.review_id, "case_id": self.case_id, "version": self.version,
            "reviewer": self.reviewer, "assignment_ids": list(self.assignment_ids),
            "lineage_id": self.lineage_id,
        })

    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id, "case_id": self.case_id, "reviewer": self.reviewer,
            "version": self.version, "status": self.status.value,
            "assignment_ids": list(self.assignment_ids), "artifact_refs": list(self.artifact_refs),
            "audit_state": self.audit_state, "lineage_id": self.lineage_id,
            "review_registry_version": self.review_registry_version,
            "content_signature": self.content_signature(),
        }


@dataclass
class Review:
    """The Review aggregate — structured human review linked to a Case + V1 inference."""

    identity: ReviewIdentity
    case_id: str
    study_id: Optional[str]
    status: ReviewStatus
    version: ReviewVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    reviewer: Optional[str] = None
    assignments: tuple[ReviewAssignment, ...] = ()
    sessions: tuple[ReviewSession, ...] = ()
    history: ReviewHistory = field(default_factory=ReviewHistory)
    artifact_refs: tuple[str, ...] = ()
    transition_count: int = 0
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    case_lineage_id: Optional[str] = None
    inference_lineage_id: Optional[str] = None
    domain_version: str = REVIEW_DOMAIN_VERSION

    @property
    def review_id(self) -> str:
        return self.identity.review_id

    @property
    def assignment_ids(self) -> tuple[str, ...]:
        return tuple(a.assignment_id for a in self.assignments)

    @property
    def session_ids(self) -> tuple[str, ...]:
        return tuple(s.session_id for s in self.sessions)

    def state_signature(self) -> str:
        return hash_obj({
            "review_id": self.review_id, "case_id": self.case_id, "study_id": self.study_id,
            "status": self.status.value, "reviewer": self.reviewer,
            "assignments": [a.to_dict() for a in self.assignments],
            "sessions": [s.signature() for s in self.sessions],
            "artifact_refs": list(self.artifact_refs),
        })

    def to_dict(self) -> dict:
        return {
            "domain_version": self.domain_version,
            "identity": self.identity.to_dict(),
            "case_id": self.case_id, "study_id": self.study_id,
            "status": self.status.value, "version": self.version.to_dict(),
            "owner": self.owner, "created_at": self.created_at, "reviewer": self.reviewer,
            "assignments": [a.to_dict() for a in self.assignments],
            "sessions": [s.to_dict() for s in self.sessions],
            "history": self.history.to_dict(),
            "artifact_refs": list(self.artifact_refs),
            "transition_count": self.transition_count,
            "lineage_id": self.lineage_id, "audit_head": self.audit_head,
            "case_lineage_id": self.case_lineage_id,
            "inference_lineage_id": self.inference_lineage_id,
            "state_signature": self.state_signature(),
        }
