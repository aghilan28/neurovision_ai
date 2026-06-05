"""``frontend/application_frontend/reports`` — report display (P7-H).

Lists, views, and "downloads" (serializes) the **actual** reports the backend produced
for an analysis (prediction / confidence / calibration / explainability / analysis /
workflow / lineage / inference). Validation + audit summaries are surfaced from the
fields the backend embeds in those reports (chain-verified, audit-verified). The frontend
adds no report content of its own.
"""

from __future__ import annotations

from ..actions import ActionResult, from_api_error
from ..domain import FrontendReport
from ..gateway import BackendGateway, OP_LIST_REPORTS, is_success
from ..state import ApplicationState
from ..util import canonical_json


class ReportController:
    def __init__(self, gateway: BackendGateway, state: ApplicationState):
        self.gateway = gateway
        self.state = state

    def load(self, analysis_id: str) -> ActionResult:
        resp = self.gateway.handle(OP_LIST_REPORTS, {"analysis_id": analysis_id}, self.state.token)
        if not is_success(resp):
            return from_api_error(resp, page="reports")
        raw = resp["body"].get("reports", {})
        # Handle both list-of-dicts and dict-of-dicts formats.
        if isinstance(raw, list):
            reports = [FrontendReport(name=r.get("name", ""), content=r.get("content", {}))
                       for r in raw if isinstance(r, dict)]
            names = [r.name for r in reports]
        else:
            names = resp["body"].get("report_names", sorted(raw))
            reports = [FrontendReport(name=n, content=raw.get(n, {})) for n in names]
        self.state.cache_reports(analysis_id, reports)
        return ActionResult(True, "reports", "info", f"{len(reports)} report(s) available.",
                            data={"report_names": names})

    @staticmethod
    def download(report: FrontendReport) -> str:
        """Serialize a report for download (deterministic canonical JSON)."""
        return canonical_json({"name": report.name, "content": report.content})


def build_reports_view(reports: list) -> dict:
    """A presentation view of an analysis's report set + a validation/audit summary."""
    by_name = {r.name: r.content for r in reports}
    workflow_report = by_name.get("workflow_report", {})
    analysis_report = by_name.get("analysis_report", {})
    lineage_report = by_name.get("lineage_report", {})
    return {
        "report_names": [r.name for r in reports],
        "validation_summary": {
            "workflow_audit_verified": workflow_report.get("audit_verified"),
            "lineage_chain_verified": lineage_report.get("chain_verified"),
            "lineage_chain_kinds": lineage_report.get("chain_kinds", []),
        },
        "audit_summary": {
            "n_audit_events": workflow_report.get("n_audit_events"),
            "audit_head": workflow_report.get("audit_head"),
        },
        "analysis_summary": {
            "predicted_label": analysis_report.get("predicted_label"),
            "confidence_level": analysis_report.get("confidence_level"),
            "calibration_quality": analysis_report.get("calibration_quality"),
        },
    }


__all__ = ["ReportController", "build_reports_view"]
