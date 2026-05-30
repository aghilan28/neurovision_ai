"""GovernanceIntelligenceService — the governed orchestration hub for V4-P7.

Derives **governance intelligence** (approvals, violations, escalations, risks,
analytics, and the human-oversight monitoring view) from already-governed upstream
artifacts — goals (V4-P1), policies/constraints (V4-P2), plans (V4-P3), tasks
(V4-P4), agents (V4-P5), and executions (V4-P6) — and admits each
governance-intelligence record through one governed path: governance-intelligence
gate (architecture/quality/context/risk/governance) -> shared-lineage node parented
by the observed artifacts' lineage nodes -> immutable audit event ->
content-addressed version -> registry sync.

Because the record's lineage parents are the observed artifacts' nodes (which trace
to the patient), a single ``verify_chain`` spans Patient -> ... -> Goal -> Policy ->
Plan -> Task -> Agent -> Execution -> Governance Intelligence. Governance
intelligence is **observation only** — it makes governance observable, analyzable,
auditable, and explainable; it never creates governance rules, modifies governance
state, or bypasses policy/approval workflows. Shares the platform's single
``ml.lineage.LineageTracker`` and the shared ``ImmutableAuditLog`` — no parallel
lineage/audit/governance.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional, Sequence

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .identity import mint_intelligence
from .models.domain import GovernanceIntelligenceRecord, GovernanceVersion, GovernanceRegistryRecord
from .models.observation import GovernanceObservationView
from .governance import GovernanceIntelligenceGate, GovernanceIntelligenceError
from .registry import GovernanceRegistry
from .validation import GovernanceValidator
from .audit import make_governance_audit_log
from .lineage import make_governance_lineage
from .approvals import build_approvals
from .violations import detect_violations
from .escalations import build_escalations
from .risk import build_risks
from .analytics import build_metrics, governance_health
from .monitoring import monitoring_summary
from .reports import (
    build_approval_report, build_violation_report, build_escalation_report,
    build_governance_risk_report, build_governance_analytics_report,
    build_governance_summary_report, build_validation_report, build_audit_report,
    build_lineage_report,
)


class GovernanceIntelligenceService:
    """Stateful service: governance-intelligence registry, shared lineage, immutable audit."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[GovernanceRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or GovernanceRegistry()
        self.audit = make_governance_audit_log()
        self.gate = GovernanceIntelligenceGate()
        self.validator = GovernanceValidator()
        self._view: Optional[GovernanceObservationView] = None

    # --- source view ----------------------------------------------------------
    def load_sources(self, *, goals: Sequence = (), policies: Sequence = (),
                     constraints: Sequence = (), plans: Sequence = (), tasks: Sequence = (),
                     agents: Sequence = (), executions: Sequence = ()
                     ) -> "GovernanceIntelligenceService":
        """Provide the already-governed upstream artifacts to derive intelligence from."""
        self._view = GovernanceObservationView.from_sources(
            goals=goals, policies=policies, constraints=constraints, plans=plans, tasks=tasks,
            agents=agents, executions=executions)
        return self

    def view(self) -> GovernanceObservationView:
        if self._view is None:
            raise RuntimeError("call load_sources(...) before deriving governance intelligence")
        return self._view

    def observations(self) -> list:
        return self.view().all()

    # --- build (the governed admission path) ---------------------------------
    def build(self, *, scope: str = "operational",
              created_at: str = DETERMINISTIC_EPOCH) -> GovernanceIntelligenceRecord:
        """Derive + admit the aggregate governance-intelligence record over the sources."""
        view = self.view()
        observations = view.all()

        approvals = tuple(build_approvals(observations))
        violations = tuple(detect_violations(observations))
        escalations = tuple(build_escalations(observations))
        risks = tuple(build_risks(observations))
        metrics = tuple(build_metrics(observations, approvals, violations, escalations, risks))
        health = governance_health(approvals, violations, escalations, risks)

        signature = _signature(scope, observations)
        ident = mint_intelligence(scope, signature)
        record = GovernanceIntelligenceRecord(
            intelligence_id=ident.id, scope=scope, approvals=approvals, violations=violations,
            escalations=escalations, risks=risks, metrics=metrics, health_score=health,
            n_observed=len(observations), observed_kinds=view.kinds(), created_at=created_at)

        parents = view.parents()
        report = self.gate.evaluate(record=record, parents=parents,
                                    requires_lineage=len(parents) > 0)
        self.gate.raise_if_failed(report)

        node = self.lineage.record(make_governance_lineage(
            record.intelligence_id, parents=parents, scope=scope, reason="generated",
            created_at=created_at))
        self.audit.append("governance_intelligence_generated",
                          {"intelligence_id": record.intelligence_id, "scope": scope,
                           "lineage_id": node.lineage_id, "n_observed": len(observations),
                           "n_approvals": len(approvals), "n_violations": len(violations),
                           "n_escalations": len(escalations), "n_risks": len(risks)},
                          created_at=created_at)
        record = replace(record, lineage_id=node.lineage_id, audit_state=self.audit.head)
        record = self._finalize(record, reason="generated", created_at=created_at)
        return record

    # --- monitoring (human-oversight projections; observe only) --------------
    def monitoring(self, record: GovernanceIntelligenceRecord) -> dict:
        return monitoring_summary(self.observations(), record.violations, record.escalations,
                                  record.risks)

    # --- validation + reports -------------------------------------------------
    def validate(self, record: GovernanceIntelligenceRecord):
        return self.validator.validate(record=record, registry=self.registry,
                                       audit_log=self.audit, lineage_tracker=self.lineage)

    def reports(self, record: GovernanceIntelligenceRecord) -> dict:
        return {
            "governance_summary_report": build_governance_summary_report(record),
            "approval_report": build_approval_report(record),
            "violation_report": build_violation_report(record),
            "escalation_report": build_escalation_report(record),
            "governance_risk_report": build_governance_risk_report(record),
            "governance_analytics_report": build_governance_analytics_report(
                record, self.observations()),
            "governance_audit_report": build_audit_report(self.audit),
            "governance_lineage_report": build_lineage_report(record, self.lineage),
        }

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_validation_report(scope, validation_report_dict)

    # --- internals ------------------------------------------------------------
    def _finalize(self, record: GovernanceIntelligenceRecord, *, reason: str,
                  created_at: str) -> GovernanceIntelligenceRecord:
        """Bump the version (chained), audit it, then sync + index the registry."""
        iid = record.intelligence_id
        version = GovernanceVersion.compute(record.state_signature(), record.version_previous())
        record = replace(record, version=version)
        self.audit.append("governance_intelligence_version_changed",
                          {"intelligence_id": iid, "version": version, "reason": reason},
                          created_at=created_at)
        record = replace(record, audit_state=self.audit.head)
        self.registry.register(GovernanceRegistryRecord(
            intelligence_id=iid, scope=record.scope, version=version,
            n_approvals=len(record.approvals), n_violations=len(record.violations),
            n_escalations=len(record.escalations), n_risks=len(record.risks),
            n_metrics=len(record.metrics), health_score=record.health_score,
            lineage_id=record.lineage_id, audit_state=record.audit_state,
            content_signature_value=record.state_signature()))
        self.registry.index(record)
        self.audit.append("governance_intelligence_registered",
                          {"intelligence_id": iid, "version": version}, created_at=created_at)
        record = replace(record, audit_state=self.audit.head)
        return record


def _signature(scope: str, observations: Sequence) -> str:
    from ml.provenance import hash_obj
    return hash_obj({"scope": scope,
                     "observations": [o.to_dict() for o in observations]})


__all__ = ["GovernanceIntelligenceService", "GovernanceIntelligenceError"]
