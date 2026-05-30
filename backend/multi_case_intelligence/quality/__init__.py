"""Quality analytics for the intelligence layer.

Analyzes review quality, finding quality, evidence/interpretation completeness,
knowledge coverage, and referential (registry) integrity across the population,
packaged as a versioned :class:`QualityReport`.
"""

from backend.multi_case_intelligence.quality.analyzer import QualityAnalyzer

__all__ = ["QualityAnalyzer"]
