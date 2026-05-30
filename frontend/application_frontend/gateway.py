"""The backend gateway — the API contract surface the frontend consumes (P7).

The frontend imports **no** domain module (NR-8). It therefore talks to the backend
through this abstract :class:`BackendGateway` port, exchanging plain dicts that mirror
the backend's *actual* ``v1`` API contract (the closed ``ApiOperation`` vocabulary, the
``ApiRequest`` params, and the ``ApiResponse`` body/status). A concrete adapter that
drives the real ``backend.application_backend.ApplicationAPI`` lives at the sanctioned
``scripts/`` seam (which may import both layers) — never inside ``frontend/``.

This is the canonical frontend↔backend boundary: **API-only, no code coupling**. The
frontend contains no business logic; it builds requests, calls the gateway, and renders
the responses.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .version import CONSUMES_API_VERSION

# The published API operation vocabulary the client must speak (the protocol contract,
# not duplicated business logic). Mirrors backend ApiOperation values.
OP_REGISTER = "register_user"
OP_LOGIN = "login"
OP_LOGOUT = "logout"
OP_UPLOAD_EEG = "upload_eeg"
OP_LIST_EEG = "list_eeg"
OP_RETRIEVE_EEG = "retrieve_eeg"
OP_START_ANALYSIS = "start_analysis"
OP_RETRIEVE_PREDICTION = "retrieve_prediction"
OP_RETRIEVE_CONFIDENCE = "retrieve_confidence"
OP_RETRIEVE_EXPLANATION = "retrieve_explanation"
OP_LIST_ANALYSIS_HISTORY = "list_analysis_history"
OP_LIST_REPORTS = "list_reports"

ALL_OPERATIONS = (
    OP_REGISTER, OP_LOGIN, OP_LOGOUT, OP_UPLOAD_EEG, OP_LIST_EEG, OP_RETRIEVE_EEG,
    OP_START_ANALYSIS, OP_RETRIEVE_PREDICTION, OP_RETRIEVE_CONFIDENCE, OP_RETRIEVE_EXPLANATION,
    OP_LIST_ANALYSIS_HISTORY, OP_LIST_REPORTS,
)

# Closed response-status vocabulary the UI interprets (mirrors backend ResponseStatus).
STATUS_OK = "ok"
STATUS_CREATED = "created"
STATUS_BAD_REQUEST = "bad_request"
STATUS_UNAUTHORIZED = "unauthorized"
STATUS_FORBIDDEN = "forbidden"
STATUS_NOT_FOUND = "not_found"
STATUS_ERROR = "error"
SUCCESS_STATUSES = frozenset({STATUS_OK, STATUS_CREATED})


class GatewayError(RuntimeError):
    """Raised when the gateway transport itself fails (not an API-level error)."""


class BackendGateway(ABC):
    """Abstract API contract: a single ``handle`` that returns the API response dict."""

    api_version: str = CONSUMES_API_VERSION

    @abstractmethod
    def handle(self, operation: str, params: Optional[dict] = None,
               token: Optional[str] = None) -> dict:
        """Send one request to the backend API and return its response dict.

        The returned dict has the backend ``ApiResponse`` shape:
        ``{"status", "body", "error_code", "api_version", "ok"}``.
        """
        raise NotImplementedError


def is_success(response: dict) -> bool:
    """True when an API response dict represents success."""
    return bool(response.get("ok")) or response.get("status") in SUCCESS_STATUSES


def is_unauthorized(response: dict) -> bool:
    return response.get("status") == STATUS_UNAUTHORIZED


__all__ = [
    "BackendGateway", "GatewayError", "is_success", "is_unauthorized",
    "ALL_OPERATIONS", "SUCCESS_STATUSES",
    "OP_REGISTER", "OP_LOGIN", "OP_LOGOUT", "OP_UPLOAD_EEG", "OP_LIST_EEG", "OP_RETRIEVE_EEG",
    "OP_START_ANALYSIS", "OP_RETRIEVE_PREDICTION", "OP_RETRIEVE_CONFIDENCE",
    "OP_RETRIEVE_EXPLANATION", "OP_LIST_ANALYSIS_HISTORY", "OP_LIST_REPORTS",
    "STATUS_OK", "STATUS_CREATED", "STATUS_BAD_REQUEST", "STATUS_UNAUTHORIZED",
    "STATUS_FORBIDDEN", "STATUS_NOT_FOUND", "STATUS_ERROR",
]
