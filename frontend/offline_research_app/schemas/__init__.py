"""``frontend/offline_research_app/schemas`` — view-model contracts (V1-P8).

Typed, versioned presentation contracts (Section, Visualization, Page, AppView).
The app is presentation-only: these carry data sourced *exclusively* from
registered artifacts; the frontend never computes domain values.
"""

from __future__ import annotations

from .viewmodels import Section, Visualization, Page, AppView, CheckResult, ValidationReport

__all__ = ["Section", "Visualization", "Page", "AppView", "CheckResult", "ValidationReport"]
