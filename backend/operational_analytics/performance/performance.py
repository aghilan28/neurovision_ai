"""Performance engine (V3-P5).

Generates deterministic **performance** analytics: completion performance,
transition performance, workflow performance, review performance, operational
efficiency, latency (in logical steps), and velocity. All metrics are derived from
the already-computed workflow metrics and temporal duration metrics (logical
steps), so they are reproducible and never depend on wall-clock time.
"""

from __future__ import annotations

from ..models.domain import AnalyticsMetric
from ..models.source import AnalyticsSourceView
from ..version import ANALYTICS_PERFORMANCE_ENGINE_VERSION
from ..metrics import _common as C


def _p(name, value, unit, observed, explanation, inputs=()):
    return AnalyticsMetric(name=name, value=float(value), unit=unit, observed=observed,
                           dimension="performance", explanation=explanation, inputs=tuple(inputs))


class PerformanceEngine:
    """Builds the ``performance`` analytics dimension (read-only, deterministic)."""

    engine_version = ANALYTICS_PERFORMANCE_ENGINE_VERSION

    def compute(self, view: AnalyticsSourceView) -> list[AnalyticsMetric]:
        metrics: list[AnalyticsMetric] = []
        workflows = view.workflows()

        def wf_mean(metric_name):
            vals = [w.metric(metric_name).value for w in workflows
                    if w.metric(metric_name) is not None]
            return C.mean(vals), bool(vals)

        # --- completion performance ------------------------------------------
        comp, comp_obs = wf_mean("completion_rate")
        metrics.append(_p("completion_performance", comp, "ratio", comp_obs,
                          "mean workflow completion rate", ["workflow"]))

        # --- transition performance (mean transition steps; lower is faster) -
        steps, steps_obs = wf_mean("mean_transition_steps")
        metrics.append(_p("transition_performance", steps, "logical_steps", steps_obs,
                          "mean logical steps between workflow transitions", ["workflow"]))

        # --- workflow performance (mean workflow health) ---------------------
        wperf, wperf_obs = wf_mean("workflow_health_score")
        metrics.append(_p("workflow_performance", wperf, "score", wperf_obs,
                          "mean workflow health score", ["workflow"]))

        # --- review performance (completed vs started, from events) ----------
        by_type = view.event_counts_by_type()
        started = by_type.get("REVIEW_STARTED", 0)
        completed = by_type.get("REVIEW_COMPLETED", 0)
        metrics.append(_p("review_performance", C.safe_ratio_0_1(completed, max(1, started)),
                          "ratio", started > 0,
                          "fraction of started reviews that completed", ["event"]))

        # --- operational efficiency (throughput) -----------------------------
        thr, thr_obs = wf_mean("throughput")
        metrics.append(_p("operational_efficiency", thr, "ratio", thr_obs,
                          "mean workflow throughput (transitions per event)", ["workflow"]))

        # --- latency metrics (mean temporal lifecycle steps) -----------------
        latency_value = C.SENTINEL_UNOBSERVED
        latency_obs = False
        if view.has_temporal():
            spans = [dm.steps for dm in view.temporal_analytics().metrics
                     if dm.observed and dm.name.endswith("_steps")]
            if spans:
                latency_value = C.mean(spans)
                latency_obs = True
        metrics.append(_p("latency_logical_steps", latency_value, "logical_steps", latency_obs,
                          "mean lifecycle latency in logical steps (temporal)",
                          ["temporal_analytics"]))

        # --- velocity metrics -------------------------------------------------
        vel, vel_obs = wf_mean("operational_velocity")
        metrics.append(_p("velocity", vel, "ratio", vel_obs,
                          "mean workflow operational velocity", ["workflow"]))

        return metrics
