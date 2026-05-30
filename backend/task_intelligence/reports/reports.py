"""Task report builders (reproducible; version-tagged) (V4-P4).

Every report is a deterministic projection of registered task artifacts + the
registry/audit/lineage state. Reports add no new truth.
"""

from __future__ import annotations

from typing import Any, Sequence

from ..version import TASK_REPORT_VERSION, TASK_INTELLIGENCE_VERSION
from ..dependencies import dependency_summary


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type, "task_report_version": TASK_REPORT_VERSION,
            "task_intelligence_version": TASK_INTELLIGENCE_VERSION, "scope": scope}


def build_task_summary_report(tasks: Sequence) -> dict:
    by_category: dict = {}
    by_state: dict = {}
    for t in tasks:
        by_category[t.category] = by_category.get(t.category, 0) + 1
        by_state[t.state.value] = by_state.get(t.state.value, 0) + 1
    return {**_header("task_summary", "all"), "n_tasks": len(tasks),
            "by_category": dict(sorted(by_category.items())),
            "by_state": dict(sorted(by_state.items()))}


def build_task_registry_report(registry: Any) -> dict:
    return {**_header("task_registry", "all"), "registry": registry.to_dict()}


def build_task_lifecycle_report(tasks: Sequence) -> dict:
    rows = [{"task_id": t.task_id, "category": t.category, "state": t.state.value,
             "priority": t.priority, "source_plan_id": t.source_plan_id,
             "approval_state": t.governance.approval_state} for t in tasks]
    return {**_header("task_lifecycle", "all"), "n_tasks": len(rows), "tasks": rows}


def build_task_dependency_report(registry: Any) -> dict:
    deps = [registry.dependency(did) for did in registry.list_dependencies()]
    return {**_header("task_dependency", "all"),
            "summary": dependency_summary(deps),
            "dependencies": [d.to_dict() for d in deps]}


def build_task_governance_report(tasks: Sequence) -> dict:
    rows = [{"task_id": t.task_id, "approval_state": t.governance.approval_state,
             "approval_authority": t.governance.approval_authority,
             "policy_references": list(t.governance.policy_references),
             "constraint_references": list(t.governance.constraint_references),
             "n_approval_events": len(t.governance.approval_history)} for t in tasks]
    return {**_header("task_governance", "all"), "n_tasks": len(rows), "tasks": rows}


def build_task_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("task_validation", scope), "validation": validation_report_dict}


def build_task_audit_report(audit_log: Any) -> dict:
    return {**_header("task_audit", "task_intelligence"),
            "verified": audit_log.verify(), "audit": audit_log.to_dict()}


def build_task_lineage_report(tasks: Sequence, lineage_tracker: Any) -> dict:
    rows = [{"task_id": t.task_id, "lineage_id": t.lineage_id,
             "lineage_verified": lineage_tracker.verify_chain(t.lineage_id) if t.lineage_id
             else False} for t in tasks]
    return {**_header("task_lineage", "all"), "n_tasks": len(rows), "tasks": rows}
