"""``frontend/application_frontend/workflows`` — analysis workflow UI controller (P7-F).

Starts an analysis and **reflects the backend workflow state** (stages, status). It does
**not** recreate the workflow engine — it asks the backend to run the orchestration and
renders whatever state the backend reports. Also surfaces the analysis history.
"""

from __future__ import annotations

from ..actions import ActionResult, from_api_error
from ..domain import FrontendWorkflow
from ..forms import ANALYSIS_FORM
from ..gateway import BackendGateway, OP_LIST_ANALYSIS_HISTORY, OP_START_ANALYSIS, is_success
from ..state import ApplicationState

# The ordered stages the backend workflow executes (the published contract the UI mirrors).
WORKFLOW_STAGES = ("upload", "validate", "process", "features", "predict", "confidence",
                   "explanation")


class AnalysisController:
    def __init__(self, gateway: BackendGateway, state: ApplicationState):
        self.gateway = gateway
        self.state = state

    def start_analysis(self, upload_id: str) -> ActionResult:
        resp = self.gateway.handle(OP_START_ANALYSIS, {"upload_id": upload_id}, self.state.token)
        if not is_success(resp):
            return from_api_error(resp, page="analysis")
        workflow = FrontendWorkflow.from_body(resp["body"])
        self.state.add_workflow(workflow)
        return ActionResult(True, "prediction", "success",
                            "Analysis complete — prediction is ready.",
                            data={"workflow": workflow.to_dict(),
                                  "summary": {k: resp["body"].get(k) for k in
                                              ("predicted_class", "predicted_label",
                                               "confidence_level", "calibration_quality")}})

    def refresh_history(self) -> ActionResult:
        resp = self.gateway.handle(OP_LIST_ANALYSIS_HISTORY, {}, self.state.token)
        if not is_success(resp):
            return from_api_error(resp, page="analysis")
        workflows = [FrontendWorkflow.from_body(b) for b in resp["body"].get("analyses", [])]
        self.state.set_workflows(workflows)
        return ActionResult(True, "analysis", "info", f"{len(workflows)} analysis run(s).",
                            data={"count": len(workflows)})

    @staticmethod
    def stage_progress(workflow: FrontendWorkflow) -> list:
        """A deterministic stage-progress view: each contractual stage + whether it ran."""
        done = set(workflow.stages)
        return [{"stage": s, "done": s in done} for s in WORKFLOW_STAGES]

    @staticmethod
    def analysis_form() -> dict:
        return ANALYSIS_FORM.to_dict()


__all__ = ["AnalysisController", "WORKFLOW_STAGES"]
