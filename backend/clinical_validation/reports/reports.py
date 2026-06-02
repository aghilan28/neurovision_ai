"""Clinical-validation report builders (DRP6-J; reproducible, version-tagged).

Each report is a plain JSON-able dict, deterministic for a given record/registry state
(no wall-clock, no randomness; performance measures are reported but never hashed).
"""

from __future__ import annotations

from typing import Any, Optional

from ..version import CLINICAL_REPORT_VERSION, CLINICAL_VALIDATION_VERSION


def _header(report_type: str, record: Any) -> dict:
    return {"report_type": report_type, "clinical_report_version": CLINICAL_REPORT_VERSION,
            "clinical_validation_version": CLINICAL_VALIDATION_VERSION,
            "validation_id": record.validation_id, "model_id": record.model_id,
            "architecture": record.architecture, "dataset_label": record.dataset_label,
            "benchmark_id": record.benchmark_id, "evidence_id": record.evidence_id,
            "validation_version": record.version.version}


def build_benchmark_report(record: Any, benchmark: Any) -> dict:
    return {**_header("benchmark", record), "benchmark": benchmark.to_dict()}


def build_performance_report(record: Any, performance: Any) -> dict:
    return {**_header("performance", record), "performance": performance.to_dict()}


def build_calibration_report(record: Any, calibration: Any) -> dict:
    return {**_header("calibration", record), "calibration": calibration.to_dict()}


def build_reliability_report(record: Any, reliability: Any) -> dict:
    return {**_header("reliability", record), "reliability": reliability.to_dict()}


def build_comparison_report(comparison: Any) -> dict:
    return {"report_type": "comparison", "clinical_report_version": CLINICAL_REPORT_VERSION,
            "clinical_validation_version": CLINICAL_VALIDATION_VERSION,
            "comparison": comparison.to_dict() if comparison is not None else None}


def build_evidence_report(record: Any, evidence: Any) -> dict:
    return {**_header("evidence", record), "evidence": evidence.to_dict()}


def build_readiness_report(record: Any, readiness: Any) -> dict:
    return {**_header("readiness", record), "readiness": readiness.to_dict()}


def build_audit_report(record: Any, audit_log: Any) -> dict:
    return {**_header("audit", record), "audit_head": audit_log.head,
            "chain_verified": audit_log.verify(), "n_events": len(audit_log),
            "events": [e.to_dict() for e in audit_log.events()]}


def build_lineage_report(record: Any, lineage_tracker: Any) -> dict:
    chain = lineage_tracker.chain(record.lineage_id) if record.lineage_id else []
    return {**_header("lineage", record), "lineage_id": record.lineage_id,
            "chain_verified": lineage_tracker.verify_chain(record.lineage_id) if record.lineage_id
            else False, "chain_length": len(chain), "chain_kinds": [r.kind for r in chain],
            "chain": [r.to_dict() for r in chain]}


def build_clinical_validation_summary(record: Any, readiness: Any, benchmark: Any,
                                      integrity_report: Optional[Any] = None) -> dict:
    out = {**_header("summary", record), "readiness_class": record.readiness_class.value,
           "readiness_score": readiness.score, "status": record.status.value,
           "deterministic_metrics": dict(sorted(benchmark.deterministic_metrics.items())),
           "content_validation_ok": record.validation_ok, "record": record.to_dict()}
    if integrity_report is not None:
        out["integrity_validation"] = integrity_report.to_dict()
        out["ok"] = bool(record.validation_ok and integrity_report.ok)
    else:
        out["ok"] = bool(record.validation_ok)
    return out


__all__ = [
    "build_benchmark_report", "build_performance_report", "build_calibration_report",
    "build_reliability_report", "build_comparison_report", "build_evidence_report",
    "build_readiness_report", "build_audit_report", "build_lineage_report",
    "build_clinical_validation_summary",
]
