"""Population analytics, trend, and quality analytics tests (V2-P5)."""

from __future__ import annotations

from backend.multi_case_intelligence.analytics.engine import AnalyticsEngine
from backend.multi_case_intelligence.quality.analyzer import QualityAnalyzer
from backend.multi_case_intelligence.schemas.base import ArtifactKind
from backend.multi_case_intelligence.schemas.intelligence import TrendDirection
from backend.multi_case_intelligence.trends.analyzer import TrendAnalyzer


# -- analytics ------------------------------------------------------------- #
def test_population_analytics_counts(sample_population):
    analytics = AnalyticsEngine().analyze_population(sample_population)
    assert analytics.block(ArtifactKind.CASE).count == 4
    assert analytics.block(ArtifactKind.REVIEW).count == 4
    assert analytics.block(ArtifactKind.FINDING).count == 4
    assert analytics.block(ArtifactKind.EVIDENCE).count == 4
    assert analytics.block(ArtifactKind.KNOWLEDGE).count == 2


def test_finding_distribution_and_frequency(sample_population):
    analytics = AnalyticsEngine().analyze_population(sample_population)
    block = analytics.block(ArtifactKind.FINDING)
    dist = block.distributions[0]
    counts = dict(dist.counts)
    assert counts == {"SZ": 1, "GPD": 1, "LPD": 1, "GRDA": 1}
    # Four equally-likely categories -> max normalized entropy (1.0).
    assert block.variability["category_entropy"] == 1.0
    assert block.coverage["has_evidence"] == 0.75  # 3 of 4
    assert block.coverage["has_interpretation"] == 0.5  # F1, F2


def test_confidence_aggregates_preserved(sample_population):
    analytics = AnalyticsEngine().analyze_population(sample_population)
    conf = analytics.block(ArtifactKind.FINDING).confidence
    assert conf["max"] == 0.9
    assert conf["min"] == 0.3
    assert conf["n"] == 4.0


def test_analytics_is_deterministic(sample_population):
    engine = AnalyticsEngine()
    a1 = engine.analyze_population(sample_population)
    a2 = engine.analyze_population(sample_population)
    assert a1.id == a2.id
    assert a1.compute_hash() == a2.compute_hash()


# -- trends ---------------------------------------------------------------- #
def test_trend_buckets_are_ordered_and_deterministic(sample_population):
    analyzer = TrendAnalyzer()
    t1 = analyzer.analyze(sample_population)
    t2 = analyzer.analyze(sample_population)
    assert t1.compute_hash() == t2.compute_hash()
    series = {s.metric: s for s in t1.series}
    assert "finding_count" in series
    buckets = [p.bucket for p in series["finding_count"].points]
    assert buckets == ["1", "2", "3"]  # sorted ordinal buckets


def test_trend_direction_for_finding_count(sample_population):
    # bucket1 has F1,F2 (2 findings); bucket2 has F3 (1); bucket3 has F4 (1).
    analyzer = TrendAnalyzer()
    trend = analyzer.analyze(sample_population)
    series = {s.metric: s for s in trend.series}["finding_count"]
    values = [p.value for p in series.points]
    assert values == [2.0, 1.0, 1.0]
    assert series.direction == TrendDirection.DECREASING
    assert series.delta == -1.0


# -- quality --------------------------------------------------------------- #
def test_quality_metrics(sample_population):
    report = QualityAnalyzer().analyze(sample_population)
    metrics = {m.name: m for m in report.metrics}
    # 2 of 4 reviews finalized (R1 signed off, R2 completed).
    assert metrics["review_quality"].value == 0.5  # R1, R2 finalized of 4
    # evidence completeness: F1,F2,F4 have evidence (3/4).
    assert metrics["evidence_completeness"].value == 0.75
    # interpretation completeness: F1,F2 (2/4).
    assert metrics["interpretation_completeness"].value == 0.5
    # knowledge coverage: SZ,GPD covered of {SZ,GPD,LPD,GRDA} -> 0.5.
    assert metrics["knowledge_coverage"].value == 0.5
    # referential integrity intact -> 1.0.
    assert metrics["referential_integrity"].value == 1.0


def test_quality_metric_ratios_are_in_range(sample_population):
    report = QualityAnalyzer().analyze(sample_population)
    for m in report.metrics:
        assert 0.0 <= m.value <= 1.0
        assert 0 <= m.numerator <= m.denominator or m.denominator == 0
