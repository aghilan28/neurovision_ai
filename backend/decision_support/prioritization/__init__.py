"""Prioritization system.

Computes an explainable *review priority* for a decision context from weighted,
transparent factors (risk, interpretation/review incompleteness, finding load).
Prioritization orders reviewer attention; it is not clinical triage, diagnosis,
or treatment.
"""

from backend.decision_support.prioritization.prioritizer import Prioritizer

__all__ = ["Prioritizer"]
