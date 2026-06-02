"""Schemas (value objects + report contracts) for the Dataset Intelligence Layer.

All dataclasses are frozen and round-trip through deterministic ``to_dict`` /
``from_dict`` so every report is serializable, hashable, versioned, and
reproducible (AP-6, NR-10).
"""

from __future__ import annotations

from evaluation.dataset_intelligence.schemas.common import (
    CategoryDistribution,
    Finding,
    NumericDistribution,
    Provenance,
    Severity,
    SummaryStats,
)
from evaluation.dataset_intelligence.schemas.enums import EegClass, classify_family
from evaluation.dataset_intelligence.schemas.reports import (
    ChannelAnalysisReport,
    ChannelInventoryEntry,
    ClassDistributionReport,
    DatasetIntelligenceReport,
    DatasetProfile,
    LeakageRiskReport,
    PatientAnalysisReport,
    QualityAnalysisReport,
    RecordingAnalysisReport,
)

__all__ = [
    "CategoryDistribution",
    "ChannelAnalysisReport",
    "ChannelInventoryEntry",
    "ClassDistributionReport",
    "DatasetIntelligenceReport",
    "DatasetProfile",
    "EegClass",
    "Finding",
    "LeakageRiskReport",
    "NumericDistribution",
    "PatientAnalysisReport",
    "Provenance",
    "QualityAnalysisReport",
    "RecordingAnalysisReport",
    "Severity",
    "SummaryStats",
    "classify_family",
]
