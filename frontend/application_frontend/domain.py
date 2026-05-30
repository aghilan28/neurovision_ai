"""Frontend domain model (P7-B) — presentation projections of backend contracts.

These are **not** duplicate domain models: each is a thin, immutable view built *from* a
backend API response body. They carry only what the UI renders, never business logic.
Secrets never appear here (a session holds only a redacted token handle, never the raw
token, which lives in volatile state and is never rendered).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .version import FRONTEND_DOMAIN_VERSION


@dataclass(frozen=True)
class FrontendUser:
    """A signed-in user, projected from the register/login response + dashboard."""

    user_id: str
    username: str
    roles: tuple[str, ...] = ()
    status: str = "active"
    domain_version: str = FRONTEND_DOMAIN_VERSION

    @staticmethod
    def from_body(body: dict, *, username: Optional[str] = None) -> "FrontendUser":
        return FrontendUser(
            user_id=body.get("user_id", ""), username=body.get("username", username or ""),
            roles=tuple(body.get("roles", ()) or ()), status=body.get("status", "active"))

    def to_dict(self) -> dict:
        return {"user_id": self.user_id, "username": self.username,
                "roles": list(self.roles), "status": self.status}


@dataclass(frozen=True)
class FrontendSession:
    """An active session handle. The raw token is NOT stored here."""

    session_id: str
    user_id: str
    active: bool = True

    @staticmethod
    def from_body(body: dict) -> "FrontendSession":
        return FrontendSession(session_id=body.get("session_id", ""),
                               user_id=body.get("user_id", ""), active=True)

    def to_dict(self) -> dict:
        return {"session_id": self.session_id, "user_id": self.user_id, "active": self.active}


@dataclass(frozen=True)
class FrontendUpload:
    """An uploaded EEG file as the user sees it."""

    upload_id: str
    filename: str
    content_fingerprint: str = ""
    size_bytes: int = 0
    status: str = "received"

    @staticmethod
    def from_body(body: dict) -> "FrontendUpload":
        return FrontendUpload(
            upload_id=body.get("upload_id", ""), filename=body.get("filename", ""),
            content_fingerprint=body.get("content_fingerprint", ""),
            size_bytes=int(body.get("size_bytes", 0) or 0), status=body.get("status", "received"))

    def to_dict(self) -> dict:
        return {"upload_id": self.upload_id, "filename": self.filename,
                "content_fingerprint": self.content_fingerprint, "size_bytes": self.size_bytes,
                "status": self.status}


@dataclass(frozen=True)
class FrontendWorkflow:
    """An analysis workflow run as the user sees it (reflects backend workflow state)."""

    analysis_id: str
    workflow_id: str
    prediction_id: str
    status: str
    stages: tuple[str, ...] = ()

    @staticmethod
    def from_body(body: dict) -> "FrontendWorkflow":
        return FrontendWorkflow(
            analysis_id=body.get("analysis_id", ""), workflow_id=body.get("workflow_id", ""),
            prediction_id=body.get("prediction_id", ""), status=body.get("status", "completed"),
            stages=tuple(body.get("stages", ()) or ()))

    def to_dict(self) -> dict:
        return {"analysis_id": self.analysis_id, "workflow_id": self.workflow_id,
                "prediction_id": self.prediction_id, "status": self.status,
                "stages": list(self.stages)}


@dataclass(frozen=True)
class FrontendPrediction:
    """A prediction result projection (prediction + confidence + calibration + explanation)."""

    analysis_id: str
    predicted_class: Optional[int]
    predicted_label: str
    confidence_level: str
    calibration_quality: str
    prediction: dict = field(default_factory=dict)
    confidence: dict = field(default_factory=dict)
    explanation: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "analysis_id": self.analysis_id, "predicted_class": self.predicted_class,
            "predicted_label": self.predicted_label, "confidence_level": self.confidence_level,
            "calibration_quality": self.calibration_quality, "prediction": self.prediction,
            "confidence": self.confidence, "explanation": self.explanation,
        }


@dataclass(frozen=True)
class FrontendReport:
    """A named report the user can view/download (content from the backend)."""

    name: str
    content: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"name": self.name, "content": self.content}


@dataclass(frozen=True)
class FrontendValidationState:
    """A single UI/flow validation result."""

    name: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


__all__ = [
    "FrontendUser", "FrontendSession", "FrontendUpload", "FrontendWorkflow",
    "FrontendPrediction", "FrontendReport", "FrontendValidationState",
]
