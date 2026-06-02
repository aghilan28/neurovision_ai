"""``frontend/application_frontend/state`` — deterministic UI state (P7-I).

Holds the presentation state the UI needs between interactions: authentication,
session, upload, workflow, prediction, and report state. It is **not** a copy of backend
state — it caches the *responses* the user has seen (projected into frontend domain
objects) plus pure navigation/flash context.

Determinism: every field is set from backend responses or explicit navigation; there is
no wall-clock and no randomness. ``snapshot()`` returns a stable, secret-free dict
(the raw session token is held only in ``_token`` and is never serialized or rendered).
"""

from __future__ import annotations

from typing import Optional

from ..domain import (
    FrontendUser, FrontendSession, FrontendUpload, FrontendWorkflow, FrontendPrediction,
    FrontendReport,
)
from ..util import fingerprint
from ..version import FRONTEND_STATE_VERSION


class ApplicationState:
    """The single, deterministic frontend application state container."""

    def __init__(self) -> None:
        # --- authentication / session state ---
        self.user: Optional[FrontendUser] = None
        self.session: Optional[FrontendSession] = None
        self._token: Optional[str] = None            # volatile; never rendered/serialized
        self.session_expired: bool = False
        # --- navigation / flash ---
        self.current_page: str = "login"
        self.flash: tuple[str, str] = ("", "")        # (level, message)
        # --- domain caches (ordered, deterministic) ---
        self.uploads: list[FrontendUpload] = []
        self.workflows: list[FrontendWorkflow] = []
        self.predictions: dict[str, FrontendPrediction] = {}
        self.reports: dict[str, list[FrontendReport]] = {}

    # --- auth/session ---------------------------------------------------------
    @property
    def is_authenticated(self) -> bool:
        return self.user is not None and self.session is not None and self._token is not None

    @property
    def token(self) -> Optional[str]:
        return self._token

    def sign_in(self, user: FrontendUser, session: FrontendSession, token: str) -> None:
        self.user, self.session, self._token = user, session, token
        self.session_expired = False
        self.current_page = "dashboard"

    def sign_out(self, *, expired: bool = False) -> None:
        self.user = self.session = self._token = None
        self.session_expired = expired
        self.current_page = "login"

    def set_flash(self, level: str, message: str) -> None:
        self.flash = (level, message)

    def clear_flash(self) -> None:
        self.flash = ("", "")

    def navigate(self, page: str) -> None:
        self.current_page = page

    # --- caches ---------------------------------------------------------------
    def add_upload(self, upload: FrontendUpload) -> None:
        self.uploads = [u for u in self.uploads if u.upload_id != upload.upload_id] + [upload]

    def set_uploads(self, uploads: list) -> None:
        self.uploads = list(uploads)

    def add_workflow(self, workflow: FrontendWorkflow) -> None:
        self.workflows = [w for w in self.workflows
                          if w.analysis_id != workflow.analysis_id] + [workflow]

    def set_workflows(self, workflows: list) -> None:
        self.workflows = list(workflows)

    def cache_prediction(self, prediction: FrontendPrediction) -> None:
        self.predictions[prediction.analysis_id] = prediction

    def cache_reports(self, analysis_id: str, reports: list) -> None:
        self.reports[analysis_id] = list(reports)

    # --- deterministic snapshot (secret-free) --------------------------------
    def snapshot(self) -> dict:
        return {
            "state_version": FRONTEND_STATE_VERSION,
            "current_page": self.current_page,
            "authenticated": self.is_authenticated,
            "session_expired": self.session_expired,
            "flash": {"level": self.flash[0], "message": self.flash[1]},
            "user": self.user.to_dict() if self.user else None,
            "session": self.session.to_dict() if self.session else None,
            "uploads": [u.to_dict() for u in self.uploads],
            "workflows": [w.to_dict() for w in self.workflows],
            "predictions": {k: v.to_dict() for k, v in sorted(self.predictions.items())},
            "reports": {k: [r.to_dict() for r in v] for k, v in sorted(self.reports.items())},
        }

    def signature(self) -> str:
        return fingerprint(self.snapshot())


__all__ = ["ApplicationState"]
