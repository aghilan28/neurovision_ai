"""``certification`` — Deployment Readiness & Production Certification Program (P10).

Transforms the validated product (P1-P9) into a **certified** product: it audits every
phase, runs end-to-end certification, assesses risk, analyses gaps, scores readiness, and
renders a single evidence-based verdict — CERTIFIED / CONDITIONALLY CERTIFIED /
NOT CERTIFIED — with a go/no-go recommendation. The objective is certification; it adds no
capability and modifies nothing.

This is the top-level *certification* layer (peer of ``scripts``/``operations``/
``validation``): it audits the existing systems and modifies none of them. It may import
``backend``/``operations``/``validation`` (lazily); no domain package imports
``certification`` (asserted in tests). The decision is evidence-based — no assumptions, no
optimism, no future promises.
"""

from __future__ import annotations

from .version import (
    CERTIFICATION_PROGRAM_VERSION, CERTIFIED, CONDITIONALLY_CERTIFIED, NOT_CERTIFIED,
)
from .evidence import EvidenceCollector
from .audits import ProductReadinessAudit, EndToEndCertification, RiskAssessment, GapAnalysis
from .deployment import DeploymentReadinessAudit
from .readiness import determine_phase_states
from .compliance import collect_compliance, check_boundaries
from .scorecards import build_scorecards
from .decision import DecisionEngine
from .reports import build_all_reports, build_executive_summary
from .program import run_certification

__all__ = [
    "CERTIFICATION_PROGRAM_VERSION", "CERTIFIED", "CONDITIONALLY_CERTIFIED", "NOT_CERTIFIED",
    "EvidenceCollector", "ProductReadinessAudit", "EndToEndCertification", "RiskAssessment",
    "GapAnalysis", "DeploymentReadinessAudit", "determine_phase_states", "collect_compliance",
    "check_boundaries", "build_scorecards", "DecisionEngine", "build_all_reports",
    "build_executive_summary", "run_certification",
]
