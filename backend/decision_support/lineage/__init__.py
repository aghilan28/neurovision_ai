"""Decision lineage system.

Tracks the provenance of every decision-support artifact back through the chain
Patient -> Case -> Review -> Finding -> Interpretation -> Knowledge -> Evidence
-> DecisionContext -> Guidance/Prioritization. Every recommendation is fully
traceable. Built on the shared lineage mechanism from the intelligence layer.
"""

from backend.decision_support.lineage.tracker import DecisionLineageTracker

__all__ = ["DecisionLineageTracker"]
