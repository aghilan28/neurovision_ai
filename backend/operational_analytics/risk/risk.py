"""Risk engine (V3-P5).

Generates deterministic operational **risk** scores and a risk profile: workflow
risk, operational risk, quality risk, knowledge risk, dependency risk, and
bottleneck risk. Each risk is a bounded [0, 1] score (higher = more risk) derived
from already-governed artifacts and is explainable.

This engine generates **risks only** — never recommendations, actions, or guidance
(those belong to V3-P6). It identifies *where* operational risk concentrates so the
recommendation layer can later reason over it.
"""

from __future__ import annotations

from ..models.domain import AnalyticsMetric
from ..models.source import AnalyticsSourceView
from ..version import ANALYTICS_RISK_ENGINE_VERSION
from ..metrics import _common as C


def _r(name, value, observed, explanation, inputs=()):
    return AnalyticsMetric(name=name, value=C.clamp01(value), unit="score", observed=observed,
                           dimension="risk", explanation=explanation, inputs=tuple(inputs))


class RiskEngine:
    """Builds the ``risk`` analytics dimension (read-only, deterministic)."""

    engine_version = ANALYTICS_RISK_ENGINE_VERSION

    def compute(self, view: AnalyticsSourceView) -> list[AnalyticsMetric]:
        metrics: list[AnalyticsMetric] = []
        workflows = view.workflows()
        n_wf = len(workflows)

        # --- workflow risk (incompletion + rework) ---------------------------
        incompletion = C.mean([1.0 - w.metric("completion_rate").value for w in workflows
                               if w.metric("completion_rate") is not None])
        rework = C.mean([w.metric("rework_rate").value for w in workflows
                         if w.metric("rework_rate") is not None])
        workflow_risk = 0.6 * incompletion + 0.4 * rework
        metrics.append(_r("workflow_risk", workflow_risk, bool(workflows),
                          "0.6*incompletion + 0.4*rework over workflows", ["workflow"]))

        # --- bottleneck risk (share of workflows with any bottleneck) --------
        bottlenecked = sum(1 for w in workflows if w.metadata.bottlenecks)
        bottleneck_risk = C.safe_ratio_0_1(bottlenecked, max(1, n_wf))
        metrics.append(_r("bottleneck_risk", bottleneck_risk, bool(workflows),
                          "fraction of workflows exhibiting any bottleneck", ["workflow"]))

        # --- dependency risk (share of waiting/blocked dependencies) ---------
        total_deps = 0
        blocked_waiting = 0
        for w in workflows:
            for d in w.dependencies:
                total_deps += 1
                if d.relation in ("waiting", "blocked"):
                    blocked_waiting += 1
        dependency_risk = C.safe_ratio_0_1(blocked_waiting, max(1, total_deps)) if total_deps else 0.0
        metrics.append(_r("dependency_risk", dependency_risk, total_deps > 0,
                          "fraction of dependencies waiting/blocked", ["workflow"]))

        # --- quality risk (inverse of derived quality signals) ---------------
        by_type = view.event_counts_by_type()
        reopened = by_type.get("REVIEW_REOPENED", 0)
        completed = by_type.get("REVIEW_COMPLETED", 0)
        revised = by_type.get("FINDING_REVISED", 0)
        superseded = by_type.get("FINDING_SUPERSEDED", 0)
        confirmed = by_type.get("FINDING_CONFIRMED", 0)
        review_defect = C.safe_ratio_0_1(reopened, max(1, completed + reopened))
        finding_defect = C.safe_ratio_0_1(revised + superseded,
                                          max(1, confirmed + revised + superseded))
        quality_risk = C.clamp01(0.5 * review_defect + 0.5 * finding_defect)
        obs_quality = (completed + reopened + confirmed + revised + superseded) > 0
        metrics.append(_r("quality_risk", quality_risk, obs_quality,
                          "0.5*review_reopen_rate + 0.5*finding_revision_rate", ["event"]))

        # --- knowledge risk (knowledge gaps / no linked evidence) ------------
        kn_total = sum(v for k, v in by_type.items() if k.startswith("KNOWLEDGE_"))
        linked = by_type.get("KNOWLEDGE_EVIDENCE_LINKED", 0)
        knowledge_risk = (C.clamp01(1.0 - C.safe_ratio_0_1(linked, max(1, kn_total)))
                          if kn_total else 1.0)
        metrics.append(_r("knowledge_risk", knowledge_risk, True,
                          "1 - fraction of knowledge events linking evidence "
                          "(max risk when no knowledge activity)", ["event"]))

        # --- operational risk (composite risk profile) -----------------------
        observed_components = [m.value for m in metrics if m.observed]
        operational_risk = C.mean(observed_components) if observed_components else 0.0
        metrics.append(_r("operational_risk", operational_risk, bool(observed_components),
                          "mean of observed risk components (composite profile)",
                          ["workflow", "event"]))

        return metrics
