"""``backend/application_backend/api`` — versioned in-process API layer (P6-F).

Structured request/response contracts + the governed dispatcher exposing the closed set
of application operations (upload, list/retrieve EEG, start analysis, retrieve
prediction/confidence/explanation, list analysis history, list reports). No HTTP,
networking, or serving infrastructure (out of scope).
"""

from __future__ import annotations

from .contracts import ApiRequest, ApiResponse, describe_api
from .application_api import ApplicationAPI

__all__ = ["ApiRequest", "ApiResponse", "describe_api", "ApplicationAPI"]
