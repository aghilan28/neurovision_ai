"""Policy report builders (reproducible; version-tagged) (V4-P2).

Every report is a deterministic projection of registered policy/constraint/
evaluation artifacts + the registry/audit/lineage state. Reports add no new truth.
"""

from __future__ import annotations

from typing import Any, Sequence

from ..version import POLICY_REPORT_VERSION, POLICY_ENGINE_VERSION


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type, "policy_report_version": POLICY_REPORT_VERSION,
            "policy_engine_version": POLICY_ENGINE_VERSION, "scope": scope}


def build_policy_summary_report(policies: Sequence) -> dict:
    by_category: dict = {}
    by_state: dict = {}
    for p in policies:
        by_category[p.category] = by_category.get(p.category, 0) + 1
        by_state[p.state] = by_state.get(p.state, 0) + 1
    return {**_header("policy_summary", "all"), "n_policies": len(policies),
            "by_category": dict(sorted(by_category.items())),
            "by_state": dict(sorted(by_state.items()))}


def build_policy_registry_report(registry: Any) -> dict:
    return {**_header("policy_registry", "all"), "registry": registry.to_dict()}


def build_constraint_report(registry: Any) -> dict:
    rows = []
    by_type: dict = {}
    for cid in registry.list_constraints():
        c = registry.constraint(cid)
        by_type[c.constraint_type] = by_type.get(c.constraint_type, 0) + 1
        rows.append({"constraint_id": cid, "constraint_type": c.constraint_type,
                     "category": c.category, "subject_kind": c.subject_kind,
                     "n_rules": len(c.rules)})
    return {**_header("constraint", "all"), "n_constraints": len(rows),
            "by_type": dict(sorted(by_type.items())), "constraints": rows}


def build_evaluation_report(registry: Any) -> dict:
    rows = []
    by_outcome: dict = {}
    for eid in registry.list_evaluations():
        e = registry.evaluation(eid)
        by_outcome[e.outcome] = by_outcome.get(e.outcome, 0) + 1
        rows.append({"evaluation_id": eid, "policy_id": e.policy_id, "request": e.request,
                     "subject_id": e.subject_id, "outcome": e.outcome,
                     "n_triggered": len(e.triggered_constraints)})
    return {**_header("evaluation", "all"), "n_evaluations": len(rows),
            "by_outcome": dict(sorted(by_outcome.items())), "evaluations": rows}


def build_policy_governance_report(policies: Sequence) -> dict:
    rows = [{"policy_id": p.policy_id, "state": p.state, "approval_state": p.approval_state,
             "n_approval_events": len(p.approval_history)} for p in policies]
    return {**_header("policy_governance", "all"), "n_policies": len(rows), "policies": rows}


def build_policy_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("policy_validation", scope), "validation": validation_report_dict}


def build_policy_audit_report(audit_log: Any) -> dict:
    return {**_header("policy_audit", "policy_engine"),
            "verified": audit_log.verify(), "audit": audit_log.to_dict()}


def build_policy_lineage_report(policies: Sequence, lineage_tracker: Any) -> dict:
    rows = [{"policy_id": p.policy_id, "lineage_id": p.lineage_id,
             "lineage_verified": lineage_tracker.verify_chain(p.lineage_id) if p.lineage_id
             else False} for p in policies]
    return {**_header("policy_lineage", "all"), "n_policies": len(rows), "policies": rows}
