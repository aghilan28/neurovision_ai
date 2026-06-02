"""Goal report builders (reproducible; version-tagged) (V4-P1).

Every report is a deterministic projection of registered goal artifacts + the
registry/audit/lineage state. Reports add no new truth.
"""

from __future__ import annotations

from typing import Any, Sequence

from ..version import GOAL_REPORT_VERSION, GOAL_INTELLIGENCE_VERSION
from ..taxonomy import GOAL_CATEGORIES


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type, "goal_report_version": GOAL_REPORT_VERSION,
            "goal_intelligence_version": GOAL_INTELLIGENCE_VERSION, "scope": scope}


def build_goal_summary_report(goals: Sequence) -> dict:
    by_category: dict = {}
    by_state: dict = {}
    for g in goals:
        by_category[g.category] = by_category.get(g.category, 0) + 1
        by_state[g.state.value] = by_state.get(g.state.value, 0) + 1
    return {**_header("goal_summary", "all"), "n_goals": len(goals),
            "by_category": dict(sorted(by_category.items())),
            "by_state": dict(sorted(by_state.items()))}


def build_goal_registry_report(registry: Any) -> dict:
    return {**_header("goal_registry", "all"), "registry": registry.to_dict()}


def build_goal_lifecycle_report(goals: Sequence) -> dict:
    rows = [{"goal_id": g.goal_id, "category": g.category, "state": g.state.value,
             "priority": g.priority, "approval_state": g.governance.approval_state}
            for g in goals]
    return {**_header("goal_lifecycle", "all"), "n_goals": len(rows), "goals": rows}


def build_goal_relationship_report(registry: Any) -> dict:
    rels = [registry.relationship(rid).to_dict() for rid in registry.list_relationships()]
    return {**_header("goal_relationship", "all"), "n_relationships": len(rels),
            "relationships": rels}


def build_goal_governance_report(goals: Sequence) -> dict:
    rows = [{"goal_id": g.goal_id, "approval_state": g.governance.approval_state,
             "approval_authority": g.governance.approval_authority,
             "policy_references": list(g.governance.policy_references),
             "n_approval_events": len(g.governance.approval_history)} for g in goals]
    return {**_header("goal_governance", "all"), "n_goals": len(rows), "goals": rows}


def build_goal_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("goal_validation", scope), "validation": validation_report_dict}


def build_goal_audit_report(audit_log: Any) -> dict:
    return {**_header("goal_audit", "goal_intelligence"),
            "verified": audit_log.verify(), "audit": audit_log.to_dict()}


def build_goal_lineage_report(goals: Sequence, lineage_tracker: Any) -> dict:
    rows = [{"goal_id": g.goal_id, "lineage_id": g.lineage_id,
             "lineage_verified": lineage_tracker.verify_chain(g.lineage_id) if g.lineage_id
             else False} for g in goals]
    return {**_header("goal_lineage", "all"), "n_goals": len(rows), "goals": rows}


def all_categories() -> tuple:
    return tuple(sorted(GOAL_CATEGORIES))
