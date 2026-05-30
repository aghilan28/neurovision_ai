"""Operational recommendation domain entities (V3-P6).

Pure data + ``to_dict`` + (where relevant) ``state_signature``. These describe
**explainable operational recommendations** derived from operational/workflow/
system intelligence (V3-P5 analytics + V3-P3 workflows + V3-P4 graph + V3-P1/P2
events/temporal). Every recommendation is explainable, traceable, auditable,
lineage-tracked, governed, evidence-linked, analytics-linked, workflow-linked and
graph-linked. No black-box recommendations.

This layer operates **exclusively on operational intelligence** — it is not
clinical decision support, medical advice, diagnosis, or treatment.

Mandated entities: ``RecommendationIdentity`` (in ``identity``),
``RecommendationRecord``, ``RecommendationContext``, ``RecommendationEvidence``,
``RecommendationPriority``, ``RecommendationVersion``, ``RecommendationAuditRecord``,
``RecommendationLineageRecord``, ``RecommendationRegistryRecord``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    RECOMMENDATION_DOMAIN_VERSION, RECOMMENDATION_CONTEXT_VERSION,
    RECOMMENDATION_EVIDENCE_VERSION, RECOMMENDATION_PRIORITY_VERSION,
    RECOMMENDATION_REGISTRY_VERSION, DETERMINISTIC_EPOCH,
)


# --- evidence -----------------------------------------------------------------
@dataclass(frozen=True)
class RecommendationEvidence:
    """A single piece of evidence supporting a recommendation.

    Evidence is always a reference to a *real* upstream artifact: an analytics
    metric, a workflow, a graph node, a risk score, etc. ``source_kind`` is one of
    analytics | workflow | graph_node | event | temporal_analytics. ``metric_name``
    + ``value`` capture the specific signal cited; ``lineage_id`` (when present) is
    used as a recommendation lineage parent so the recommendation traces to the
    patient. No recommendation may exist without evidence.
    """

    evidence_id: str
    source_kind: str
    source_id: str
    metric_name: str = ""
    value: float = 0.0
    detail: str = ""
    lineage_id: Optional[str] = None
    evidence_version: str = RECOMMENDATION_EVIDENCE_VERSION

    def to_dict(self) -> dict:
        return {"evidence_id": self.evidence_id, "source_kind": self.source_kind,
                "source_id": self.source_id, "metric_name": self.metric_name,
                "value": self.value, "detail": self.detail, "lineage_id": self.lineage_id,
                "evidence_version": self.evidence_version}


# --- context ------------------------------------------------------------------
@dataclass(frozen=True)
class RecommendationContext:
    """A deterministic context bundle aggregated from operational intelligence.

    Aggregates the headline signals the recommendation engines reason over:
    analytics context (per-dimension headline metrics), workflow context, graph
    context, temporal context, risk context, and health context. The context is a
    *derived view* — it adds no new truth; it selects and summarizes existing
    analytics/workflow/graph signals so prioritization/guidance are explainable.
    """

    context_id: str
    scope: str
    analytics_context: dict = field(default_factory=dict)
    workflow_context: dict = field(default_factory=dict)
    graph_context: dict = field(default_factory=dict)
    temporal_context: dict = field(default_factory=dict)
    risk_context: dict = field(default_factory=dict)
    health_context: dict = field(default_factory=dict)
    context_version: str = RECOMMENDATION_CONTEXT_VERSION

    def state_signature(self) -> str:
        return hash_obj({"context_id": self.context_id, "scope": self.scope,
                         "analytics_context": self.analytics_context,
                         "workflow_context": self.workflow_context,
                         "graph_context": self.graph_context,
                         "temporal_context": self.temporal_context,
                         "risk_context": self.risk_context,
                         "health_context": self.health_context})

    def to_dict(self) -> dict:
        return {"context_id": self.context_id, "scope": self.scope,
                "analytics_context": self.analytics_context,
                "workflow_context": self.workflow_context, "graph_context": self.graph_context,
                "temporal_context": self.temporal_context, "risk_context": self.risk_context,
                "health_context": self.health_context, "context_version": self.context_version,
                "state_signature": self.state_signature()}


# --- priority -----------------------------------------------------------------
@dataclass(frozen=True)
class RecommendationPriority:
    """An explainable priority assignment.

    ``level`` is one of low|medium|high|critical; ``score`` is the deterministic
    [0,1] value it was derived from; ``reason`` and the supporting signal lists make
    the assignment explainable (every prioritization must be explainable).
    """

    level: str
    score: float
    reason: str
    supporting_metrics: tuple[str, ...] = ()
    supporting_risks: tuple[str, ...] = ()
    supporting_trends: tuple[str, ...] = ()
    supporting_workflow: tuple[str, ...] = ()
    priority_version: str = RECOMMENDATION_PRIORITY_VERSION

    def to_dict(self) -> dict:
        return {"level": self.level, "score": self.score, "reason": self.reason,
                "supporting_metrics": list(self.supporting_metrics),
                "supporting_risks": list(self.supporting_risks),
                "supporting_trends": list(self.supporting_trends),
                "supporting_workflow": list(self.supporting_workflow),
                "priority_version": self.priority_version}



# --- recommendation record (the explainable output) --------------------------
@dataclass(frozen=True)
class RecommendationRecord:
    """A first-class, explainable operational recommendation.

    A recommendation belongs to exactly one kind (guidance | prioritization |
    optimization | escalation), carries a human-readable ``statement``, a
    :class:`RecommendationPriority`, the :class:`RecommendationEvidence` it cites,
    and the ``context_id`` of the :class:`RecommendationContext` it reasoned over.
    It is **operational only** (never clinical), evidence-linked and analytics-
    linked, versioned, lineage-tracked and audited. A recommendation is a
    *suggestion* — it is never executed, never auto-escalated.
    """

    recommendation_id: str
    kind: str                       # guidance | prioritization | optimization | escalation
    scope: str
    subject_kind: str               # case | review | finding | workflow | queue | operational
    subject_id: str
    statement: str                  # the explainable suggestion (no action taken)
    priority: RecommendationPriority
    evidence: tuple[RecommendationEvidence, ...] = ()
    context_id: Optional[str] = None
    analytics_ids: tuple[str, ...] = ()    # analytics records this links to
    workflow_ids: tuple[str, ...] = ()     # workflows this links to
    graph_ids: tuple[str, ...] = ()        # graph nodes this links to
    rationale: str = ""
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = RECOMMENDATION_DOMAIN_VERSION

    @property
    def n_evidence(self) -> int:
        return len(self.evidence)

    def state_signature(self) -> str:
        return hash_obj({
            "recommendation_id": self.recommendation_id, "kind": self.kind, "scope": self.scope,
            "subject_kind": self.subject_kind, "subject_id": self.subject_id,
            "statement": self.statement, "priority": self.priority.to_dict(),
            "evidence": [e.to_dict() for e in self.evidence], "context_id": self.context_id,
            "analytics_ids": list(self.analytics_ids), "workflow_ids": list(self.workflow_ids),
            "graph_ids": list(self.graph_ids), "rationale": self.rationale,
        })

    def to_dict(self) -> dict:
        return {
            "recommendation_id": self.recommendation_id, "kind": self.kind, "scope": self.scope,
            "subject_kind": self.subject_kind, "subject_id": self.subject_id,
            "statement": self.statement, "priority": self.priority.to_dict(),
            "evidence": [e.to_dict() for e in self.evidence], "context_id": self.context_id,
            "analytics_ids": list(self.analytics_ids), "workflow_ids": list(self.workflow_ids),
            "graph_ids": list(self.graph_ids), "rationale": self.rationale,
            "n_evidence": self.n_evidence, "version": self.version, "lineage_id": self.lineage_id,
            "audit_state": self.audit_state, "domain_version": self.domain_version,
            "state_signature": self.state_signature(),
        }


# --- audit / version / lineage / registry projections ------------------------
@dataclass(frozen=True)
class RecommendationAuditRecord:
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
class RecommendationVersion:
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
class RecommendationLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass
class RecommendationRegistryRecord:
    recommendation_id: str
    kind: str
    scope: str
    subject_id: str
    priority_level: str
    version: str
    lineage_id: str
    audit_state: str
    content_signature_value: str
    recommendation_registry_version: str = RECOMMENDATION_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"recommendation_id": self.recommendation_id, "kind": self.kind,
                         "version": self.version, "lineage_id": self.lineage_id,
                         "scope": self.scope, "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"recommendation_id": self.recommendation_id, "kind": self.kind, "scope": self.scope,
                "subject_id": self.subject_id, "priority_level": self.priority_level,
                "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state,
                "content_signature_value": self.content_signature_value,
                "recommendation_registry_version": self.recommendation_registry_version,
                "content_signature": self.content_signature()}
