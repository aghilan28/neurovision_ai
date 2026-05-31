"""``backend/operations_platform/reports`` — deterministic operations reports (T4-H).

Eight reports: Health / Monitoring / Diagnostics / Qualification / Readiness / Audit /
Lineage / Operational Summary. Each is a pure function of the (already deterministic) records,
so it reproduces byte-for-byte for a given observed product state.
"""

from __future__ import annotations

from typing import Optional

from ..version import OPS_REPORT_VERSION


def _h(report_type: str) -> dict:
    return {"report_type": report_type, "ops_report_version": OPS_REPORT_VERSION}


def build_health_report(health) -> dict:
    return {**_h("health"), "health": health.to_dict()}


def build_monitoring_report(metrics) -> dict:
    # deterministic counts + the *names* of informational measures tracked (not volatile values)
    return {**_h("monitoring"),
            "deterministic_metrics": {k: round(float(v), 9)
                                      for k, v in sorted(metrics.deterministic_metrics.items())},
            "informational_measures_tracked": sorted(metrics.informational_metrics.keys()),
            "metrics_snapshot_id": metrics.metrics_snapshot_id,
            "signature": metrics.signature()}


def build_diagnostics_report(diagnostic) -> dict:
    return {**_h("diagnostics"), "diagnostics": diagnostic.to_dict()}


def build_qualification_report(qualification) -> dict:
    return {**_h("qualification"), "qualification": qualification.to_dict()}


def build_readiness_report(readiness) -> dict:
    return {**_h("readiness"), "readiness": readiness.to_dict()}


def build_audit_report(audit_log, *, subject: str) -> dict:
    return {**_h("audit"), "subject": subject, "audit_head": audit_log.head,
            "chain_verified": audit_log.verify(), "n_events": len(audit_log),
            "events": [e.to_dict() for e in audit_log.events()]}


def build_lineage_report(tracker, lineage_id: Optional[str]) -> dict:
    chain = tracker.chain(lineage_id) if lineage_id else []
    return {**_h("lineage"), "lineage_id": lineage_id,
            "chain_verified": tracker.verify_chain(lineage_id) if lineage_id else False,
            "chain_length": len(chain), "chain_kinds": sorted({r.kind for r in chain}),
            "chain": [r.to_dict() for r in chain]}


def build_operational_summary_report(*, health, metrics, diagnostic, qualification,
                                     readiness) -> dict:
    return {**_h("operational_summary"),
            "health_overall": health.overall.value,
            "deterministic_metrics": {k: round(float(v), 9)
                                      for k, v in sorted(metrics.deterministic_metrics.items())},
            "diagnostics_ok": diagnostic.ok, "root_causes": list(diagnostic.root_causes),
            "qualification_status": qualification.status.value,
            "qualification_available": f"{qualification.n_available}/{qualification.n_targets}",
            "readiness_classification": readiness.classification.value,
            "readiness_score": round(readiness.score, 9),
            "ready_for_deployment":
                readiness.classification.value == "READY_FOR_DEPLOYMENT"}


__all__ = [
    "build_health_report", "build_monitoring_report", "build_diagnostics_report",
    "build_qualification_report", "build_readiness_report", "build_audit_report",
    "build_lineage_report", "build_operational_summary_report",
]
