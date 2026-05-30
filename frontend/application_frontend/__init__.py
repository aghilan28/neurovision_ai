"""``frontend/application_frontend`` — Application Frontend Platform (Productization P7).

Transforms the application backend into a **usable product**: a real frontend through
which a user can log in, upload an EEG, run an analysis, receive a prediction, view its
confidence + explanation, and access reports. The objective is *user interaction* —
**no deployment, monitoring, or cloud infrastructure** (all out of scope).

**Presentation layer only (NR-8).** It imports **no** domain module (not even
``backend`` as code) — standard library only. It speaks to the backend exclusively
through the abstract :class:`BackendGateway` API-contract port, exchanging plain dicts
that mirror the backend's actual ``v1`` API. A concrete adapter that drives the real
``backend.application_backend.ApplicationAPI`` lives at the sanctioned ``scripts/`` seam
(``scripts.application_frontend_gateway`` / ``scripts.build_application_frontend_snapshot``).

**No duplicated business logic / no bypassed services.** Every action is a backend API
call; the frontend only validates fields for UX, manages deterministic navigation state,
and renders deterministic static HTML (inline CSS, no JavaScript). Uncertainty
(confidence + calibration) is always shown alongside the label (NR-4).

Entry points: :class:`FrontendApp` (the controller), :class:`BackendGateway` (the port),
and the page builders + :func:`layouts.render`.
"""

from __future__ import annotations

from .version import (
    APPLICATION_FRONTEND_VERSION, FRONTEND_DOMAIN_VERSION, FRONTEND_GATEWAY_VERSION,
    FRONTEND_STATE_VERSION, FRONTEND_VIEWMODEL_VERSION, FRONTEND_VALIDATION_VERSION,
    FRONTEND_REPORT_VERSION, CONSUMES_API_VERSION,
)
from .gateway import (
    BackendGateway, GatewayError, is_success, is_unauthorized, ALL_OPERATIONS,
    OP_REGISTER, OP_LOGIN, OP_LOGOUT, OP_UPLOAD_EEG, OP_LIST_EEG, OP_RETRIEVE_EEG,
    OP_START_ANALYSIS, OP_RETRIEVE_PREDICTION, OP_RETRIEVE_CONFIDENCE, OP_RETRIEVE_EXPLANATION,
    OP_LIST_ANALYSIS_HISTORY, OP_LIST_REPORTS,
)
from .domain import (
    FrontendUser, FrontendSession, FrontendUpload, FrontendWorkflow, FrontendPrediction,
    FrontendReport, FrontendValidationState,
)
from .actions import ActionResult
from .state import ApplicationState
from .auth import AuthController
from .uploads import UploadController
from .workflows import AnalysisController, WORKFLOW_STAGES
from .predictions import PredictionController, build_prediction_view
from .reports import ReportController, build_reports_view
from .validation import FrontendValidator, FrontendValidationReport
from .application import FrontendApp
from . import layouts, pages, components, reporting

__all__ = [
    # versions
    "APPLICATION_FRONTEND_VERSION", "FRONTEND_DOMAIN_VERSION", "FRONTEND_GATEWAY_VERSION",
    "FRONTEND_STATE_VERSION", "FRONTEND_VIEWMODEL_VERSION", "FRONTEND_VALIDATION_VERSION",
    "FRONTEND_REPORT_VERSION", "CONSUMES_API_VERSION",
    # gateway
    "BackendGateway", "GatewayError", "is_success", "is_unauthorized", "ALL_OPERATIONS",
    "OP_REGISTER", "OP_LOGIN", "OP_LOGOUT", "OP_UPLOAD_EEG", "OP_LIST_EEG", "OP_RETRIEVE_EEG",
    "OP_START_ANALYSIS", "OP_RETRIEVE_PREDICTION", "OP_RETRIEVE_CONFIDENCE",
    "OP_RETRIEVE_EXPLANATION", "OP_LIST_ANALYSIS_HISTORY", "OP_LIST_REPORTS",
    # domain
    "FrontendUser", "FrontendSession", "FrontendUpload", "FrontendWorkflow",
    "FrontendPrediction", "FrontendReport", "FrontendValidationState",
    # core
    "ActionResult", "ApplicationState", "AuthController", "UploadController",
    "AnalysisController", "WORKFLOW_STAGES", "PredictionController", "build_prediction_view",
    "ReportController", "build_reports_view", "FrontendValidator", "FrontendValidationReport",
    "FrontendApp", "layouts", "pages", "components", "reporting",
]
