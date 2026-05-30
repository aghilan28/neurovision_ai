"""Plan report builders (reproducible; version-tagged) (V4-P3).

Every report is a deterministic projection of registered plan artifacts + the
registry/audit/lineage state. Reports add no new truth.
"""

from __future__ import annotations

from typing import Any, Sequence

from ..version import PLAN_REPORT_VERSION, PLANNING_FOUNDATION_VERSION
from ..dependencies import dependency_summary


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type, "plan_report_version": PLAN_REPORT_VERSION,
            "planning_foundation_version": PLANNING_FOUNDATION_VERSION, "scope": scope}


def build_plan_summary_report(plans: Sequence) -> dict:
    by_category: dict = {}
    by_state: dict = {}
    for p in plans:
        by_category[p.category] = by_category.get(p.category, 0) + 1
        by_state[p.state.value] = by_state.get(p.state.value, 0) + 1
    return {**_header("plan_summary", "all"), "n_plans": len(plans),
            "by_category": dict(sorted(by_category.items())),
            "by_state": dict(sorted(by_state.items()))}


def build_plan_registry_report(registry: Any) -> dict:
    return {**_header("plan_registry", "all"), "registry": registry.to_dict()}


def build_plan_lifecycle_report(plans: Sequence) -> dict:
    rows = [{"plan_id": p.plan_id, "category": p.category, "state": p.state.value,
             "priority": p.priority, "source_goal_id": p.source_goal_id,
             "approval_state": p.governance.approval_state} for p in plans]
    return {**_header("plan_lifecycle", "all"), "n_plans": len(rows), "plans": rows}


def build_plan_dependency_report(registry: Any) -> dict:
    deps = [registry.dependency(did) for did in registry.list_dependencies()]
    return {**_header("plan_dependency", "all"),
            "summary": dependency_summary(deps),
            "dependencies": [d.to_dict() for d in deps]}


def build_plan_governance_report(plans: Sequence) -> dict:
    rows = [{"plan_id": p.plan_id, "approval_state": p.governance.approval_state,
             "approval_authority": p.governance.approval_authority,
             "policy_references": list(p.governance.policy_references),
             "constraint_references": list(p.governance.constraint_references),
             "n_approval_events": len(p.governance.approval_history)} for p in plans]
    return {**_header("plan_governance", "all"), "n_plans": len(rows), "plans": rows}


def build_plan_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("plan_validation", scope), "validation": validation_report_dict}


def build_plan_audit_report(audit_log: Any) -> dict:
    return {**_header("plan_audit", "planning_foundation"),
            "verified": audit_log.verify(), "audit": audit_log.to_dict()}


def build_plan_lineage_report(plans: Sequence, lineage_tracker: Any) -> dict:
    rows = [{"plan_id": p.plan_id, "lineage_id": p.lineage_id,
             "lineage_verified": lineage_tracker.verify_chain(p.lineage_id) if p.lineage_id
             else False} for p in plans]
    return {**_header("plan_lineage", "all"), "n_plans": len(rows), "plans": rows}
