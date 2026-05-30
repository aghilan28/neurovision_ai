"""Temporal intelligence domain entities (V3-P2).

Pure data + ``to_dict`` + ``state_signature``. These describe *time* over the
platform: timelines (ordered event sequences), histories (reconstructed change
logs), evolution records (state transitions), and temporal analytics (durations
and timing metrics). They are derived strictly **from events** and ordered by the
events' deterministic logical clock — no hidden state reconstruction.

Every artifact is versioned, lineage-tracked, and audited (orchestration lives in
``service.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    TEMPORAL_TIMELINE_VERSION, TEMPORAL_HISTORY_VERSION,
    TEMPORAL_EVOLUTION_VERSION, TEMPORAL_ANALYTICS_VERSION, TEMPORAL_REGISTRY_VERSION,
    TEMPORAL_VIZ_VERSION, DETERMINISTIC_EPOCH,
)


# --- timeline -----------------------------------------------------------------
@dataclass(frozen=True)
class TimelinePoint:
    """One ordered point on a timeline — a reference to a source event."""

    order: int                 # deterministic position (0-based)
    event_id: str
    event_type: str
    category: str
    clock: dict                # the event's logical clock (deterministic)

    def to_dict(self) -> dict:
        return {"order": self.order, "event_id": self.event_id, "event_type": self.event_type,
                "category": self.category, "clock": self.clock}


@dataclass(frozen=True)
class Timeline:
    timeline_id: str
    scope: str                 # e.g. "case:case+abc" / "patient:patient+xyz"
    subject_kind: str
    subject_id: str
    points: tuple[TimelinePoint, ...] = ()
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = TEMPORAL_TIMELINE_VERSION

    @property
    def length(self) -> int:
        return len(self.points)

    def state_signature(self) -> str:
        return hash_obj({"timeline_id": self.timeline_id, "scope": self.scope,
                         "subject_kind": self.subject_kind, "subject_id": self.subject_id,
                         "points": [p.to_dict() for p in self.points]})

    def to_dict(self) -> dict:
        return {"timeline_id": self.timeline_id, "scope": self.scope,
                "subject_kind": self.subject_kind, "subject_id": self.subject_id,
                "points": [p.to_dict() for p in self.points], "length": self.length,
                "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state, "domain_version": self.domain_version,
                "state_signature": self.state_signature()}


# --- history ------------------------------------------------------------------
@dataclass(frozen=True)
class HistoryEntry:
    order: int
    event_id: str
    event_type: str
    summary: str
    source_version: str

    def to_dict(self) -> dict:
        return {"order": self.order, "event_id": self.event_id, "event_type": self.event_type,
                "summary": self.summary, "source_version": self.source_version}


@dataclass(frozen=True)
class History:
    history_id: str
    scope: str
    subject_kind: str
    subject_id: str
    entries: tuple[HistoryEntry, ...] = ()
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = TEMPORAL_HISTORY_VERSION

    @property
    def length(self) -> int:
        return len(self.entries)

    def state_signature(self) -> str:
        return hash_obj({"history_id": self.history_id, "scope": self.scope,
                         "subject_kind": self.subject_kind, "subject_id": self.subject_id,
                         "entries": [e.to_dict() for e in self.entries]})

    def to_dict(self) -> dict:
        return {"history_id": self.history_id, "scope": self.scope,
                "subject_kind": self.subject_kind, "subject_id": self.subject_id,
                "entries": [e.to_dict() for e in self.entries], "length": self.length,
                "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state, "domain_version": self.domain_version,
                "state_signature": self.state_signature()}


# --- evolution ----------------------------------------------------------------
@dataclass(frozen=True)
class EvolutionStep:
    order: int
    from_state: Optional[str]
    to_state: str
    event_id: str
    event_type: str

    def to_dict(self) -> dict:
        return {"order": self.order, "from_state": self.from_state, "to_state": self.to_state,
                "event_id": self.event_id, "event_type": self.event_type}


@dataclass(frozen=True)
class EvolutionRecord:
    evolution_id: str
    scope: str
    subject_kind: str
    subject_id: str
    steps: tuple[EvolutionStep, ...] = ()
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = TEMPORAL_EVOLUTION_VERSION

    @property
    def n_transitions(self) -> int:
        return len(self.steps)

    def state_signature(self) -> str:
        return hash_obj({"evolution_id": self.evolution_id, "scope": self.scope,
                         "subject_kind": self.subject_kind, "subject_id": self.subject_id,
                         "steps": [s.to_dict() for s in self.steps]})

    def to_dict(self) -> dict:
        return {"evolution_id": self.evolution_id, "scope": self.scope,
                "subject_kind": self.subject_kind, "subject_id": self.subject_id,
                "steps": [s.to_dict() for s in self.steps], "n_transitions": self.n_transitions,
                "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state, "domain_version": self.domain_version,
                "state_signature": self.state_signature()}


# --- temporal analytics -------------------------------------------------------
@dataclass(frozen=True)
class DurationMetric:
    """A duration measured in deterministic logical steps (event-count spans).

    Because the platform forbids wall-clock, "duration" is the number of ordered
    operational steps between two events (a reproducible logical interval), not a
    physical time delta.
    """

    name: str
    from_event_type: str
    to_event_type: str
    steps: int                 # logical steps (>=0) or -1 if not observed
    observed: bool
    detail: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "from_event_type": self.from_event_type,
                "to_event_type": self.to_event_type, "steps": self.steps,
                "observed": self.observed, "detail": self.detail}


@dataclass(frozen=True)
class TemporalAnalytics:
    analytics_id: str
    scope: str
    metrics: tuple[DurationMetric, ...] = ()
    counts: dict = field(default_factory=dict)       # event-type counts
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = TEMPORAL_ANALYTICS_VERSION

    def metric(self, name: str) -> Optional[DurationMetric]:
        for m in self.metrics:
            if m.name == name:
                return m
        return None

    def state_signature(self) -> str:
        return hash_obj({"analytics_id": self.analytics_id, "scope": self.scope,
                         "metrics": [m.to_dict() for m in self.metrics], "counts": self.counts})

    def to_dict(self) -> dict:
        return {"analytics_id": self.analytics_id, "scope": self.scope,
                "metrics": [m.to_dict() for m in self.metrics], "counts": self.counts,
                "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state, "domain_version": self.domain_version,
                "state_signature": self.state_signature()}


# --- visualization contracts (no UI; contracts only) -------------------------
@dataclass(frozen=True)
class VisualizationContract:
    """A visualization-ready, JSON-able contract (no rendering here).

    ``contract_type`` is one of: timeline | event_sequence | evolution_graph |
    duration_graph | trend_graph | operational_dashboard.
    """

    contract_type: str
    title: str
    spec: dict
    viz_version: str = TEMPORAL_VIZ_VERSION

    def to_dict(self) -> dict:
        return {"contract_type": self.contract_type, "title": self.title, "spec": self.spec,
                "viz_version": self.viz_version}


# --- audit / version / lineage / registry projections ------------------------
@dataclass(frozen=True)
class TemporalAuditRecord:
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
class TemporalVersion:
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
class TemporalRegistryRecord:
    artifact_id: str
    artifact_kind: str          # timeline|history|evolution|temporal_analytics|temporal_report
    scope: str
    version: str
    lineage_id: str
    audit_state: str
    content_signature_value: str
    temporal_registry_version: str = TEMPORAL_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"artifact_id": self.artifact_id, "artifact_kind": self.artifact_kind,
                         "version": self.version, "lineage_id": self.lineage_id,
                         "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"artifact_id": self.artifact_id, "artifact_kind": self.artifact_kind,
                "scope": self.scope, "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state,
                "content_signature_value": self.content_signature_value,
                "temporal_registry_version": self.temporal_registry_version,
                "content_signature": self.content_signature()}


# --- type-based id/kind resolution -------------------------------------------
_ARTIFACT_SPEC = {
    Timeline: ("timeline_id", "timeline"),
    History: ("history_id", "history"),
    EvolutionRecord: ("evolution_id", "evolution"),
    TemporalAnalytics: ("analytics_id", "temporal_analytics"),
}


def artifact_id_of(artifact) -> str:
    spec = _ARTIFACT_SPEC.get(type(artifact))
    if spec is None:
        raise ValueError(f"unrecognised temporal artifact type {type(artifact)!r}")
    return getattr(artifact, spec[0])


def artifact_kind_of(artifact) -> str:
    spec = _ARTIFACT_SPEC.get(type(artifact))
    if spec is None:
        raise ValueError(f"unrecognised temporal artifact type {type(artifact)!r}")
    return spec[1]
