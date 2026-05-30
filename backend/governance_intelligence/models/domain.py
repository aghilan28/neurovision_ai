"""Governance-intelligence domain entities (V4-P7).

Pure data + ``to_dict`` + (where relevant) ``state_signature``. Governance
intelligence is **observation about governance** — it never modifies governance,
creates governance rules, or bypasses approval/policy workflows. Every entity here
is *derived* from already-governed artifacts (goals/policies/constraints/plans/
tasks/agents/executions) and is reproducible and auditable.

Mandated entities: ``GovernanceIntelligenceIdentity`` (in ``identity``),
``GovernanceIntelligenceRecord``, ``ApprovalRecord``, ``ViolationRecord``,
``EscalationRecord``, ``GovernanceRiskRecord``, ``GovernanceMetric``,
``GovernanceVersion``, ``GovernanceAuditRecord``, ``GovernanceLineageRecord``,
``GovernanceRegistryRecord``.

The aggregate ``GovernanceIntelligenceRecord`` is frozen + content-addressed (a
governance-intelligence snapshot is immutable once admitted); the service replaces
it via ``dataclasses.replace`` when versioning. All admission goes through the
service's governed path (gate -> lineage -> audit -> version -> registry).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    GOVERNANCE_DOMAIN_VERSION, GOVERNANCE_APPROVAL_VERSION, GOVERNANCE_VIOLATION_VERSION,
    GOVERNANCE_ESCALATION_VERSION, GOVERNANCE_RISK_VERSION, GOVERNANCE_METRIC_VERSION,
    GOVERNANCE_REGISTRY_VERSION, DETERMINISTIC_EPOCH,
)


# --- closed vocabularies ------------------------------------------------------
class GovernedKind:
    """The governed-entity kinds governance intelligence observes (closed set)."""

    GOAL = "goal"
    POLICY = "policy"
    CONSTRAINT = "constraint"
    PLAN = "plan"
    TASK = "task"
    AGENT = "agent"
    EXECUTION = "execution"


GOVERNED_KINDS: frozenset[str] = frozenset({
    GovernedKind.GOAL, GovernedKind.POLICY, GovernedKind.CONSTRAINT, GovernedKind.PLAN,
    GovernedKind.TASK, GovernedKind.AGENT, GovernedKind.EXECUTION,
})


class Severity:
    INFO = "info"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


SEVERITY_RANK: dict[str, int] = {
    Severity.INFO: 0, Severity.LOW: 1, Severity.MODERATE: 2, Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}
SEVERITIES: frozenset[str] = frozenset(SEVERITY_RANK)


class ViolationType:
    POLICY = "policy_violation"
    CONSTRAINT = "constraint_violation"
    GOVERNANCE = "governance_violation"
    APPROVAL = "approval_violation"
    AUTHORIZATION = "authorization_violation"
    LIFECYCLE = "lifecycle_violation"


VIOLATION_TYPES: frozenset[str] = frozenset(
    v for k, v in vars(ViolationType).items() if not k.startswith("_"))


class RiskDimension:
    APPROVAL = "approval_risk"
    EXECUTION = "execution_risk"
    POLICY = "policy_risk"
    CONSTRAINT = "constraint_risk"
    ASSIGNMENT = "assignment_risk"
    GOVERNANCE = "governance_risk"


RISK_DIMENSIONS: frozenset[str] = frozenset(
    v for k, v in vars(RiskDimension).items() if not k.startswith("_"))


class RiskLevel:
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


def risk_level_for(score: float) -> str:
    """Map an explainable [0,1] risk score to a level (deterministic thresholds)."""
    if score >= 0.75:
        return RiskLevel.CRITICAL
    if score >= 0.5:
        return RiskLevel.HIGH
    if score >= 0.25:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


# --- approval record ----------------------------------------------------------
@dataclass(frozen=True)
class ApprovalRecord:
    """Approval intelligence for one governed entity (derived; observation only).

    ``latency_steps`` is a *logical* latency — the number of governance events that
    preceded the terminal approval/authorization decision (never wall-clock). The
    record states whether the entity is approved, denied, or escalated, with the
    deciding authority and policy references.
    """

    approval_id: str
    entity_kind: str
    entity_id: str
    approval_state: str            # approved | pending | rejected | escalated | authorized | denied
    decision: str                  # the terminal decision (permitted/approved/denied/...)
    authority: Optional[str]
    latency_steps: int
    approved: bool
    escalated: bool
    policy_references: tuple[str, ...] = ()
    source_lineage_id: Optional[str] = None
    approval_version: str = GOVERNANCE_APPROVAL_VERSION

    def state_signature(self) -> str:
        return hash_obj({"entity_kind": self.entity_kind, "entity_id": self.entity_id,
                         "approval_state": self.approval_state, "decision": self.decision,
                         "authority": self.authority, "latency_steps": self.latency_steps,
                         "approved": self.approved, "escalated": self.escalated,
                         "policy_references": list(self.policy_references)})

    def to_dict(self) -> dict:
        return {"approval_id": self.approval_id, "entity_kind": self.entity_kind,
                "entity_id": self.entity_id, "approval_state": self.approval_state,
                "decision": self.decision, "authority": self.authority,
                "latency_steps": self.latency_steps, "approved": self.approved,
                "escalated": self.escalated, "policy_references": list(self.policy_references),
                "source_lineage_id": self.source_lineage_id,
                "approval_version": self.approval_version}


# --- violation record ---------------------------------------------------------
@dataclass(frozen=True)
class ViolationRecord:
    """A detected governance violation (derived). Severity + impact analysis."""

    violation_id: str
    entity_kind: str
    entity_id: str
    violation_type: str
    severity: str
    detail: str
    impact: str
    source_lineage_id: Optional[str] = None
    violation_version: str = GOVERNANCE_VIOLATION_VERSION

    def state_signature(self) -> str:
        return hash_obj({"entity_kind": self.entity_kind, "entity_id": self.entity_id,
                         "violation_type": self.violation_type, "severity": self.severity,
                         "detail": self.detail, "impact": self.impact})

    def to_dict(self) -> dict:
        return {"violation_id": self.violation_id, "entity_kind": self.entity_kind,
                "entity_id": self.entity_id, "violation_type": self.violation_type,
                "severity": self.severity, "detail": self.detail, "impact": self.impact,
                "source_lineage_id": self.source_lineage_id,
                "violation_version": self.violation_version}


# --- escalation record --------------------------------------------------------
@dataclass(frozen=True)
class EscalationRecord:
    """Escalation intelligence for one governed entity (derived).

    ``delay_steps`` is a *logical* delay (governance events between the escalation
    request and its outcome). ``effective`` records whether the escalation was
    resolved (a terminal approval/authorization decision followed).
    """

    escalation_id: str
    entity_kind: str
    entity_id: str
    requested: bool
    outcome: str                   # resolved | pending | unresolved
    delay_steps: int
    risk: str                      # the escalation-risk level
    effective: bool
    source_lineage_id: Optional[str] = None
    escalation_version: str = GOVERNANCE_ESCALATION_VERSION

    def state_signature(self) -> str:
        return hash_obj({"entity_kind": self.entity_kind, "entity_id": self.entity_id,
                         "requested": self.requested, "outcome": self.outcome,
                         "delay_steps": self.delay_steps, "risk": self.risk,
                         "effective": self.effective})

    def to_dict(self) -> dict:
        return {"escalation_id": self.escalation_id, "entity_kind": self.entity_kind,
                "entity_id": self.entity_id, "requested": self.requested,
                "outcome": self.outcome, "delay_steps": self.delay_steps, "risk": self.risk,
                "effective": self.effective, "source_lineage_id": self.source_lineage_id,
                "escalation_version": self.escalation_version}


# --- governance risk record ---------------------------------------------------
@dataclass(frozen=True)
class GovernanceRiskRecord:
    """An explainable governance-risk score for one (dimension, entity) (derived)."""

    risk_id: str
    dimension: str
    entity_kind: str
    entity_id: str
    score: float                   # explainable [0,1]
    level: str
    factors: tuple[str, ...]       # the human-readable factors that produced the score
    explanation: str
    source_lineage_id: Optional[str] = None
    risk_version: str = GOVERNANCE_RISK_VERSION

    def state_signature(self) -> str:
        return hash_obj({"dimension": self.dimension, "entity_kind": self.entity_kind,
                         "entity_id": self.entity_id, "score": self.score, "level": self.level,
                         "factors": list(self.factors)})

    def to_dict(self) -> dict:
        return {"risk_id": self.risk_id, "dimension": self.dimension,
                "entity_kind": self.entity_kind, "entity_id": self.entity_id,
                "score": self.score, "level": self.level, "factors": list(self.factors),
                "explanation": self.explanation, "source_lineage_id": self.source_lineage_id,
                "risk_version": self.risk_version}


# --- governance metric --------------------------------------------------------
@dataclass(frozen=True)
class GovernanceMetric:
    """A single governance analytics metric (derived, deterministic)."""

    name: str
    value: float
    unit: str = ""
    detail: str = ""
    metric_version: str = GOVERNANCE_METRIC_VERSION

    def to_dict(self) -> dict:
        return {"name": self.name, "value": self.value, "unit": self.unit,
                "detail": self.detail, "metric_version": self.metric_version}


# --- version ------------------------------------------------------------------
@dataclass(frozen=True)
class GovernanceVersion:
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


# --- audit record -------------------------------------------------------------
@dataclass(frozen=True)
class GovernanceAuditRecord:
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


# --- lineage projection -------------------------------------------------------
@dataclass(frozen=True)
class GovernanceLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


# --- registry record ----------------------------------------------------------
@dataclass
class GovernanceRegistryRecord:
    intelligence_id: str
    scope: str
    version: str
    n_approvals: int
    n_violations: int
    n_escalations: int
    n_risks: int
    n_metrics: int
    health_score: float
    lineage_id: str
    audit_state: str
    content_signature_value: str
    governance_registry_version: str = GOVERNANCE_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"intelligence_id": self.intelligence_id, "scope": self.scope,
                         "version": self.version, "lineage_id": self.lineage_id,
                         "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"intelligence_id": self.intelligence_id, "scope": self.scope,
                "version": self.version, "n_approvals": self.n_approvals,
                "n_violations": self.n_violations, "n_escalations": self.n_escalations,
                "n_risks": self.n_risks, "n_metrics": self.n_metrics,
                "health_score": self.health_score, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state,
                "content_signature_value": self.content_signature_value,
                "governance_registry_version": self.governance_registry_version,
                "content_signature": self.content_signature()}


# --- governance-intelligence aggregate (frozen; content-addressed) -----------
@dataclass(frozen=True)
class GovernanceIntelligenceRecord:
    """The aggregate governance-intelligence snapshot over the observed entities.

    Bundles the derived approval, violation, escalation, and risk records plus the
    governance analytics metrics and the overall governance health score. It is a
    *derived* observation — it never modifies governance. Its lineage parents are the
    lineage nodes of the governed entities it observed, so ``verify_chain`` from this
    record reaches the patient.
    """

    intelligence_id: str
    scope: str
    approvals: tuple = ()
    violations: tuple = ()
    escalations: tuple = ()
    risks: tuple = ()
    metrics: tuple = ()
    health_score: float = 1.0
    n_observed: int = 0
    observed_kinds: tuple[str, ...] = ()
    version: str = ""
    previous_version: Optional[str] = None
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    owner: str = "governance-ops"
    created_at: str = DETERMINISTIC_EPOCH
    domain_version: str = GOVERNANCE_DOMAIN_VERSION

    def version_previous(self) -> Optional[str]:
        return self.previous_version

    @property
    def n_unresolved_violations(self) -> int:
        return sum(1 for v in self.violations if v.severity in (Severity.HIGH, Severity.CRITICAL))

    @property
    def n_high_risks(self) -> int:
        return sum(1 for r in self.risks if r.level in (RiskLevel.HIGH, RiskLevel.CRITICAL))

    def state_signature(self) -> str:
        return hash_obj({
            "intelligence_id": self.intelligence_id, "scope": self.scope,
            "approvals": [a.state_signature() for a in self.approvals],
            "violations": [v.state_signature() for v in self.violations],
            "escalations": [e.state_signature() for e in self.escalations],
            "risks": [r.state_signature() for r in self.risks],
            "metrics": [m.to_dict() for m in self.metrics],
            "health_score": self.health_score, "n_observed": self.n_observed,
            "observed_kinds": list(self.observed_kinds),
        })

    def to_dict(self) -> dict:
        return {
            "intelligence_id": self.intelligence_id, "scope": self.scope,
            "approvals": [a.to_dict() for a in self.approvals],
            "violations": [v.to_dict() for v in self.violations],
            "escalations": [e.to_dict() for e in self.escalations],
            "risks": [r.to_dict() for r in self.risks],
            "metrics": [m.to_dict() for m in self.metrics],
            "health_score": self.health_score, "n_observed": self.n_observed,
            "observed_kinds": list(self.observed_kinds),
            "n_unresolved_violations": self.n_unresolved_violations,
            "n_high_risks": self.n_high_risks, "version": self.version,
            "lineage_id": self.lineage_id, "audit_state": self.audit_state, "owner": self.owner,
            "created_at": self.created_at, "domain_version": self.domain_version,
            "state_signature": self.state_signature(),
        }
