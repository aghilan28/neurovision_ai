"""FrontendApp — the Application Frontend controller (P7).

Ties together the deterministic UI state, the backend gateway, and the page/layout
view-models. It contains **no business logic**: every action calls the backend through
the gateway and renders the response; the only state it owns is presentation/navigation
state. Session expiration is handled centrally (an ``unauthorized`` response clears auth
state and routes to login).
"""

from __future__ import annotations

from typing import Optional

from . import pages
from .actions import ActionResult
from .auth import AuthController
from .gateway import BackendGateway
from .layouts import render as render_html
from .predictions import PredictionController, build_prediction_view
from .reports import ReportController, build_reports_view
from .state import ApplicationState
from .uploads import UploadController
from .workflows import AnalysisController


class FrontendApp:
    """The presentation controller a user (or a test/seam) drives."""

    def __init__(self, gateway: BackendGateway):
        self.gateway = gateway
        self.state = ApplicationState()
        self.auth = AuthController(gateway, self.state)
        self.uploads = UploadController(gateway, self.state)
        self.analysis = AnalysisController(gateway, self.state)
        self.predictions = PredictionController(gateway, self.state)
        self.reports = ReportController(gateway, self.state)

    @property
    def is_authenticated(self) -> bool:
        return self.state.is_authenticated

    # --- result handling (central session-expiration handling) ---------------
    def _handle(self, result: ActionResult) -> ActionResult:
        if not result.ok and result.data.get("status") == "unauthorized":
            self.state.sign_out(expired=True)
            self.state.set_flash("warning", "Your session has expired. Please log in again.")
            return ActionResult(False, "login", "warning",
                                "Your session has expired. Please log in again.")
        self.state.navigate(result.page)
        if result.message:
            self.state.set_flash(result.level, result.message)
        return result

    # --- auth -----------------------------------------------------------------
    def register(self, username: str, password: str, password_confirm: str,
                 role: str = "clinician") -> ActionResult:
        return self._handle(self.auth.register(username, password, password_confirm, role))

    def login(self, username: str, password: str) -> ActionResult:
        return self._handle(self.auth.login(username, password))

    def logout(self) -> ActionResult:
        return self._handle(self.auth.logout())

    # --- dashboard ------------------------------------------------------------
    def dashboard(self) -> ActionResult:
        up = self.uploads.refresh_history()
        if not up.ok and up.data.get("status") == "unauthorized":
            return self._handle(up)
        self.analysis.refresh_history()
        self.state.navigate("dashboard")
        return ActionResult(True, "dashboard", "info", "",
                            data={"uploads": len(self.state.uploads),
                                  "analyses": len(self.state.workflows)})

    # --- uploads --------------------------------------------------------------
    def upload(self, filename: str, content: bytes) -> ActionResult:
        return self._handle(self.uploads.upload(filename, content))

    def refresh_uploads(self) -> ActionResult:
        return self._handle(self.uploads.refresh_history())

    # --- analysis -------------------------------------------------------------
    def start_analysis(self, upload_id: str) -> ActionResult:
        result = self._handle(self.analysis.start_analysis(upload_id))
        if result.ok:
            wf = result.data.get("workflow", {})
            if wf.get("analysis_id"):
                self.predictions.load(wf["analysis_id"])
                self.reports.load(wf["analysis_id"])
                self._enrich_workflow_stages(wf["analysis_id"])
                self._enrich_prediction_summary(wf["analysis_id"], result.data.get("summary", {}))
        return result

    def view_upload(self, upload_id: str) -> ActionResult:
        """View a single upload's details (exercises the backend retrieve_eeg op)."""
        return self._handle(self.uploads.retrieve(upload_id))

    def _enrich_prediction_summary(self, analysis_id: str, summary: dict) -> None:
        """Fill confidence/calibration/label from the analysis summary, which carries
        fields the per-facet retrieve endpoints do not (e.g. calibration_quality)."""
        from .domain import FrontendPrediction
        cached = self.state.predictions.get(analysis_id)
        if cached is None or not summary:
            return
        self.state.cache_prediction(FrontendPrediction(
            analysis_id=cached.analysis_id,
            predicted_class=cached.predicted_class
            if cached.predicted_class is not None else summary.get("predicted_class"),
            predicted_label=cached.predicted_label or str(summary.get("predicted_label", "")),
            confidence_level=cached.confidence_level or str(summary.get("confidence_level", "")),
            calibration_quality=cached.calibration_quality
            or str(summary.get("calibration_quality", "")),
            prediction=cached.prediction, confidence=cached.confidence,
            explanation=cached.explanation))

    def _enrich_workflow_stages(self, analysis_id: str) -> None:
        """Fill a workflow's ordered stages from its workflow report (the analysis
        summary omits them), so the progress view reflects the real backend stages."""
        from .domain import FrontendWorkflow
        reports = self.state.reports.get(analysis_id, [])
        wf_report = next((r.content for r in reports if r.name == "workflow_report"), {})
        stages = wf_report.get("stages") or (wf_report.get("workflow") or {}).get("stages") or []
        if not stages:
            return
        updated = []
        for w in self.state.workflows:
            if w.analysis_id == analysis_id and not w.stages:
                updated.append(FrontendWorkflow(
                    analysis_id=w.analysis_id, workflow_id=w.workflow_id,
                    prediction_id=w.prediction_id, status=w.status, stages=tuple(stages)))
            else:
                updated.append(w)
        self.state.set_workflows(updated)

    def refresh_analyses(self) -> ActionResult:
        return self._handle(self.analysis.refresh_history())

    def load_prediction(self, analysis_id: str) -> ActionResult:
        return self._handle(self.predictions.load(analysis_id))

    def load_reports(self, analysis_id: str) -> ActionResult:
        return self._handle(self.reports.load(analysis_id))

    # --- page rendering (deterministic static HTML) --------------------------
    def render_login(self, field_errors=()) -> str:
        return render_html(pages.login_page(self.state.snapshot(), field_errors=field_errors))

    def render_register(self, field_errors=()) -> str:
        return render_html(pages.register_page(self.state.snapshot(), field_errors=field_errors))

    def render_dashboard(self) -> str:
        return render_html(pages.dashboard_page(self.state.snapshot()))

    def render_upload(self, field_errors=()) -> str:
        return render_html(pages.upload_page(self.state.snapshot(), field_errors=field_errors))

    def render_analysis(self) -> str:
        stage_view = None
        if self.state.workflows:
            latest = self.state.workflows[-1]
            stage_view = self.analysis.stage_progress(latest)
        return render_html(pages.analysis_page(self.state.snapshot(), stage_view=stage_view))

    def render_prediction(self, analysis_id: Optional[str] = None) -> str:
        if analysis_id is None and self.state.predictions:
            analysis_id = next(reversed(self.state.predictions))
        prediction = self.state.predictions.get(analysis_id) if analysis_id else None
        view = build_prediction_view(prediction) if prediction else None
        return render_html(pages.prediction_page(self.state.snapshot(), view))

    def render_reports(self, analysis_id: Optional[str] = None) -> str:
        if analysis_id is None and self.state.reports:
            analysis_id = next(reversed(self.state.reports))
        reports = self.state.reports.get(analysis_id, []) if analysis_id else []
        view = build_reports_view(reports) if reports else None
        return render_html(pages.reports_page(self.state.snapshot(), view, reports))

    def render_current(self) -> str:
        page = self.state.current_page
        return {
            "login": self.render_login, "register": self.render_register,
            "dashboard": self.render_dashboard, "upload": self.render_upload,
            "analysis": self.render_analysis, "prediction": self.render_prediction,
            "reports": self.render_reports,
        }.get(page, self.render_login)()


__all__ = ["FrontendApp"]
