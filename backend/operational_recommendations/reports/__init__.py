"""Recommendation reports package (V3-P6)."""

from __future__ import annotations

from .reports import (
    build_guidance_report, build_priority_report, build_optimization_report,
    build_escalation_report, build_recommendation_report, build_validation_report,
    build_audit_report,
)

__all__ = [
    "build_guidance_report", "build_priority_report", "build_optimization_report",
    "build_escalation_report", "build_recommendation_report", "build_validation_report",
    "build_audit_report",
]
