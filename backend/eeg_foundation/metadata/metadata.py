"""EEG metadata extraction / normalization (Productization P1).

Converts a raw parse result into the normalized, deterministic :class:`EEGMetadata`
(+ :class:`EEGChannelSet` + annotations) that is stored independently of the raw file.
Deterministic: a given file always yields identical metadata (no wall-clock, no
randomness; ``recording_start`` is read from the file, not the system clock).
"""

from __future__ import annotations

from ..version import EEG_METADATA_VERSION
from ..models.domain import EEGChannel, EEGChannelSet, EEGAnnotation, EEGMetadata
from ..ingestion.raw import RawEEG


def build_channel_set(raw: RawEEG) -> EEGChannelSet:
    channels = tuple(
        EEGChannel(label=c.label, index=i, sampling_frequency=c.sampling_frequency,
                   physical_dimension=c.physical_dimension, transducer=c.transducer, kind=c.kind)
        for i, c in enumerate(raw.channels))
    return EEGChannelSet(channels=channels)


def build_annotations(raw: RawEEG) -> tuple:
    return tuple(EEGAnnotation(onset_seconds=float(a.get("onset_seconds", 0.0)),
                               duration_seconds=float(a.get("duration_seconds", 0.0)),
                               description=str(a.get("description", "")))
                 for a in raw.annotations)


def normalize(raw: RawEEG, *, recording_id: str) -> tuple:
    """Return (EEGMetadata, EEGChannelSet, annotations) for a raw parse result."""
    channel_set = build_channel_set(raw)
    annotations = build_annotations(raw)
    signal = channel_set.signal_channels
    sfreqs = tuple(c.sampling_frequency for c in channel_set.channels)
    representative = max((c.sampling_frequency for c in signal), default=0.0)
    annot_types = tuple(sorted({a.description for a in annotations}))
    patient_identifier = raw.patient_field or None

    metadata = EEGMetadata(
        recording_id=recording_id, fmt=raw.fmt, n_channels=channel_set.count,
        n_signal_channels=len(signal), sampling_frequency=representative,
        sampling_frequencies=sfreqs, duration_seconds=raw.duration_seconds,
        n_samples=raw.n_samples, channel_set=channel_set, annotation_count=len(annotations),
        annotation_types=annot_types, recording_start=raw.recording_start,
        patient_identifier=patient_identifier, metadata_version=EEG_METADATA_VERSION)
    return metadata, channel_set, annotations
