"""``evaluation.dataset_intelligence.reports`` — report assembly & persistence.

Assembles the per-area analyses into the comprehensive, versioned, reproducible
:class:`~evaluation.dataset_intelligence.schemas.reports.DatasetIntelligenceReport`,
and persists any report as canonical JSON (stable bytes for reproducibility).
"""

from __future__ import annotations

from evaluation.dataset_intelligence.reports.generator import (
    generate_intelligence_report,
    save_report,
    summary_of,
)

__all__ = ["generate_intelligence_report", "save_report", "summary_of"]
