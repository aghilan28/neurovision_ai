"""Agent report builders (reproducible; version-tagged) (V4-P5).

Every report is a deterministic projection of registered agent artifacts + the
registry/audit/lineage state. Reports add no new truth.
"""

from __future__ import annotations

from typing import Any, Sequence

from ..version import AGENT_REPORT_VERSION, AGENT_COORDINATION_VERSION
from ..capabilities import capability_summary


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type, "agent_report_version": AGENT_REPORT_VERSION,
            "agent_coordination_version": AGENT_COORDINATION_VERSION, "scope": scope}


def build_agent_summary_report(agents: Sequence) -> dict:
    by_category: dict = {}
    by_state: dict = {}
    for a in agents:
        by_category[a.category] = by_category.get(a.category, 0) + 1
        by_state[a.state.value] = by_state.get(a.state.value, 0) + 1
    return {**_header("agent_summary", "all"), "n_agents": len(agents),
            "by_category": dict(sorted(by_category.items())),
            "by_state": dict(sorted(by_state.items()))}


def build_capability_report(agents: Sequence) -> dict:
    rows = [{"agent_id": a.agent_id, "summary": capability_summary(a)} for a in agents]
    return {**_header("agent_capability", "all"), "n_agents": len(rows), "agents": rows}


def build_assignment_report(registry: Any) -> dict:
    assigns = [registry.assignment(aid) for aid in registry.list_assignments()]
    by_state: dict = {}
    for a in assigns:
        by_state[a.state] = by_state.get(a.state, 0) + 1
    return {**_header("agent_assignment", "all"), "n_assignments": len(assigns),
            "by_state": dict(sorted(by_state.items())),
            "assignments": [a.to_dict() for a in assigns]}


def build_agent_lifecycle_report(agents: Sequence) -> dict:
    rows = [{"agent_id": a.agent_id, "category": a.category, "state": a.state.value,
             "priority": a.priority, "approval_state": a.governance.approval_state} for a in agents]
    return {**_header("agent_lifecycle", "all"), "n_agents": len(rows), "agents": rows}


def build_agent_governance_report(agents: Sequence) -> dict:
    rows = [{"agent_id": a.agent_id, "approval_state": a.governance.approval_state,
             "approval_authority": a.governance.approval_authority,
             "capability_approved": a.governance.capability_approved,
             "assignment_approved": a.governance.assignment_approved,
             "policy_references": list(a.governance.policy_references),
             "n_approval_events": len(a.governance.approval_history)} for a in agents]
    return {**_header("agent_governance", "all"), "n_agents": len(rows), "agents": rows}


def build_agent_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("agent_validation", scope), "validation": validation_report_dict}


def build_agent_audit_report(audit_log: Any) -> dict:
    return {**_header("agent_audit", "agent_coordination"),
            "verified": audit_log.verify(), "audit": audit_log.to_dict()}


def build_agent_lineage_report(agents: Sequence, lineage_tracker: Any) -> dict:
    rows = [{"agent_id": a.agent_id, "lineage_id": a.lineage_id,
             "lineage_verified": lineage_tracker.verify_chain(a.lineage_id) if a.lineage_id
             else False} for a in agents]
    return {**_header("agent_lineage", "all"), "n_agents": len(rows), "agents": rows}
