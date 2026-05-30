"""Guidance system.

Generates review/evidence/knowledge/investigation/risk guidance from a decision
context. Guidance is produced only from controlled, process-oriented templates
and is screened by the decision scope guard. It NEVER provides diagnosis,
treatment, clinical orders, or medication advice.
"""

from backend.decision_support.guidance.generator import GuidanceGenerator

__all__ = ["GuidanceGenerator"]
