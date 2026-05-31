"""``validation/reporting`` — validation reporting (P9-J).

Assembles the nine deterministic reports (benchmark, performance, reliability, robustness,
calibration, drift, readiness, validation summary, executive summary). The executive
summary answers, with measured evidence, the five questions P9 exists to answer:
how accurate are the models? how reliable is the pipeline? how robust is the system?
how stable are predictions? how ready is the product?
"""

from __future__ import annotations

from ..util import fingerprint
from ..version import VALIDATION_PROGRAM_VERSION, VALIDATION_REPORT_VERSION


def _header(report_type: str) -> dict:
    return {"report_type": report_type, "validation_report_version": VALIDATION_REPORT_VERSION,
            "validation_program_version": VALIDATION_PROGRAM_VERSION}


def build_benchmark_report(benchmarks: dict, model_benchmark: dict) -> dict:
    return {**_header("benchmark"),
            "benchmarks": {n: (r.to_dict() if hasattr(r, "to_dict") else r)
                           for n, r in sorted(benchmarks.items())},
            "model_benchmark": {a: m for a, m in model_benchmark.get("models", {}).items()}}


def build_validation_summary(*, performance, reliability, robustness, calibration, drift,
                             scorecards, reproducibility) -> dict:
    parts = {
        "performance_ok": performance.get("ok"),
        "reliability_ok": reliability.get("ok"),
        "robustness_ok": robustness.get("ok"),
        "calibration_ok": calibration.get("ok"),
        "drift_measured": drift.get("ok"),
        "reproducibility_ok": reproducibility.get("ok"),
        "overall_ready": scorecards.get("overall_ready"),
    }
    return {**_header("validation_summary"), "components": parts,
            "validation_complete": all(v for v in parts.values()),
            "signature": fingerprint(parts)}


def build_executive_summary(*, model_benchmark, reliability, robustness, reproducibility,
                            drift, scorecards) -> dict:
    accuracy = {a: {"accuracy": m["metrics"]["accuracy"], "f1_macro": m["metrics"]["f1_macro"],
                    "ece": m["metrics"]["ece"], "brier": m["metrics"]["brier"]}
                for a, m in model_benchmark.get("models", {}).items()}
    best = max(accuracy.items(), key=lambda kv: kv[1]["accuracy"], default=(None, {}))
    return {
        **_header("executive_summary"),
        "how_accurate_are_the_models": {
            "per_architecture": accuracy,
            "best_architecture": best[0], "best_accuracy": best[1].get("accuracy"),
            "note": "deterministic untuned reference baselines (P4) — metrics are evidence, "
                    "not a tuned accuracy claim"},
        "how_reliable_is_the_pipeline": {
            "reliable": reliability.get("ok"),
            "repeated_execution_deterministic": _check(reliability, "repeated_execution")},
        "how_robust_is_the_system": {
            "graceful_on_bad_input": robustness.get("all_graceful"),
            "recovers": robustness.get("recovered"), "n_cases": robustness.get("n_cases")},
        "how_stable_are_predictions": {
            "reproducible_within_instance": reproducibility.get("within_instance", {}).get("reproducible"),
            "reproducible_across_instances": reproducibility.get("cross_instance", {}).get("reproducible"),
            "pipeline_stable": drift.get("pipeline_drift", {}).get("stable")},
        "how_ready_is_the_product": {
            "overall_ready": scorecards.get("overall_ready"),
            "overall_score": scorecards.get("overall_score"),
            "subsystem_scores": {k: v["score"] for k, v in scorecards.get("scorecards", {}).items()}},
    }


def build_all_reports(*, benchmarks, model_benchmark, performance, reliability, robustness,
                      calibration, drift, scorecards, reproducibility) -> dict:
    from ..performance import build_performance_report
    from ..reliability import build_reliability_report
    from ..robustness import build_robustness_report
    from ..calibration import build_calibration_report
    from ..drift import build_drift_report
    return {
        "benchmark_report": build_benchmark_report(benchmarks, model_benchmark),
        "performance_report": build_performance_report(benchmarks),
        "reliability_report": build_reliability_report(reliability),
        "robustness_report": build_robustness_report(robustness),
        "calibration_report": build_calibration_report(calibration),
        "drift_report": build_drift_report(drift),
        "readiness_report": {**_header("readiness"), **scorecards},
        "validation_summary": build_validation_summary(
            performance=performance, reliability=reliability, robustness=robustness,
            calibration=calibration, drift=drift, scorecards=scorecards,
            reproducibility=reproducibility),
        "executive_summary": build_executive_summary(
            model_benchmark=model_benchmark, reliability=reliability, robustness=robustness,
            reproducibility=reproducibility, drift=drift, scorecards=scorecards),
    }


def _check(result: dict, name: str) -> bool:
    for c in result.get("checks", []):
        if c.get("name") == name:
            return bool(c.get("passed"))
    return False


__all__ = ["build_benchmark_report", "build_validation_summary", "build_executive_summary",
           "build_all_reports"]
