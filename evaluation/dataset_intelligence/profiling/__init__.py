"""``evaluation.dataset_intelligence.profiling`` — dataset profiling.

Produces a reproducible, versioned :class:`~evaluation.dataset_intelligence.schemas.reports.DatasetProfile`
(size, patient/recording/session counts, duration statistics, sampling/channel
configurations, annotation coverage, dataset versions).
"""

from __future__ import annotations

from evaluation.dataset_intelligence.profiling.profiler import profile_dataset

__all__ = ["profile_dataset"]
