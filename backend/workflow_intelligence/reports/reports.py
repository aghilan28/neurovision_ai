"""Workflow report builders (reproducible; version-tagged) (V3-P3)."""

from __future__ import annotations

from typing import Any

from ..version import WORKFLOW_REPORT_VERSION, WORKFLOW_INTELLIGENCE_VERSION
from ..transitions import transition_frequencies


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type, "workflow_report_version": WORKFLOW_REPORT_VERSION,
            "workflow_intelligence_version": WORKFLOW_INTELLIGENCE_VERSION, "scope": scope}


def build_workflow_report(wf: Any) -> dict:
    return {**_header("workflow", wf.workflow_id), "workflow": wf.to_dict()}


def build_transition_report(wf: Any) -> dict:
    return {**_header("transition", wf.workflow_id),
            "workflow_id": wf.workflow_id, "state": wf.state,
            "n_transitions": wf.n_transitions,
            "transitions": [t.to_dict() for t in wf.transitions],
            "frequencies": transition_frequencies(wf.transitions)}


def build_dependency_report(wf: Any) -> dict:
    by_relation: dict = {}
    for d in wf.dependencies:
        by_relation[d.relation] = by_relation.get(d.relation, 0) + 1
    return {**_header("dependency", wf.workflow_id), "workflow_id": wf.workflow_id,
            "n_dependencies": len(wf.dependencies), "by_relation": dict(sorted(by_relation.items())),
            "dependencies": [d.to_dict() for d in wf.dependencies]}


def build_bottleneck_report(wf: Any) -> dict:
    bottleneck_names = {"slow_transitions", "rework_states", "workflow_stall", "wait_states",
                        "dependency_congestion"}
    metrics = [m.to_dict() for m in wf.metrics if m.name in bottleneck_names]
    return {**_header("bottleneck", wf.workflow_id), "workflow_id": wf.workflow_id,
            "detected": list(wf.metadata.bottlenecks), "metrics": metrics}


def build_efficiency_report(wf: Any) -> dict:
    eff_names = {"completion_rate", "mean_transition_steps", "rework_rate", "throughput",
                 "operational_velocity", "workflow_health_score"}
    metrics = [m.to_dict() for m in wf.metrics if m.name in eff_names]
    return {**_header("efficiency", wf.workflow_id), "workflow_id": wf.workflow_id,
            "metrics": metrics}


def build_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("workflow_validation", scope), "validation": validation_report_dict}


def build_audit_report(audit_log: Any) -> dict:
    return {**_header("workflow_audit", "workflow_intelligence"),
            "verified": audit_log.verify(), "audit": audit_log.to_dict()}
