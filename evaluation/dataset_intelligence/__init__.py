"""``evaluation.dataset_intelligence`` — Dataset Intelligence Layer (V1-P3).

Produces a comprehensive, **reproducible** understanding of any EEG dataset
*without training a model*: profiling, statistical distributions, patient /
channel / recording analysis, class-distribution analysis, data-quality scoring,
and **leakage-risk** assessment — assembled into versioned, traceable reports.

Input contract
--------------
The analyzers consume the rich :class:`datasets.schemas.validated_record.ValidatedEegRecord`
produced by V1-P1 ingestion (it carries metadata, channels, sampling, annotations,
patient/session, validation, and quality). The intelligence layer **reads** these;
it never alters dataset contracts or preprocessing outputs.

Purpose: *understanding*, not modelling. The actual leakage-safe **splitting** and
metric machinery live in the Evaluation Foundation (V1-P4).
"""

from __future__ import annotations

from evaluation.dataset_intelligence._version import DATASET_INTELLIGENCE_VERSION
from evaluation.dataset_intelligence.channel_analysis import analyze_channels
from evaluation.dataset_intelligence.distributions import analyze_class_distribution
from evaluation.dataset_intelligence.leakage import analyze_leakage_risk
from evaluation.dataset_intelligence.patient_analysis import analyze_patients
from evaluation.dataset_intelligence.profiling import profile_dataset
from evaluation.dataset_intelligence.quality_analysis import analyze_quality
from evaluation.dataset_intelligence.recording_analysis import analyze_recordings
from evaluation.dataset_intelligence.reports import (
    generate_intelligence_report,
    save_report,
)

__all__ = [
    "DATASET_INTELLIGENCE_VERSION",
    "analyze_channels",
    "analyze_class_distribution",
    "analyze_leakage_risk",
    "analyze_patients",
    "analyze_quality",
    "analyze_recordings",
    "generate_intelligence_report",
    "profile_dataset",
    "save_report",
]
