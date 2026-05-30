"""Decision-support report builders (reproducible; version-tagged) (V2-P6)."""

from __future__ import annotations

from typing import Any

from ..version import DECISION_REPORT_VERSION, DECISION_SUPPORT_VERSION


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type, "decision_report_version": DECISION_REPORT_VERSION,
            "decision_support_version": DECISION_SUPPORT_VERSION, "scope": scope}


def build_evidence_report(bundle: Any) -> dict:
    return {**_header("evidence", f"context:{bundle.context_id}"), "bundle_id": bundle.bundle_id,
            "size": bundle.size, "items": [i.to_dict() for i in bundle.items],
            "version": bundle.version, "lineage_id": bundle.lineage_id}


def build_risk_report(risk: Any) -> dict:
    return {**_header("risk", f"context:{risk.context_id}"), "risk_id": risk.risk_id,
            "band": risk.band.value, "aggregate": risk.aggregate,
            "components": [c.to_dict() for c in risk.components],
            "version": risk.version, "lineage_id": risk.lineage_id}


def build_prioritization_report(pr: Any) -> dict:
    return {**_header("prioritization", f"context:{pr.context_id}"), "priority_id": pr.priority_id,
            "level": pr.level.value, "score": pr.score, "reason": pr.reason,
            "factors": [f.to_dict() for f in pr.factors],
            "supporting_evidence": list(pr.supporting_evidence),
            "version": pr.version, "lineage_id": pr.lineage_id}


def build_guidance_report(g: Any) -> dict:
    return {**_header("guidance", f"context:{g.context_id}"), "guidance_id": g.guidance_id,
            "items": [i.to_dict() for i in g.items], "version": g.version, "lineage_id": g.lineage_id}


def build_decision_support_report(record: Any, context: Any, bundle: Any, risk: Any,
                                  prioritization: Any, guidance: Any) -> dict:
    return {
        **_header("decision_support", f"case:{record.case_id}"),
        "record_id": record.record_id, "patient_id": record.patient_id, "case_id": record.case_id,
        "priority": {"level": prioritization.level.value, "score": prioritization.score,
                     "reason": prioritization.reason},
        "risk": {"band": risk.band.value, "aggregate": risk.aggregate,
                 "components": {c.name: c.value for c in risk.components}},
        "evidence": {"count": bundle.size, "ranking": list(bundle.ranking)},
        "guidance": [{"category": it.category.value, "message": it.message} for it in guidance.items],
        "context_counts": dict(context.counts), "context_completeness": dict(context.completeness),
        "explanation": record.explanation,
        "references": {"context_id": context.context_id, "evidence_bundle_id": bundle.bundle_id,
                       "risk_id": risk.risk_id, "prioritization_id": prioritization.priority_id,
                       "guidance_id": guidance.guidance_id},
    }


def build_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("validation", scope), "validation": validation_report_dict}


def build_registry_report(registry: Any) -> dict:
    return {**_header("registry", "decision_support"), "registry": registry.to_dict()}
