"""Deterministic temporal analytics (V3-P2).

Computes timing metrics from the operational timeline. Because the platform
forbids wall-clock, a "duration" is the number of ordered **logical steps** (event
positions) between a start event type and an end event type for a subject — a
reproducible interval. Metrics are computed per subject and reported as the
deterministic mean over the subjects where both endpoints were observed.
"""

from __future__ import annotations

from typing import Optional, Sequence

from ..identity import mint_analytics
from ..models.domain import DurationMetric, TemporalAnalytics
from ..timelines import EventSourceView

# (metric name, start event type, end event type, scope kind)
_DURATION_SPECS = [
    ("case_lifecycle_steps", "CASE_CREATED", "CASE_REVIEWED", "case"),
    ("review_duration_steps", "REVIEW_STARTED", "REVIEW_COMPLETED", "review"),
    ("finding_resolution_steps", "FINDING_CREATED", "FINDING_CONFIRMED", "finding"),
    ("decision_latency_steps", "DECISION_CONTEXT_BUILT", "DECISION_GENERATED", "decision"),
]


def _span(events_for_subject: Sequence, start_type: str, end_type: str) -> Optional[int]:
    """Logical-step span between the first start_type and the next end_type."""
    start_idx = None
    for i, e in enumerate(events_for_subject):
        if start_idx is None and e.event_type == start_type:
            start_idx = i
        elif start_idx is not None and e.event_type == end_type:
            return i - start_idx
    return None


def _mean_int(values: Sequence[int]) -> int:
    return round(sum(values) / len(values)) if values else -1


class TemporalAnalyticsEngine:
    """Builds :class:`TemporalAnalytics` from an event-source view (read-only)."""

    def build(self, view: EventSourceView, *, scope: str = "operational") -> TemporalAnalytics:
        # event-type counts across the whole population
        counts: dict = {}
        for e in view.all():
            counts[e.event_type] = counts.get(e.event_type, 0) + 1

        metrics: list[DurationMetric] = []
        source_ids = view.source_ids()
        for name, start_type, end_type, _kind in _DURATION_SPECS:
            spans = []
            for sid in source_ids:
                span = _span(view.for_source(sid), start_type, end_type)
                if span is not None:
                    spans.append(span)
            observed = bool(spans)
            metrics.append(DurationMetric(
                name=name, from_event_type=start_type, to_event_type=end_type,
                steps=_mean_int(spans) if observed else -1, observed=observed,
                detail=f"mean logical steps over {len(spans)} subject(s)"))

        # knowledge/operational timing: total knowledge updates + total events
        n_knowledge = sum(v for k, v in counts.items() if k.startswith("KNOWLEDGE_"))
        metrics.append(DurationMetric(
            name="knowledge_update_count", from_event_type="KNOWLEDGE_*", to_event_type="-",
            steps=n_knowledge if n_knowledge > 0 else -1,
            observed=n_knowledge > 0,
            detail="count of knowledge events (operational timing proxy)"))
        n_total = len(view.all())
        metrics.append(DurationMetric(
            name="operational_event_total", from_event_type="*", to_event_type="-",
            steps=n_total if n_total > 0 else -1, observed=n_total > 0,
            detail="total operational events on the timeline"))

        ident = mint_analytics(scope)
        return TemporalAnalytics(analytics_id=ident.id, scope=scope, metrics=tuple(metrics),
                                 counts=dict(sorted(counts.items())))
