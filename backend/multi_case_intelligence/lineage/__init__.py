"""Intelligence lineage system.

Tracks the provenance of every intelligence artifact back through the chain
Patient -> Case -> Review -> Finding -> Knowledge -> Cohort -> Analytics ->
Trend -> Report. Every artifact must be traceable to its source roots.
"""

from backend.multi_case_intelligence.lineage.tracker import IntelligenceLineageTracker

__all__ = ["IntelligenceLineageTracker"]
