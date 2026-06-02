"""``evaluation.dataset_intelligence.distributions`` — distribution analyzers.

Builds the statistical distributions used across the intelligence reports:

* :mod:`~evaluation.dataset_intelligence.distributions.dataset_distributions` —
  duration, sampling-rate, channel-configuration, and annotation-count
  distributions over a record set.
* :mod:`~evaluation.dataset_intelligence.distributions.labels` — the deterministic
  annotation-text → canonical EEG-class mapping.
* :mod:`~evaluation.dataset_intelligence.distributions.class_distribution` — the
  class/label distribution analysis (analysis only; no balancing).
"""

from __future__ import annotations

from evaluation.dataset_intelligence.distributions.class_distribution import (
    analyze_class_distribution,
)
from evaluation.dataset_intelligence.distributions.dataset_distributions import (
    annotation_count_distribution,
    channel_configuration_distribution,
    duration_distribution,
    sampling_frequency_distribution,
)
from evaluation.dataset_intelligence.distributions.labels import (
    DEFAULT_LABEL_MAPPING,
    LabelMapping,
    map_annotation_text,
)

__all__ = [
    "DEFAULT_LABEL_MAPPING",
    "LabelMapping",
    "analyze_class_distribution",
    "annotation_count_distribution",
    "channel_configuration_distribution",
    "duration_distribution",
    "map_annotation_text",
    "sampling_frequency_distribution",
]
