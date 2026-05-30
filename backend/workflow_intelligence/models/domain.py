"""Workflow intelligence domain entities (V3-P3).

Pure data + ``to_dict`` + ``state_signature``. These describe *how work flows*:
transitions (state changes derived from events/timelines), dependencies (between
operational entities), and metrics (bottlenecks + efficiency). A workflow is a
first-class entity, derived strictly **from events and temporal intelligence** —
no hidden workflow state.

Mandated entities: ``WorkflowIdentity`` (in ``identity``), ``WorkflowRecord``,
``WorkflowMetadata``, ``WorkflowTransition``, ``WorkflowDependency``,
``WorkflowMetric``, ``WorkflowVersion``, ``WorkflowAuditRecord``,
``WorkflowLineageRecord``, ``WorkflowRegistryRecord``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    WORKFLOW_DOMAIN_VERSION, WORKFLOW_TRANSITION_VERSION, WORKFLOW_DEPENDENCY_VERSION,
    WORKFLOW_METRIC_VERSION, WORKFLOW_REGISTRY_VERSION, DETERMINISTIC_EPOCH,
)


# --- transition ---------------------------------------------------------------
@dataclass(frozen=True)
class WorkflowTransition:
    """One observed state transition, derived from a lifecycle event."""

    order: int
    from_state: Optional[str]
    to_state: str
    event_id: str
    event_type: str
    transition_version: str = WORKFLOW_TRANSITION_VERSION

    def to_dict(self) -> dict:
        return {"order": self.order, "from_state": self.from_state, "to_state": self.to_state,
                "event_id": self.event_id, "event_type": self.event_type,
                "transition_version": self.transition_version}


# --- dependency ---------------------------------------------------------------
@dataclass(frozen=True)
class WorkflowDependency:
    """A directed dependency between two operational entities.

    ``relation`` is one of upstream | downstream | blocked | waiting | completed.
    """

    dependency_id: str
    from_entity: str
    from_kind: str
    to_entity: str
    to_kind: str
    relation: str
    dependency_version: str = WORKFLOW_DEPENDENCY_VERSION

    def to_dict(self) -> dict:
        return {"dependency_id": self.dependency_id, "from_entity": self.from_entity,
                "from_kind": self.from_kind, "to_entity": self.to_entity, "to_kind": self.to_kind,
                "relation": self.relation, "dependency_version": self.dependency_version}


# --- metric -------------------------------------------------------------------
@dataclass(frozen=True)
class WorkflowMetric:
    """A single explainable workflow metric (efficiency or bottleneck).

    ``value`` is a deterministic number; ``unit`` documents its meaning
    (ratio | logical_steps | count). ``observed`` flags whether inputs existed.
    """

    name: str
    value: float
    unit: str
    observed: bool
    detail: str = ""
    metric_version: str = WORKFLOW_METRIC_VERSION

    def to_dict(self) -> dict:
        return {"name": self.name, "value": self.value, "unit": self.unit,
                "observed": self.observed, "detail": self.detail,
                "metric_version": self.metric_version}


# --- metadata -----------------------------------------------------------------
@dataclass(frozen=True)
class WorkflowMetadata:
    """Descriptive metadata: what the workflow was derived from."""

    source_event_ids: tuple[str, ...] = ()
    source_timeline_id: Optional[str] = None
    n_events: int = 0
    bottlenecks: tuple[str, ...] = ()       # names of detected bottleneck conditions

    def to_dict(self) -> dict:
        return {"source_event_ids": list(self.source_event_ids),
                "source_timeline_id": self.source_timeline_id, "n_events": self.n_events,
                "bottlenecks": list(self.bottlenecks)}


# --- workflow record (first-class entity) ------------------------------------
@dataclass(frozen=True)
class WorkflowRecord:
    """A first-class workflow: the flow of work for a subject entity."""

    workflow_id: str
    workflow_type: str          # case_workflow | review_workflow | finding_workflow | operational_workflow
    subject_kind: str
    subject_id: str
    state: str                  # the latest observed state (or "empty")
    transitions: tuple[WorkflowTransition, ...] = ()
    dependencies: tuple[WorkflowDependency, ...] = ()
    metrics: tuple[WorkflowMetric, ...] = ()
    metadata: WorkflowMetadata = field(default_factory=WorkflowMetadata)
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = WORKFLOW_DOMAIN_VERSION

    @property
    def n_transitions(self) -> int:
        return len(self.transitions)

    def metric(self, name: str) -> Optional[WorkflowMetric]:
        for m in self.metrics:
            if m.name == name:
                return m
        return None

    def state_signature(self) -> str:
        return hash_obj({
            "workflow_id": self.workflow_id, "workflow_type": self.workflow_type,
            "subject_kind": self.subject_kind, "subject_id": self.subject_id, "state": self.state,
            "transitions": [t.to_dict() for t in self.transitions],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "metrics": [m.to_dict() for m in self.metrics],
            "metadata": self.metadata.to_dict(),
        })

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id, "workflow_type": self.workflow_type,
            "subject_kind": self.subject_kind, "subject_id": self.subject_id, "state": self.state,
            "transitions": [t.to_dict() for t in self.transitions],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "metrics": [m.to_dict() for m in self.metrics], "metadata": self.metadata.to_dict(),
            "n_transitions": self.n_transitions, "version": self.version,
            "lineage_id": self.lineage_id, "audit_state": self.audit_state,
            "domain_version": self.domain_version, "state_signature": self.state_signature(),
        }


# --- audit / version / lineage / registry projections ------------------------
@dataclass(frozen=True)
class WorkflowAuditRecord:
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
class WorkflowVersion:
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
class WorkflowLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass
class WorkflowRegistryRecord:
    workflow_id: str
    workflow_type: str
    subject_id: str
    state: str
    version: str
    lineage_id: str
    audit_state: str
    content_signature_value: str
    workflow_registry_version: str = WORKFLOW_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"workflow_id": self.workflow_id, "workflow_type": self.workflow_type,
                         "version": self.version, "lineage_id": self.lineage_id,
                         "state": self.state, "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"workflow_id": self.workflow_id, "workflow_type": self.workflow_type,
                "subject_id": self.subject_id, "state": self.state, "version": self.version,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "content_signature_value": self.content_signature_value,
                "workflow_registry_version": self.workflow_registry_version,
                "content_signature": self.content_signature()}
