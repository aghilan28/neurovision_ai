"""Operational analytics domain entities (V3-P5).

Pure data + ``to_dict`` + (where relevant) ``state_signature``. These describe
**derived operational intelligence**: metrics, health scores, performance,
quality, trends, and risks computed from already-governed artifacts (events,
temporal intelligence, workflows, the operational graph). Analytics is *derived* —
it never becomes a source of truth.

Mandated entities: ``AnalyticsIdentity`` (in ``identity``), ``AnalyticsRecord``,
``AnalyticsMetric``, ``AnalyticsCategory`` (in ``categories``), ``AnalyticsVersion``,
``AnalyticsAuditRecord``, ``AnalyticsLineageRecord``, ``AnalyticsRegistryRecord``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    ANALYTICS_DOMAIN_VERSION, ANALYTICS_METRIC_VERSION, ANALYTICS_REGISTRY_VERSION,
    DETERMINISTIC_EPOCH,
)


# --- metric -------------------------------------------------------------------
@dataclass(frozen=True)
class AnalyticsMetric:
    """A single explainable analytics metric (deterministic, derived).

    ``value`` is a deterministic number; ``unit`` documents its meaning
    (count | rate | ratio | logical_steps | score | distribution | index).
    ``observed`` flags whether the inputs existed (an unobserved metric carries a
    sentinel value and is never treated as a real measurement). ``explanation``
    makes every metric self-describing — health/risk scores must be explainable.
    """

    name: str
    value: float
    unit: str
    observed: bool
    dimension: str = ""             # which analytics dimension produced it
    explanation: str = ""
    inputs: tuple[str, ...] = ()    # the kinds of upstream artifacts it summarizes
    metric_version: str = ANALYTICS_METRIC_VERSION

    def to_dict(self) -> dict:
        return {"name": self.name, "value": self.value, "unit": self.unit,
                "observed": self.observed, "dimension": self.dimension,
                "explanation": self.explanation, "inputs": list(self.inputs),
                "metric_version": self.metric_version}


# --- source reference ---------------------------------------------------------
@dataclass(frozen=True)
class AnalyticsSourceRef:
    """A read-only reference to an upstream artifact an analytics record derives from.

    ``kind`` is one of event | timeline | workflow | graph_node | graph_edge |
    temporal_analytics. ``lineage_id`` (when present) is used as the analytics
    record's lineage parent, so the analytics traces back through the upstream
    artifact to the patient (no analytics-only truth).
    """

    artifact_id: str
    kind: str
    lineage_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {"artifact_id": self.artifact_id, "kind": self.kind,
                "lineage_id": self.lineage_id}


# --- analytics record (derived intelligence) ---------------------------------
@dataclass(frozen=True)
class AnalyticsRecord:
    """A first-class analytics artifact: a derived, explainable intelligence record.

    An analytics record belongs to exactly one :class:`AnalyticsCategory`
    (metrics / health / performance / quality / trend / risk / operational), carries
    a tuple of explainable :class:`AnalyticsMetric`, and references the upstream
    artifacts it was derived from. It is versioned, lineage-tracked and audited
    (orchestration lives in ``service.py``).
    """

    analytics_id: str
    category: str
    scope: str                       # e.g. "case:case+abc" / "operational:all"
    subject_kind: str                # case | review | finding | knowledge | workflow | operational
    subject_id: str
    metrics: tuple[AnalyticsMetric, ...] = ()
    sources: tuple[AnalyticsSourceRef, ...] = ()
    summary: str = ""
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = ANALYTICS_DOMAIN_VERSION

    @property
    def n_metrics(self) -> int:
        return len(self.metrics)

    def metric(self, name: str) -> Optional[AnalyticsMetric]:
        for m in self.metrics:
            if m.name == name:
                return m
        return None

    def state_signature(self) -> str:
        return hash_obj({
            "analytics_id": self.analytics_id, "category": self.category, "scope": self.scope,
            "subject_kind": self.subject_kind, "subject_id": self.subject_id,
            "metrics": [m.to_dict() for m in self.metrics],
            "sources": [s.to_dict() for s in self.sources], "summary": self.summary,
        })

    def to_dict(self) -> dict:
        return {
            "analytics_id": self.analytics_id, "category": self.category, "scope": self.scope,
            "subject_kind": self.subject_kind, "subject_id": self.subject_id,
            "metrics": [m.to_dict() for m in self.metrics],
            "sources": [s.to_dict() for s in self.sources], "summary": self.summary,
            "n_metrics": self.n_metrics, "version": self.version, "lineage_id": self.lineage_id,
            "audit_state": self.audit_state, "domain_version": self.domain_version,
            "state_signature": self.state_signature(),
        }


# --- audit / version / lineage / registry projections ------------------------
@dataclass(frozen=True)
class AnalyticsAuditRecord:
    """An immutable audit event; field-compatible with the shared ImmutableAuditLog."""

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
class AnalyticsVersion:
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
class AnalyticsLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass
class AnalyticsRegistryRecord:
    analytics_id: str
    category: str
    scope: str
    subject_id: str
    version: str
    lineage_id: str
    audit_state: str
    content_signature_value: str
    analytics_registry_version: str = ANALYTICS_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"analytics_id": self.analytics_id, "category": self.category,
                         "version": self.version, "lineage_id": self.lineage_id,
                         "scope": self.scope, "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"analytics_id": self.analytics_id, "category": self.category, "scope": self.scope,
                "subject_id": self.subject_id, "version": self.version,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "content_signature_value": self.content_signature_value,
                "analytics_registry_version": self.analytics_registry_version,
                "content_signature": self.content_signature()}
