"""Decision reporting.

Rolls decision-support artifacts into human-readable, fully-referenced
:class:`DecisionReport` artifacts (decision-support, guidance, evidence, risk,
prioritization, validation). Reports carry only references and derived summaries.
"""

from backend.decision_support.reports.builder import DecisionReportBuilder

__all__ = ["DecisionReportBuilder"]
