"""Population analytics for the intelligence layer.

Generates statistics (counts, distributions, coverage, variability, frequency,
confidence) over case/review/finding/knowledge/evidence populations, packaged as
a versioned :class:`PopulationAnalytics` artifact.
"""

from backend.multi_case_intelligence.analytics.engine import AnalyticsEngine

__all__ = ["AnalyticsEngine"]
