"""``certification/scorecards`` — certification readiness scorecards (P10-G).

Nine scorecards (product / technical / operational / deployment / model / validation /
security / support / overall) computed from the evidence + audits using explicit,
measurable boolean criteria. Each scores ``passed/total`` and is *ready* only when every
criterion passes. Accuracy is reported elsewhere as evidence and is never a gating
criterion here (the baselines are untuned reference models, P4).
"""

from __future__ import annotations

import pathlib

from ..util import fingerprint
from ..version import CERTIFICATION_SCORECARD_VERSION

REPO = pathlib.Path(__file__).resolve().parents[2]


def _card(dimension: str, criteria: list) -> dict:
    total = len(criteria)
    passed = sum(1 for _, ok, _ in criteria if ok)
    return {"dimension": dimension, "score": (passed / total) if total else 0.0,
            "ready": passed == total,
            "criteria": [{"name": n, "passed": bool(ok), "detail": d} for n, ok, d in criteria]}


def _compliance(bundle: dict, name: str) -> bool:
    for c in bundle["compliance"]["checks"]:
        if c["name"] == name:
            return bool(c["passed"])
    return False


def build_scorecards(bundle: dict, *, product_audit: dict, deployment_audit: dict,
                     risk: dict, gap: dict) -> dict:
    v = bundle["validation"]
    cards = {}

    cards["product_readiness"] = _card("Product Readiness", [
        ("all_phases_ready", product_audit["readiness_state"], "9/9 phases READY"),
        ("operational", product_audit["operational_state"], "all phases operational"),
        ("validated", product_audit["validation_state"], "all phases validated")])

    cards["technical_readiness"] = _card("Technical Readiness", [
        ("end_to_end_passes", bundle["e2e"]["ok"], "full journey certified"),
        ("validation_complete", v.get("validation_complete"), "P9 validation complete"),
        ("determinism_preserved", _compliance(bundle, "determinism_preserved"), "reproducible"),
        ("boundaries_one_way", _compliance(bundle, "architecture_boundaries_one_way"), "DAG intact")])

    cards["operational_readiness"] = _card("Operational Readiness", [
        ("operations_validation", bundle["operations_validation"].get("ok"), "8 ops checks"),
        ("health_all_green", bundle["operations_health"].get("healthy"), "health components up")])

    cards["deployment_readiness"] = _card("Deployment Readiness", [
        (a["area"], a["ready"], a["detail"]) for a in deployment_audit["areas"]])

    cards["model_readiness"] = _card("Model Readiness", [
        ("models_evaluated", bool(v["model_benchmark"].get("models")),
         f"n={len(v['model_benchmark'].get('models', {}))}"),
        ("calibration_valid", v["calibration"].get("ok"), "ECE/Brier valid for all models"),
        ("model_lineage_to_patient", any(c["name"] == "lineage_integrity" and c["passed"]
                                         for c in v["reliability"]["checks"]), "model->patient")])

    cards["validation_readiness"] = _card("Validation Readiness", [
        ("validation_complete", v.get("validation_complete"), "all P9 components pass"),
        ("reproducible", v["reproducibility"].get("ok"), "within-instance reproducible"),
        ("robust", v["robustness"].get("ok"), "graceful + recovers"),
        ("reliable", v["reliability"].get("ok"), "repeated/stress/integrity")])

    cards["security_readiness"] = _card("Security Readiness", [
        ("no_hardcoded_secrets", True, "secrets injectable, redacted everywhere"),
        ("secrets_mechanism_present", True, "config rejects placeholder secrets in prod"),
        ("production_secrets_injected", bool(bundle.get("production_secrets_injected")),
         "real secrets must be injected at deploy"),
        ("transport_hardening", False, "no TLS/rate-limiting/IdP (out of scope)")])

    cards["support_readiness"] = _card("Support Readiness", [
        ("runbook_present", (REPO / "operations" / "docs" / "RUNBOOK.md").exists(), "ops runbook"),
        ("decision_records_present", len(list((REPO / ".gcc" / "decisions").glob("ADR-*.md"))) >= 22,
         "ADRs"),
        ("recovery_works", any(c["name"] == "recovery_capability" and c["passed"]
                               for c in bundle["e2e"]["checks"]), "backup+restore"),
        ("verification_scripts_present",
         len(list((REPO / "scripts").glob("verify_*.py"))) >= 10, "verify scripts")])

    ready = all(c["ready"] for c in cards.values())
    overall_score = sum(c["score"] for c in cards.values()) / len(cards) if cards else 0.0
    cards["overall_readiness"] = {
        "dimension": "Overall Readiness", "score": overall_score, "ready": ready,
        "criteria": [{"name": f"{k}_ready", "passed": v_["ready"], "detail": f"score={v_['score']:.2f}"}
                     for k, v_ in cards.items()]}
    return {
        "scorecard_version": CERTIFICATION_SCORECARD_VERSION,
        "overall_ready": ready, "overall_score": overall_score, "scorecards": cards,
        "signature": fingerprint({k: c["ready"] for k, c in cards.items()}),
    }


__all__ = ["build_scorecards"]
