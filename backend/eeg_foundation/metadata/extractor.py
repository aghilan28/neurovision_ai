"""Deterministic EEG metadata extraction (P1-D).

Turns an ingestion result (``ParsedEEG``) into a normalized, deterministic
``EEGMetadata`` record that is stored *independently* of the raw signal bytes. The
metadata is a pure function of the parsed facts, so re-extracting from the same file
always yields the same ``EEGMetadata`` (and the same ``recording_id`` and
signature).

The ``recording_id`` is content-addressed (``recording+{hash16}``) from the file's
content + acquisition parameters — never from its filename — so the same recording
is identified consistently wherever it is stored.
"""

from __future__ import annotations

from ml.provenance import content_id  # allowed: backend -> ml

from ..ingestion.reader import ParsedEEG
from ..models.domain import EEGChannelType, EEGMetadata, EEGFormat


def _channel_layout(parsed: ParsedEEG) -> dict:
    hist: dict[str, int] = {}
    for c in parsed.channels:
        t = c.channel_type.value if isinstance(c.channel_type, EEGChannelType) else str(c.channel_type)
        hist[t] = hist.get(t, 0) + 1
    return dict(sorted(hist.items()))


def _annotation_types(parsed: ParsedEEG) -> tuple[str, ...]:
    return tuple(sorted({desc for _, _, desc in parsed.annotations}))


def compute_recording_id(parsed: ParsedEEG) -> str:
    """A deterministic, content-addressed recording id (independent of filename)."""
    fmt = parsed.detected_format.value if parsed.detected_format else "unknown"
    payload = {
        "checksum_sha256": parsed.checksum_sha256,
        "format": fmt,
        "n_channels": parsed.n_channels,
        "sampling_frequency": round(parsed.sampling_frequency, 6),
        "n_samples": parsed.n_samples,
        "channel_labels": [c.label for c in parsed.channels],
    }
    return content_id("recording", payload)


def extract_metadata(parsed: ParsedEEG) -> EEGMetadata:
    """Build the normalized ``EEGMetadata`` for a parsed EEG file.

    Requires a recognized format (``parsed.detected_format`` is not None); the
    service only extracts metadata once the format is known (unsupported/unreadable
    files are rejected before this point).
    """
    if parsed.detected_format is None:
        raise ValueError("cannot extract metadata: unrecognized EEG format")
    fmt: EEGFormat = parsed.detected_format
    return EEGMetadata(
        recording_id=compute_recording_id(parsed),
        eeg_format=fmt,
        duration_seconds=parsed.duration_seconds,
        sampling_frequency=parsed.sampling_frequency,
        n_channels=parsed.n_channels,
        n_samples=parsed.n_samples,
        channel_labels=tuple(c.label for c in parsed.channels),
        channel_layout=_channel_layout(parsed),
        n_annotations=len(parsed.annotations),
        annotation_types=_annotation_types(parsed),
        patient_identifier=parsed.patient_identifier,
        acquisition_date=parsed.recording_start_time,
        highpass_hz=parsed.highpass_hz,
        lowpass_hz=parsed.lowpass_hz,
        source_metadata=dict(parsed.source_metadata),
    )
