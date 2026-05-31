"""Tests for Productization P10 — Deployment Readiness & Production Certification.

Exercises the certification layer over the **real** P1-P9 systems (no substitutes): the
certification framework, readiness framework, gap analysis, risk analysis, scorecards, the
decision engine, reporting, and evidence integrity. A single module-scoped certification run
is shared across assertions.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from certification import (
    run_certification, DecisionEngine, build_scorecards, CERTIFIED, CONDITIONALLY_CERTIFIED,
    NOT_CERTIFIED,
)
from certification.audits import RiskAssessment, GapAnalysis, ProductReadinessAudit
from certification.deployment import DeploymentReadinessAudit

REPO = pathlib.Path(__file__).resolve().parents[1]
VERDICTS = {CERTIFIED, CONDITIONALLY_CERTIFIED, NOT_CERTIFIED}


@pytest.fixture(scope="module")
def cert(eeg_fixtures, tmp_path_factory):
    ws = tmp_path_factory.mktemp("p10_cert")
    return run_certification(dict(eeg_fixtures),
                             validation_kwargs={"benchmark_runs": 2, "reliability_repeats": 2,
                                                "reliability_stress": 2, "cross_instance": False},
                             workspace_dir=str(ws))


# =============================================================================
# Evidence + end-to-end (P10-D)
# =============================================================================
def test_evidence_collected(cert):
    b = cert["evidence"]
    assert {"validation", "e2e", "operations_health", "operations_validation", "deployment",
            "config", "compliance"} <= set(b)
    assert b["signature"]


def test_end_to_end_certification(cert):
    e2e = cert["evidence"]["e2e"]
    assert e2e["ok"] and e2e["n_checks"] == 10
    names = {c["name"] for c in e2e["checks"]}
    assert {"user_login", "eeg_upload", "eeg_processing", "feature_generation",
            "prediction_generation", "confidence_generation", "explanation_generation",
            "report_generation", "operational_monitoring", "recovery_capability"} == names
    assert all(c["passed"] for c in e2e["checks"])


# =============================================================================
# Product readiness audit (P10-B)
# =============================================================================
def test_product_readiness_audit(cert):
    pa = cert["product_audit"]
    assert pa["n_phases"] == 9 and pa["readiness_state"]
    assert pa["readiness_findings"] and pa["evidence_findings"]
    assert pa["gap_findings"]            # disclosed inherited gaps surface as findings


# =============================================================================
# Deployment readiness audit (P10-C)
# =============================================================================
def test_deployment_readiness_audit(cert):
    da = cert["deployment_audit"]
    areas = {a["area"] for a in da["areas"]}
    assert {"build_readiness", "deployment_readiness", "configuration_readiness",
            "recovery_readiness", "monitoring_readiness", "operational_readiness",
            "security_readiness"} == areas
    # security is honestly NOT ready (production secrets must be injected at deploy)
    assert "security_readiness" in da["not_ready_areas"]


# =============================================================================
# Risk assessment (P10-E)
# =============================================================================
def test_risk_assessment(cert):
    risk = cert["risk"]
    cats = {r["category"] for r in risk["risks"]}
    assert {"data", "model", "deployment", "security", "operational"} <= cats
    assert all(r["mitigation_recommendation"] for r in risk["risks"])
    # no CRITICAL risk blocks a non-clinical deployment
    assert risk["open_critical_non_clinical"] == []
    assert risk["critical"]              # at least one critical (clinical-scoped) risk recorded


# =============================================================================
# Gap analysis (P10-F)
# =============================================================================
def test_gap_analysis(cert):
    gap = cert["gap"]
    assert gap["exists"] and gap["partial"] and gap["missing"]
    assert {"CRITICAL", "MAJOR", "MINOR", "INFORMATIONAL"} >= set(gap["by_severity"])
    # clinical deployment is blocked; non-clinical deployment is not
    assert gap["blocks_clinical_deployment"]
    assert gap["blocks_nonclinical_deployment"] == []


# =============================================================================
# Scorecards (P10-G)
# =============================================================================
def test_scorecards(cert):
    sc = cert["scorecards"]["scorecards"]
    assert {"product_readiness", "technical_readiness", "operational_readiness",
            "deployment_readiness", "model_readiness", "validation_readiness",
            "security_readiness", "support_readiness", "overall_readiness"} == set(sc)
    for card in sc.values():
        assert card["criteria"] and "score" in card and "ready" in card


# =============================================================================
# Decision engine (P10-I)
# =============================================================================
def test_decision_engine(cert):
    d = cert["decision"]
    assert d["verdict"] in VERDICTS
    # given the evidence (technically ready; clinical/persistence/security conditions) the
    # honest verdict is CONDITIONALLY CERTIFIED with cited conditions
    assert d["verdict"] == CONDITIONALLY_CERTIFIED
    assert d["conditions"]
    assert {"readiness", "risks", "gaps", "validation", "operations", "deployment"} <= set(
        d["citations"])
    assert d["go_no_go"].startswith("GO")


def test_decision_is_evidence_based_and_pure(cert):
    """Re-deriving the decision from the same evidence yields the same verdict + signature."""
    b = cert["evidence"]
    pa = ProductReadinessAudit().run(b)
    da = DeploymentReadinessAudit().run(b)
    risk = RiskAssessment().run(b)
    gap = GapAnalysis().run(b)
    sc = build_scorecards(b, product_audit=pa, deployment_audit=da, risk=risk, gap=gap)
    d = DecisionEngine().decide(bundle=b, product_audit=pa, deployment_audit=da, risk=risk,
                                gap=gap, scorecards=sc)
    assert d["verdict"] == cert["decision"]["verdict"]
    assert d["signature"] == cert["decision"]["signature"]


# =============================================================================
# Reporting (P10-H)
# =============================================================================
def test_reports_and_executive_summary(cert):
    reports = cert["reports"]
    assert {"deployment_readiness_report", "certification_report", "gap_analysis_report",
            "risk_report", "executive_summary", "production_qualification_report",
            "go_no_go_recommendation"} == set(reports)
    exe = reports["executive_summary"]
    assert {"can_it_be_deployed", "can_it_be_operated", "can_it_be_maintained",
            "can_it_be_trusted", "what_risks_remain", "what_gaps_remain",
            "should_deployment_proceed"} <= set(exe)
    assert reports["go_no_go_recommendation"]["recommendation"].startswith("GO")


# =============================================================================
# Evidence integrity + boundary
# =============================================================================
def test_evidence_integrity_signatures(cert):
    assert cert["signature"] and cert["decision"]["signature"]
    assert cert["scorecards"]["signature"] and cert["product_audit"]["signature"]
    assert cert["risk"]["signature"] and cert["gap"]["signature"]


def test_no_domain_package_imports_certification():
    for pkg in ("preprocessing", "datasets", "ml", "evaluation", "backend", "frontend",
                "operations", "validation"):
        for path in (REPO / pkg).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    assert all(a.name.split(".")[0] != "certification" for a in node.names), path
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    assert node.module.split(".")[0] != "certification", path
