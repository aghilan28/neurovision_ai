"""Shared builders for the V3-P5 / V3-P6 test suites.

Extends the V3-P3/P4 fixture (`build_v3b`) with derived operational analytics
(V3-P5) and explainable operational recommendations (V3-P6), all over the one
shared platform lineage tracker. Also builds the V3-P2 temporal analytics so the
analytics layer's temporal/duration inputs are exercised against a real artifact.
Not collected by pytest (no ``test_`` prefix).
"""

from __future__ import annotations

from dataclasses import dataclass

from _v3b_helpers import build_v3b, V3bFixture

from backend.temporal_intelligence import TemporalIntelligenceService
from backend.operational_analytics import OperationalAnalyticsService
from backend.operational_recommendations import OperationalRecommendationService


@dataclass
class V3cFixture:
    base: V3bFixture
    temporal: object                  # TemporalAnalytics artifact (V3-P2)
    analytics: OperationalAnalyticsService
    analytics_records: dict           # category -> AnalyticsRecord
    recommendations: OperationalRecommendationService
    recommendation_records: dict      # kind -> list[RecommendationRecord]


def build_v3c(n_cases: int = 2) -> V3cFixture:
    b = build_v3b(n_cases)
    tracker = b.base.cs.lineage       # single shared platform lineage tracker

    # --- V3-P2 temporal analytics (a real upstream artifact for analytics) ---
    ti = TemporalIntelligenceService(b.base.events, lineage_tracker=tracker)
    ti.load_events(b.base.all_events)
    temporal = ti.build_analytics(scope="operational")

    # --- V3-P5 operational analytics -----------------------------------------
    oa = OperationalAnalyticsService(lineage_tracker=tracker)
    oa.load_sources(events=b.base.all_events, workflows=list(b.workflow_records.values()),
                    graph_registry=b.graph.registry, temporal_analytics=temporal)
    analytics_records = oa.build_all()

    # --- V3-P6 operational recommendations -----------------------------------
    orr = OperationalRecommendationService(lineage_tracker=tracker)
    orr.load_intelligence(analytics=list(analytics_records.values()),
                          workflows=list(b.workflow_records.values()),
                          graph_registry=b.graph.registry)
    recommendation_records = orr.generate()

    return V3cFixture(base=b, temporal=temporal, analytics=oa,
                      analytics_records=analytics_records, recommendations=orr,
                      recommendation_records=recommendation_records)


def all_recommendations(fx: V3cFixture) -> list:
    out: list = []
    for recs in fx.recommendation_records.values():
        out.extend(recs)
    return out
