"""Channel-level schema structures.

A :class:`ChannelDescriptor` captures everything the data foundation knows about
a single EDF signal channel after ingestion: its canonical and raw labels, its
technical EDF header fields, and its derived :class:`~datasets.schemas.enums.ChannelType`.
These descriptors are the basis for channel-consistency validation and for the
montage compatibility checks performed later (in ``preprocessing``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datasets.schemas.enums import ChannelType


@dataclass(frozen=True, slots=True)
class ChannelDescriptor:
    """Immutable description of one EDF signal channel.

    Fields mirror the EDF signal header (physical/digital ranges, dimension,
    transducer, prefiltering) plus a canonical label and a derived channel type.
    ``sampling_frequency_hz`` is computed as ``samples_per_record / record_duration``.
    """

    label: str
    """Canonical (normalized) channel label, e.g. ``"FP1"``."""

    raw_label: str
    """Original label exactly as stored in the EDF header."""

    channel_type: ChannelType
    sampling_frequency_hz: float
    samples_per_record: int
    physical_dimension: str
    physical_min: float
    physical_max: float
    digital_min: int
    digital_max: int
    transducer: str = ""
    prefiltering: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "raw_label": self.raw_label,
            "channel_type": self.channel_type.value,
            "sampling_frequency_hz": self.sampling_frequency_hz,
            "samples_per_record": self.samples_per_record,
            "physical_dimension": self.physical_dimension,
            "physical_min": self.physical_min,
            "physical_max": self.physical_max,
            "digital_min": self.digital_min,
            "digital_max": self.digital_max,
            "transducer": self.transducer,
            "prefiltering": self.prefiltering,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChannelDescriptor:
        return cls(
            label=data["label"],
            raw_label=data["raw_label"],
            channel_type=ChannelType(data["channel_type"]),
            sampling_frequency_hz=float(data["sampling_frequency_hz"]),
            samples_per_record=int(data["samples_per_record"]),
            physical_dimension=data["physical_dimension"],
            physical_min=float(data["physical_min"]),
            physical_max=float(data["physical_max"]),
            digital_min=int(data["digital_min"]),
            digital_max=int(data["digital_max"]),
            transducer=data.get("transducer", ""),
            prefiltering=data.get("prefiltering", ""),
        )


@dataclass(frozen=True, slots=True)
class ReferenceInfo:
    """Reference/derivation information for a recording.

    EDF does not encode a machine-readable reference scheme, so this is derived
    heuristically (e.g. from a ``-REF``/``-LE`` label suffix) and recorded for
    traceability and for downstream montage handling.
    """

    scheme: str = "unknown"
    """e.g. ``"referential"``, ``"average"``, ``"unknown"``."""

    reference_label: str | None = None
    """Named reference electrode if discoverable (e.g. ``"REF"``, ``"LE"``)."""

    def to_dict(self) -> dict[str, Any]:
        return {"scheme": self.scheme, "reference_label": self.reference_label}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReferenceInfo:
        return cls(
            scheme=data.get("scheme", "unknown"),
            reference_label=data.get("reference_label"),
        )
