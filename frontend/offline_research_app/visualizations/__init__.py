"""``frontend/offline_research_app/visualizations`` — chart spec builders (V1-P8).

Deterministic builders that turn registered-artifact data into JSON chart specs
(bar / line / graph / layout / table). Specs are renderer-agnostic; the static HTML
report renders them as inline SVG. The eleven mandated visualizations are covered:
EEG metadata, channel layout, dataset statistics, class distribution, evaluation
metrics, calibration curves, coverage curves, risk profiles, benchmark comparisons,
lineage graphs, version graphs.
"""

from __future__ import annotations

from .charts import (
    eeg_metadata, channel_layout, dataset_statistics, class_distribution,
    evaluation_metrics, calibration_curve, coverage_curve, risk_profile,
    benchmark_comparison, lineage_graph, version_graph,
)

__all__ = [
    "eeg_metadata", "channel_layout", "dataset_statistics", "class_distribution",
    "evaluation_metrics", "calibration_curve", "coverage_curve", "risk_profile",
    "benchmark_comparison", "lineage_graph", "version_graph",
]
