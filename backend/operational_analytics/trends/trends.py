"""Trend engine (V3-P5).

Generates deterministic **trends** that derive from temporal intelligence: temporal,
workflow, review, finding, knowledge, and operational trends. Because the platform
forbids wall-clock, a "trend" is computed over the deterministically-ordered event
stream split into two equal logical halves (earlier vs later); the trend direction
(rising / falling / flat) and magnitude are reproducible functions of those halves.

All trends derive from the ordered events (V3-P2 ``EventSourceView``) — no
wall-clock, no sampling, no randomness.
"""

from __future__ import annotations

from typing import Sequence

from ..models.domain import AnalyticsMetric
from ..models.source import AnalyticsSourceView
from ..version import ANALYTICS_TREND_ENGINE_VERSION
from ..metrics import _common as C


def _direction(earlier: float, later: float) -> str:
    if later > earlier:
        return "rising"
    if later < earlier:
        return "falling"
    return "flat"


def _t(name, value, observed, explanation, inputs=()):
    # value is a signed slope in [-1, 1]: (later - earlier) / max(1, earlier+later)
    return AnalyticsMetric(name=name, value=float(value), unit="index", observed=observed,
                           dimension="trend", explanation=explanation, inputs=tuple(inputs))


def _halves(events: Sequence) -> tuple[list, list]:
    n = len(events)
    mid = n // 2
    return list(events[:mid]), list(events[mid:])


def _count(events: Sequence, predicate) -> int:
    return sum(1 for e in events if predicate(e))


def _slope(earlier_count: int, later_count: int) -> float:
    total = earlier_count + later_count
    return C.rnd((later_count - earlier_count) / total) if total else 0.0


class TrendEngine:
    """Builds the ``trend`` analytics dimension (read-only, deterministic)."""

    engine_version = ANALYTICS_TREND_ENGINE_VERSION

    def compute(self, view: AnalyticsSourceView) -> list[AnalyticsMetric]:
        metrics: list[AnalyticsMetric] = []
        events = view.events()           # already deterministically ordered
        earlier, later = _halves(events)
        observed = len(events) >= 2

        def trend_for(name, predicate, inputs=("event",)):
            e_count = _count(earlier, predicate)
            l_count = _count(later, predicate)
            slope = _slope(e_count, l_count)
            metrics.append(_t(name, slope, observed,
                              f"{_direction(e_count, l_count)} "
                              f"(earlier={e_count}, later={l_count})", inputs))

        # --- temporal trend (overall event volume earlier vs later) ----------
        # split count: trivially earlier=len(earlier), later=len(later)
        metrics.append(_t("temporal_volume_trend", _slope(len(earlier), len(later)), observed,
                          f"{_direction(len(earlier), len(later))} overall event volume "
                          f"(earlier={len(earlier)}, later={len(later)})", ["event"]))

        # --- workflow trend (workflow lifecycle events) ----------------------
        trend_for("workflow_trend",
                  lambda e: e.category in ("case",) and e.event_type.endswith(
                      ("REVIEWED", "CLOSED", "ARCHIVED")))

        # --- review trend (review events) ------------------------------------
        trend_for("review_trend", lambda e: e.category == "review")

        # --- finding trend (finding events) ----------------------------------
        trend_for("finding_trend", lambda e: e.category == "finding")

        # --- knowledge trend (knowledge events) ------------------------------
        trend_for("knowledge_trend", lambda e: e.category == "knowledge")

        # --- operational trend (governance/validation activity) --------------
        trend_for("operational_trend",
                  lambda e: e.category in ("governance", "validation", "quality", "system"))

        return metrics
