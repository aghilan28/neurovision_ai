"""``operations/monitoring`` — metrics foundation (P8-G).

A dependency-free, in-process metrics registry (counters, gauges, observation summaries)
with helpers for the application / workflow / prediction / system / health / error metric
families, plus a deterministic report. No cloud dependencies, no network — metrics are
generated locally and reported as plain dicts a collector can scrape.
"""

from __future__ import annotations

from typing import Optional

from ..version import OPERATIONS_MONITORING_VERSION


class MetricsRegistry:
    """An in-memory metrics registry. Deterministic: identical inputs -> identical report."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._observations: dict[str, list[float]] = {}

    # --- primitives -----------------------------------------------------------
    def incr(self, name: str, by: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + by

    def set_gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        self._observations.setdefault(name, []).append(float(value))

    def counter(self, name: str) -> int:
        return self._counters.get(name, 0)

    def gauge(self, name: str) -> Optional[float]:
        return self._gauges.get(name)

    # --- metric families ------------------------------------------------------
    def record_request(self, operation: str, status: str) -> None:
        self.incr("app_requests_total")
        self.incr(f"app_requests_total.op={operation}")
        self.incr(f"app_requests_total.status={status}")
        if status not in ("ok", "created"):
            self.incr("app_request_errors_total")

    def record_workflow(self, status: str, n_stages: int) -> None:
        self.incr("workflow_runs_total")
        self.incr(f"workflow_runs_total.status={status}")
        self.observe("workflow_stages", n_stages)

    def record_prediction(self, confidence_level: str, calibration_quality: str) -> None:
        self.incr("predictions_total")
        self.incr(f"predictions_total.confidence={confidence_level}")
        self.incr(f"predictions_total.calibration={calibration_quality}")

    def record_error(self, error_type: str) -> None:
        self.incr("errors_total")
        self.incr(f"errors_total.type={error_type}")

    def record_health(self, component: str, healthy: bool) -> None:
        self.set_gauge(f"health.{component}", 1.0 if healthy else 0.0)

    def set_system(self, *, registry_records: int, uploads: int, workflows: int) -> None:
        self.set_gauge("system_registry_records", registry_records)
        self.set_gauge("system_uploads", uploads)
        self.set_gauge("system_workflows", workflows)

    # --- snapshot / report ----------------------------------------------------
    def _obs_summary(self) -> dict:
        out = {}
        for name, vals in sorted(self._observations.items()):
            if vals:
                out[name] = {"count": len(vals), "sum": sum(vals),
                             "min": min(vals), "max": max(vals),
                             "mean": sum(vals) / len(vals)}
        return out

    def snapshot(self) -> dict:
        return {
            "counters": dict(sorted(self._counters.items())),
            "gauges": dict(sorted(self._gauges.items())),
            "observations": self._obs_summary(),
        }


def build_monitoring_report(registry: MetricsRegistry) -> dict:
    snap = registry.snapshot()
    return {
        "report_type": "monitoring", "monitoring_version": OPERATIONS_MONITORING_VERSION,
        "cloud_dependencies": False,
        "n_counters": len(snap["counters"]), "n_gauges": len(snap["gauges"]),
        "n_observation_series": len(snap["observations"]),
        "metrics": snap,
    }


__all__ = ["MetricsRegistry", "build_monitoring_report"]
