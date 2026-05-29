"""Discovery helpers: channels, sampling rates, and duration.

These functions derive higher-level descriptors from a decoded
:class:`~datasets.ingestion.edf_reader.EdfFileHeader`. They contain the only
channel-label-normalization and channel-type-classification logic in the data
layer, so that behaviour is defined in exactly one place (reused by metadata
extraction).
"""

from __future__ import annotations

import re

from datasets.ingestion.edf_reader import EDF_ANNOTATIONS_LABEL, EdfFileHeader
from datasets.schemas.channels import ChannelDescriptor, ReferenceInfo
from datasets.schemas.enums import ChannelType

# Canonical 10–20 (and common extended) EEG electrode names, uppercased.
_EEG_ELECTRODES = frozenset(
    {
        "FP1", "FP2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2",
        "F7", "F8", "T3", "T4", "T5", "T6", "FZ", "CZ", "PZ", "OZ",
        "A1", "A2", "T1", "T2", "FPZ",
        # Extended 10–10 names sometimes present
        "T7", "T8", "P7", "P8", "FC1", "FC2", "CP1", "CP2", "FC5", "FC6",
        "CP5", "CP6", "AF3", "AF4", "PO3", "PO4", "F9", "F10", "P9", "P10",
    }
)

# Reference-suffix tokens commonly appended to EEG labels (e.g. "FP1-REF").
_REFERENCE_SUFFIXES = ("-REF", "-LE", "-RE", "-AVG", "-A1", "-A2", "REF")

_LABEL_PREFIX_RE = re.compile(r"^(EEG|EOG|ECG|EKG|EMG)\s+", re.IGNORECASE)


def normalize_label(raw_label: str) -> str:
    """Normalize an EDF channel label to a canonical, comparable form.

    Strips a leading modality prefix (``"EEG FP1"`` -> ``"FP1"``) and a trailing
    reference suffix (``"FP1-REF"`` -> ``"FP1"``), then uppercases. The original
    label is always preserved separately on the descriptor for traceability.
    """
    label = raw_label.strip()
    label = _LABEL_PREFIX_RE.sub("", label).strip()
    upper = label.upper()
    for suffix in _REFERENCE_SUFFIXES:
        if suffix != "REF" and upper.endswith(suffix):
            upper = upper[: -len(suffix)]
            break
    return upper.strip()


def classify_channel(raw_label: str, normalized: str) -> ChannelType:
    """Classify a channel by its label into a coarse :class:`ChannelType`."""
    if raw_label.strip() == EDF_ANNOTATIONS_LABEL:
        return ChannelType.ANNOTATION
    upper_raw = raw_label.upper()
    if "ECG" in upper_raw or "EKG" in upper_raw:
        return ChannelType.ECG
    if "EOG" in upper_raw:
        return ChannelType.EOG
    if "EMG" in upper_raw:
        return ChannelType.EMG
    if normalized in _EEG_ELECTRODES or upper_raw.startswith("EEG"):
        return ChannelType.EEG
    if normalized in {"REF", "LE", "RE", "AVG"} or upper_raw.strip() in {"REF", "A1A2"}:
        return ChannelType.REFERENCE
    return ChannelType.OTHER


def _sampling_frequency(samples_per_record: int, record_duration: float) -> float:
    if record_duration <= 0:
        return 0.0
    return samples_per_record / record_duration


def discover_channels(header: EdfFileHeader) -> tuple[ChannelDescriptor, ...]:
    """Build canonical channel descriptors from a decoded header."""
    descriptors: list[ChannelDescriptor] = []
    for h in header.signal_headers:
        normalized = normalize_label(h.label)
        channel_type = classify_channel(h.label, normalized)
        label = EDF_ANNOTATIONS_LABEL if channel_type is ChannelType.ANNOTATION else normalized
        descriptors.append(
            ChannelDescriptor(
                label=label or h.label.strip(),
                raw_label=h.label.strip(),
                channel_type=channel_type,
                sampling_frequency_hz=_sampling_frequency(
                    h.samples_per_record, header.record_duration_seconds
                ),
                samples_per_record=h.samples_per_record,
                physical_dimension=h.physical_dimension,
                physical_min=h.physical_min,
                physical_max=h.physical_max,
                digital_min=h.digital_min,
                digital_max=h.digital_max,
                transducer=h.transducer,
                prefiltering=h.prefiltering,
            )
        )
    return tuple(descriptors)


def discover_sampling_rates(header: EdfFileHeader) -> dict[str, float]:
    """Map each *data* channel's label to its sampling frequency in Hz."""
    rates: dict[str, float] = {}
    for desc in discover_channels(header):
        if desc.channel_type is ChannelType.ANNOTATION:
            continue
        rates[desc.label] = desc.sampling_frequency_hz
    return rates


def discover_duration_seconds(header: EdfFileHeader) -> float:
    """Total recording duration in seconds (records * record duration)."""
    records = header.num_data_records if header.num_data_records >= 0 else 0
    return records * header.record_duration_seconds


def discover_reference(header: EdfFileHeader) -> ReferenceInfo:
    """Heuristically infer reference information from channel labels."""
    for h in header.signal_headers:
        upper = h.label.upper()
        if upper.endswith("-LE"):
            return ReferenceInfo(scheme="referential", reference_label="LE")
        if upper.endswith("-REF") or upper.endswith("REF"):
            return ReferenceInfo(scheme="referential", reference_label="REF")
        if upper.endswith("-AVG"):
            return ReferenceInfo(scheme="average", reference_label="AVG")
    return ReferenceInfo(scheme="unknown", reference_label=None)
