"""``certification/reports`` — certification reporting (P10-H).

Assembles the seven deterministic reports + the executive summary that answers the seven
final questions, and surfaces the single go/no-go recommendation from the decision engine.
"""

from __future__ import annotations

from ..version import CERTIFICATION_REPORT_VERSION


def _header(report_type: str) -> dict:
    return {"report_type": report_type, "certification_report_version": CERTIFICATION_REPORT_VERSION}


def build_executive_summary(*, bundle, decision, risk, gap, scorecards, deployment_audit) -> dict:
    v = bundle["validation"]
    support = scorecards["scorecards"]["support_readiness"]
    return {
        **_header("executive_summary"),
        "can_it_be_deployed": {"verdict": decision["verdict"], "go_no_go": decision["go_no_go"]},
        "can_it_be_operated": {"operations_health": bundle["operations_health"].get("healthy"),
                               "operations_validation": bundle["operations_validation"].get("ok")},
        "can_it_be_maintained": {"support_ready": support["ready"],
                                 "recovery_works": any(c["name"] == "recovery_capability" and c["passed"]
                                                       for c in bundle["e2e"]["checks"])},
        "can_it_be_trusted": {"validation_complete": v.get("validation_complete"),
                              "determinism": v["reproducibility"].get("ok"),
                              "compliance": bundle["compliance"].get("ok")},
        "what_risks_remain": {"critical": risk["critical"], "high": risk["high"]},
        "what_gaps_remain": {"blocks_clinical": gap["blocks_clinical_deployment"],
                             "blocks_nonclinical": gap["blocks_nonclinical_deployment"]},
        "should_deployment_proceed": {"recommendation": decision["go_no_go"],
                                      "scope": decision["scope"], "conditions": decision["conditions"]},
    }


def build_all_reports(*, bundle, product_audit, deployment_audit, risk, gap, scorecards,
                      decision) -> dict:
    return {
        "deployment_readiness_report": {**_header("deployment_readiness"), **deployment_audit},
        "certification_report": {
            **_header("certification"), "verdict": decision["verdict"],
            "evidence_signature": bundle["signature"],
            "product_audit": {"readiness_state": product_audit["readiness_state"],
                              "phase_states": product_audit["phase_states"]},
            "scorecards": scorecards, "decision": decision},
        "gap_analysis_report": {**_header("gap_analysis"), **gap},
        "risk_report": {**_header("risk"), **risk},
        "executive_summary": build_executive_summary(
            bundle=bundle, decision=decision, risk=risk, gap=gap, scorecards=scorecards,
            deployment_audit=deployment_audit),
        "production_qualification_report": {
            **_header("production_qualification"),
            "overall_ready": scorecards["overall_ready"], "overall_score": scorecards["overall_score"],
            "scorecards": {k: {"ready": c["ready"], "score": c["score"]}
                           for k, c in scorecards["scorecards"].items()},
            "verdict": decision["verdict"]},
        "go_no_go_recommendation": {
            **_header("go_no_go"), "recommendation": decision["go_no_go"],
            "verdict": decision["verdict"], "scope": decision["scope"],
            "conditions": decision["conditions"], "rationale": decision["rationale"]},
    }


__all__ = ["build_all_reports", "build_executive_summary"]
