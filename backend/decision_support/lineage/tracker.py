"""Decision lineage tracker.

Reuses the deterministic, transitive-root lineage tracker from the intelligence
layer. Kept as a distinct class so the decision subsystem owns its own provenance
graph instance (decision lineage is separate from intelligence lineage, though
the two connect through shared source/intelligence references).
"""

from __future__ import annotations

from backend.multi_case_intelligence.lineage.tracker import IntelligenceLineageTracker


class DecisionLineageTracker(IntelligenceLineageTracker):
    """Provenance graph for decision-support artifacts."""


__all__ = ["DecisionLineageTracker"]
