"""Execution report builders (reproducible; version-tagged) (V4-P6).

Every report is a deterministic projection of registered execution artifacts + the
registry/audit/lineage state. Reports add no new truth.
"""

from __future__ import annotations

from typing import Any, Sequence

from ..version import EXECUTION_REPORT_VERSION, EXECUTION_ORCHESTRATION_VERSION
from ..monitoring import observe, monitoring_summary
from ..coordination import coordination_summary


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type, "execution_report_version": EXECUTION_REPORT_VERSION,
            "execution_orchestration_version": EXECUTION_ORCHESTRATION_VERSION, "scope": scope}


def build_execution_summary_report(executions: Sequence) -> dict:
    by_state: dict = {}
    for e in executions:
        by_state[e.state.value] = by_state.get(e.state.value, 0) + 1
    return {**_header("execution_summary", "all"), "n_executions": len(executions),
            "by_state": dict(sorted(by_state.items()))}


def build_authorization_report(executions: Sequence) -> dict:
    rows = [{"execution_id": e.execution_id,
             "authorization_state": e.governance.authorization_state,
             "authorization_authority": e.governance.authorization_authority,
             "policy_references": list(e.governance.policy_references),
             "n_authorization_events": len(e.governance.authorization_history)}
            for e in executions]
    return {**_header("execution_authorization", "all"), "n_executions": len(rows),
            "executions": rows}


def build_status_report(executions: Sequence) -> dict:
    rows = [{"execution_id": e.execution_id, "status": observe(e).to_dict()}
            for e in executions]
    return {**_header("execution_status", "all"), "n_executions": len(rows), "executions": rows}


def build_monitoring_report(executions: Sequence) -> dict:
    return {**_header("execution_monitoring", "all"),
            "summary": monitoring_summary(list(executions)),
            "executions": [{"execution_id": e.execution_id, "status": observe(e).to_dict()}
                           for e in executions]}


def build_execution_governance_report(executions: Sequence) -> dict:
    rows = [{"execution_id": e.execution_id, "state": e.state.value,
             "authorization_state": e.governance.authorization_state,
             "coordination": coordination_summary(e.context)} for e in executions]
    return {**_header("execution_governance", "all"), "n_executions": len(rows),
            "executions": rows}


def build_execution_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("execution_validation", scope), "validation": validation_report_dict}


def build_execution_audit_report(audit_log: Any) -> dict:
    return {**_header("execution_audit", "execution_orchestration"),
            "verified": audit_log.verify(), "audit": audit_log.to_dict()}


def build_execution_lineage_report(executions: Sequence, lineage_tracker: Any) -> dict:
    rows = [{"execution_id": e.execution_id, "lineage_id": e.lineage_id,
             "lineage_verified": lineage_tracker.verify_chain(e.lineage_id) if e.lineage_id
             else False} for e in executions]
    return {**_header("execution_lineage", "all"), "n_executions": len(rows), "executions": rows}
