"""Governance-intelligence report builders (reproducible; version-tagged) (V4-P7).

Every report is a deterministic projection of an admitted governance-intelligence
record + the registry / audit / lineage state. Reports add no new truth.
"""

from __future__ import annotations

from typing import Any

from ..version import GOVERNANCE_REPORT_VERSION, GOVERNANCE_INTELLIGENCE_VERSION
from ..approvals import approval_metrics
from ..violations import violation_summary
from ..escalations import escalation_summary
from ..risk import risk_summary, highest_risks
from ..analytics import governance_trends, governance_bottlenecks


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type, "governance_report_version": GOVERNANCE_REPORT_VERSION,
            "governance_intelligence_version": GOVERNANCE_INTELLIGENCE_VERSION, "scope": scope}


def build_approval_report(record) -> dict:
    return {**_header("governance_approval", record.scope),
            "metrics": approval_metrics(record.approvals),
            "approvals": [a.to_dict() for a in record.approvals]}


def build_violation_report(record) -> dict:
    return {**_header("governance_violation", record.scope),
            "summary": violation_summary(record.violations),
            "violations": [v.to_dict() for v in record.violations]}


def build_escalation_report(record) -> dict:
    return {**_header("governance_escalation", record.scope),
            "summary": escalation_summary(record.escalations),
            "escalations": [e.to_dict() for e in record.escalations]}


def build_governance_risk_report(record) -> dict:
    return {**_header("governance_risk", record.scope),
            "summary": risk_summary(record.risks),
            "highest_risks": highest_risks(record.risks, limit=10),
            "risks": [r.to_dict() for r in record.risks]}


def build_governance_analytics_report(record, observations=()) -> dict:
    return {**_header("governance_analytics", record.scope),
            "health_score": record.health_score,
            "metrics": [m.to_dict() for m in record.metrics],
            "trends": governance_trends(observations),
            "bottlenecks": governance_bottlenecks(record.approvals, record.risks)}


def build_governance_summary_report(record) -> dict:
    return {**_header("governance_summary", record.scope),
            "intelligence_id": record.intelligence_id, "n_observed": record.n_observed,
            "observed_kinds": list(record.observed_kinds), "health_score": record.health_score,
            "n_approvals": len(record.approvals), "n_violations": len(record.violations),
            "n_escalations": len(record.escalations), "n_risks": len(record.risks),
            "n_high_or_critical_violations": record.n_unresolved_violations,
            "n_high_risks": record.n_high_risks, "version": record.version}


def build_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("governance_validation", scope), "validation": validation_report_dict}


def build_audit_report(audit_log: Any) -> dict:
    return {**_header("governance_audit", "governance_intelligence"),
            "verified": audit_log.verify(), "audit": audit_log.to_dict()}


def build_lineage_report(record, lineage_tracker: Any) -> dict:
    verified = lineage_tracker.verify_chain(record.lineage_id) if record.lineage_id else False
    return {**_header("governance_lineage", record.scope),
            "intelligence_id": record.intelligence_id, "lineage_id": record.lineage_id,
            "lineage_verified": verified}
