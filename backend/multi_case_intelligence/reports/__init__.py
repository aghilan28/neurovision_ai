"""Intelligence reporting.

Rolls cohorts, analytics, trends, quality and validation results into
human-readable, fully-referenced :class:`IntelligenceReport` artifacts. Reports
contain only references and derived summaries — never source records.
"""

from backend.multi_case_intelligence.reports.builder import ReportBuilder

__all__ = ["ReportBuilder"]
