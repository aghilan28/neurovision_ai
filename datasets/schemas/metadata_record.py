"""Canonical metadata schema (Contract: *Metadata Record*).

The :class:`MetadataRecord` is the single canonical representation of everything
extracted from an EDF/EDF+ file. Downstream layers (datasets curation, and later
``ml``/``evaluation`` via the public surface) consume *this* — never the raw EDF
header — so the metadata contract is stable across the platform's lifetime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from datasets.schemas.channels import ChannelDescriptor, ReferenceInfo
from datasets.schemas.enums import ChannelType, FileFormat


@dataclass(frozen=True, slots=True)
class Annotation:
    """A single EDF+ annotation (Time-stamped Annotation List entry)."""

    onset_seconds: float
    duration_seconds: float | None
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "onset_seconds": self.onset_seconds,
            "duration_seconds": self.duration_seconds,
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Annotation:
        dur = data.get("duration_seconds")
        return cls(
            onset_seconds=float(data["onset_seconds"]),
            duration_seconds=None if dur is None else float(dur),
            text=data["text"],
        )


@dataclass(frozen=True, slots=True)
class TechnicalMetadata:
    """Low-level EDF header technical fields, preserved verbatim for traceability.

    These are the raw header strings/values (reserved field, header byte size,
    record structure). Keeping them lets any output be traced back to the exact
    bytes that produced it (AP-5/NR-11) and lets validation reason about integrity.
    """

    edf_version_field: str
    reserved_field: str
    header_bytes: int
    num_data_records: int
    record_duration_seconds: float
    num_signals: int
    raw_patient_field: str
    raw_recording_field: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "edf_version_field": self.edf_version_field,
            "reserved_field": self.reserved_field,
            "header_bytes": self.header_bytes,
            "num_data_records": self.num_data_records,
            "record_duration_seconds": self.record_duration_seconds,
            "num_signals": self.num_signals,
            "raw_patient_field": self.raw_patient_field,
            "raw_recording_field": self.raw_recording_field,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TechnicalMetadata:
        return cls(
            edf_version_field=data["edf_version_field"],
            reserved_field=data["reserved_field"],
            header_bytes=int(data["header_bytes"]),
            num_data_records=int(data["num_data_records"]),
            record_duration_seconds=float(data["record_duration_seconds"]),
            num_signals=int(data["num_signals"]),
            raw_patient_field=data["raw_patient_field"],
            raw_recording_field=data["raw_recording_field"],
        )


@dataclass(frozen=True, slots=True)
class MetadataRecord:
    """Canonical metadata extracted from one EEG file.

    Required identity fields (``file_id``, ``patient_id``, ``recording_id``) are
    deterministic and content-derived. ``dataset_id`` is optional until the record
    is assigned to a dataset. Dates/times are stored as the EDF header strings
    (no timezone assumptions) plus a normalized ISO date when parseable.
    """

    # --- identity ---------------------------------------------------------
    file_id: str
    patient_id: str
    recording_id: str
    file_format: FileFormat

    # --- recording descriptors -------------------------------------------
    start_date: str  # raw EDF "dd.mm.yy" (or EDF+ field)
    start_time: str  # raw EDF "hh.mm.ss"
    recording_date_iso: str | None  # normalized "YYYY-MM-DD" when parseable
    duration_seconds: float

    # --- channel descriptors ---------------------------------------------
    channels: tuple[ChannelDescriptor, ...]
    reference: ReferenceInfo

    technical: TechnicalMetadata

    dataset_id: str | None = None
    annotations: tuple[Annotation, ...] = ()
    extractor_version: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    # --- derived convenience views ---------------------------------------
    @property
    def channel_labels(self) -> tuple[str, ...]:
        return tuple(c.label for c in self.channels)

    @property
    def data_channels(self) -> tuple[ChannelDescriptor, ...]:
        """Channels excluding the EDF+ annotation channel."""
        return tuple(c for c in self.channels if c.channel_type is not ChannelType.ANNOTATION)

    @property
    def channel_count(self) -> int:
        return len(self.channels)

    @property
    def data_channel_count(self) -> int:
        return len(self.data_channels)

    @property
    def sampling_frequencies_hz(self) -> tuple[float, ...]:
        return tuple(c.sampling_frequency_hz for c in self.data_channels)

    @property
    def is_uniform_sampling(self) -> bool:
        freqs = set(self.sampling_frequencies_hz)
        return len(freqs) <= 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "patient_id": self.patient_id,
            "recording_id": self.recording_id,
            "dataset_id": self.dataset_id,
            "file_format": self.file_format.value,
            "start_date": self.start_date,
            "start_time": self.start_time,
            "recording_date_iso": self.recording_date_iso,
            "duration_seconds": self.duration_seconds,
            "channels": [c.to_dict() for c in self.channels],
            "reference": self.reference.to_dict(),
            "technical": self.technical.to_dict(),
            "annotations": [a.to_dict() for a in self.annotations],
            "extractor_version": self.extractor_version,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MetadataRecord:
        return cls(
            file_id=data["file_id"],
            patient_id=data["patient_id"],
            recording_id=data["recording_id"],
            dataset_id=data.get("dataset_id"),
            file_format=FileFormat(data["file_format"]),
            start_date=data["start_date"],
            start_time=data["start_time"],
            recording_date_iso=data.get("recording_date_iso"),
            duration_seconds=float(data["duration_seconds"]),
            channels=tuple(ChannelDescriptor.from_dict(c) for c in data.get("channels", [])),
            reference=ReferenceInfo.from_dict(data.get("reference", {})),
            technical=TechnicalMetadata.from_dict(data["technical"]),
            annotations=tuple(Annotation.from_dict(a) for a in data.get("annotations", [])),
            extractor_version=data.get("extractor_version", ""),
            extra=dict(data.get("extra", {})),
        )
