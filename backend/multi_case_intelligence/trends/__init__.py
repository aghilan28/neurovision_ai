"""Trend analysis for the intelligence layer.

Trends are computed over a *deterministic ordinal dimension* (the logical
``ordinal`` carried by cases) — never over a wall-clock timestamp — so the same
population always yields the same trend series.
"""

from backend.multi_case_intelligence.trends.analyzer import TrendAnalyzer

__all__ = ["TrendAnalyzer"]
