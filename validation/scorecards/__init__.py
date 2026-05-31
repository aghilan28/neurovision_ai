"""``validation/scorecards`` — readiness scorecards (P9-I).

Produces nine readiness scorecards from the measured validation evidence, using explicit,
measurable boolean criteria. Each scorecard scores ``passed/total`` and is *ready* when
every criterion passes. Readiness reflects whether each subsystem **works correctly,
deterministically, and traceably** — not an (untuned) accuracy bar; the reference baselines
are deterministic and not tuned (P4), so model metrics are reported as evidence, never
gated on.
"""

from __future__ import annotations

from ..util import clamp01, fingerprint
from ..version import VALIDATION_SCORECARD_VERSION


def _scorecard(dimension: str, criteria: list) -> dict:
    total = len(criteria)
    passed = sum(1 for _, ok, _ in criteria if ok)
    score = clamp01(passed / total) if total else 0.0
    return {
        "dimension": dimension, "score": score, "ready": passed == total,
        "criteria": [{"name": n, "passed": bool(ok), "detail": d} for n, ok, d in criteria],
    }


def build_scorecards(*, pipeline_result, robustness: dict, reliability: dict, calibration: dict,
                     drift: dict, model_benchmark: dict, operations_health: dict) -> dict:
    stages = {s.name: s.ok for s in pipeline_result.stages}
    cards = {}

    cards["eeg_readiness"] = _scorecard("EEG Readiness", [
        ("ingestion_succeeds", stages.get("ingest", False), "valid EEG ingested"),
        ("handles_bad_input_gracefully", robustness.get("all_graceful", False), "no crash on bad input"),
        ("recovers_after_failure", robustness.get("recovered", False), "recovers after bad input"),
    ])
    cards["signal_processing_readiness"] = _scorecard("Signal Processing Readiness", [
        ("processing_succeeds", stages.get("process", False), "clean signal produced"),
        ("pipeline_deterministic", drift["pipeline_drift"]["stable"], "stable across runs"),
    ])
    cards["feature_engineering_readiness"] = _scorecard("Feature Engineering Readiness", [
        ("features_succeed", stages.get("features", False), "feature asset produced"),
        ("feature_vector_nonempty", drift["feature_drift"]["dims"] > 0,
         f"dims={drift['feature_drift']['dims']}"),
    ])
    model_ok = all(m["valid"] for m in calibration.get("models", {}).values()) and bool(model_benchmark)
    cards["model_readiness"] = _scorecard("Model Readiness", [
        ("models_evaluated", bool(model_benchmark.get("models")),
         f"n_models={len(model_benchmark.get('models', {}))}"),
        ("calibration_valid", model_ok, "ECE in [0,1], Brier finite for all models"),
        ("model_lineage_to_patient", reliability_lineage(reliability), "model->...->patient"),
    ])
    cards["inference_readiness"] = _scorecard("Inference Readiness", [
        ("prediction_succeeds", stages.get("predict", False), "prediction produced"),
        ("confidence_reported", calibration.get("ok", False), "confidence+calibration alongside label"),
        ("inference_deterministic", reliability_stress(reliability), "repeated inference deterministic"),
    ])
    backend = operations_health.get("components", {}).get("backend", {})
    cards["backend_readiness"] = _scorecard("Backend Readiness", [
        ("backend_healthy", bool(backend.get("healthy")), backend.get("detail", "")),
        ("workflow_integrity", reliability_workflow(reliability), "5-stage workflow intact"),
    ])
    frontend = operations_health.get("components", {}).get("frontend", {})
    cards["frontend_readiness"] = _scorecard("Frontend Readiness", [
        ("frontend_healthy", bool(frontend.get("healthy")), frontend.get("detail", "")),
    ])
    cards["operations_readiness"] = _scorecard("Operations Readiness", [
        ("system_healthy", bool(operations_health.get("healthy")), "all health components up"),
    ])

    subsystem_ready = all(c["ready"] for c in cards.values())
    overall_score = clamp01(sum(c["score"] for c in cards.values()) / len(cards)) if cards else 0.0
    cards["overall_product_readiness"] = {
        "dimension": "Overall Product Readiness", "score": overall_score,
        "ready": subsystem_ready,
        "criteria": [{"name": f"{k}_ready", "passed": v["ready"], "detail": f"score={v['score']:.2f}"}
                     for k, v in cards.items()],
    }
    return {
        "scorecard_version": VALIDATION_SCORECARD_VERSION,
        "overall_ready": subsystem_ready, "overall_score": overall_score,
        "scorecards": cards,
        "signature": fingerprint({k: v["ready"] for k, v in cards.items()}),
    }


def reliability_lineage(reliability: dict) -> bool:
    return _check(reliability, "lineage_integrity")


def reliability_stress(reliability: dict) -> bool:
    return _check(reliability, "stress_execution")


def reliability_workflow(reliability: dict) -> bool:
    return _check(reliability, "workflow_integrity")


def _check(result: dict, name: str) -> bool:
    for c in result.get("checks", []):
        if c.get("name") == name:
            return bool(c.get("passed"))
    return False


__all__ = ["build_scorecards"]
