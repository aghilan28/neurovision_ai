"""Distribution builders over a set of validated EEG records."""

from __future__ import annotations

from collections.abc import Sequence

from datasets.schemas.enums import ChannelType
from datasets.schemas.validated_record import ValidatedEegRecord
from evaluation.dataset_intelligence.schemas.common import (
    CategoryDistribution,
    NumericDistribution,
)
from evaluation.dataset_intelligence.statistics import category_counts, numeric_distribution


def _fmt_hz(hz: float) -> str:
    """Format a sampling rate as a stable category key (e.g. ``"256"`` / ``"256.5"``)."""
    if float(hz).is_integer():
        return str(int(hz))
    return repr(round(float(hz), 4))


def channel_signature(record: ValidatedEegRecord) -> str:
    """Deterministic signature of a record's *data* channel set (sorted labels)."""
    labels = sorted(
        c.label for c in record.metadata.channels if c.channel_type is not ChannelType.ANNOTATION
    )
    return "|".join(labels)


def duration_distribution(records: Sequence[ValidatedEegRecord], *, bins: int = 10) -> NumericDistribution:
    """Distribution of recording durations (seconds)."""
    return numeric_distribution(
        "duration_seconds", [r.metadata.duration_seconds for r in records], bins=bins
    )


def sampling_frequency_distribution(records: Sequence[ValidatedEegRecord]) -> CategoryDistribution:
    """Distribution of (representative) sampling rate per recording."""
    keys: list[str] = []
    for r in records:
        freqs = r.metadata.sampling_frequencies_hz
        if freqs:
            keys.append(_fmt_hz(freqs[0]))
        else:
            keys.append("none")
    return category_counts("sampling_frequency_hz", keys)


def channel_configuration_distribution(records: Sequence[ValidatedEegRecord]) -> CategoryDistribution:
    """Distribution of distinct data-channel configurations across recordings."""
    return category_counts("channel_configuration", [channel_signature(r) for r in records])


def annotation_count_distribution(records: Sequence[ValidatedEegRecord], *, bins: int = 10) -> NumericDistribution:
    """Distribution of annotation counts per recording."""
    return numeric_distribution(
        "annotations_per_recording", [len(r.metadata.annotations) for r in records], bins=bins
    )
