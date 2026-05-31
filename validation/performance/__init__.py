"""``validation/performance`` — performance validation (P9).

Aggregates benchmark results into a performance view and checks them against explicit,
measurable thresholds. Latency/throughput/memory are reported as **informational**
(wall-clock, not hashed); the pass/fail gate is on **deterministic** evidence
(success/failure rates and determinism), so the verdict is reproducible.
"""

from __future__ import annotations

from ..version import VALIDATION_PERFORMANCE_VERSION

# Deterministic thresholds (success/failure rates + determinism), not timing thresholds.
MIN_SUCCESS_RATE = 1.0          # the deterministic pipeline must succeed every run
REQUIRE_DETERMINISM = True


class PerformanceValidator:
    """Validates benchmark results against deterministic performance thresholds."""

    def validate(self, benchmarks: dict) -> dict:
        checks = []
        for name, result in sorted(benchmarks.items()):
            d = result.to_dict() if hasattr(result, "to_dict") else result
            sr_ok = d["success_rate"] >= MIN_SUCCESS_RATE
            det_ok = d["deterministic"] or not REQUIRE_DETERMINISM
            checks.append({"benchmark": name, "success_rate": d["success_rate"],
                           "deterministic": d["deterministic"],
                           "passed": bool(sr_ok and det_ok),
                           "latency_ms": d["latency_ms"], "throughput_per_s": d["throughput_per_s"]})
        ok = all(c["passed"] for c in checks)
        return {"performance_version": VALIDATION_PERFORMANCE_VERSION, "ok": ok, "checks": checks}


def build_performance_report(benchmarks: dict) -> dict:
    result = PerformanceValidator().validate(benchmarks)
    return {"report_type": "performance", **result,
            "benchmarks": {n: (r.to_dict() if hasattr(r, "to_dict") else r)
                           for n, r in sorted(benchmarks.items())}}


__all__ = ["PerformanceValidator", "build_performance_report", "MIN_SUCCESS_RATE"]
