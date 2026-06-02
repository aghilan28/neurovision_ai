"""The intermediate raw-parse result produced by a format reader (Productization P1).

A :class:`RawEEG` is the neutral, format-agnostic structure every reader returns. It
holds exactly what was read from the real file (header fields, channel layout,
annotations, structural sizes). Readers never raise on malformed content — they return
``RawEEG(ok=False, error=...)`` so the validation engine can turn problems into
*structured findings* rather than exceptions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class RawChannel:
    label: str
    sampling_frequency: float
    physical_dimension: str = ""
    transducer: str = ""
    kind: str = "eeg"            # eeg | annotation

    def to_dict(self) -> dict:
        return {"label": self.label, "sampling_frequency": self.sampling_frequency,
                "physical_dimension": self.physical_dimension, "transducer": self.transducer,
                "kind": self.kind}


@dataclass(frozen=True)
class RawEEG:
    ok: bool
    fmt: str
    subtype: str = ""
    channels: tuple = ()                       # tuple[RawChannel]
    n_samples: int = 0                         # representative samples per signal channel
    duration_seconds: float = 0.0
    recording_start: Optional[str] = None
    patient_field: str = ""
    recording_field: str = ""
    annotations: tuple = ()                    # tuple[dict] {onset,duration,description}
    file_size_bytes: int = 0
    expected_data_bytes: Optional[int] = None
    actual_data_bytes: Optional[int] = None
    extra: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def n_channels(self) -> int:
        return len(self.channels)

    @property
    def signal_channels(self) -> tuple:
        return tuple(c for c in self.channels if c.kind != "annotation")

    def to_dict(self) -> dict:
        return {"ok": self.ok, "format": self.fmt, "subtype": self.subtype,
                "n_channels": self.n_channels, "channels": [c.to_dict() for c in self.channels],
                "n_samples": self.n_samples, "duration_seconds": self.duration_seconds,
                "recording_start": self.recording_start, "patient_field": self.patient_field,
                "recording_field": self.recording_field,
                "annotations": [dict(a) for a in self.annotations],
                "file_size_bytes": self.file_size_bytes,
                "expected_data_bytes": self.expected_data_bytes,
                "actual_data_bytes": self.actual_data_bytes, "error": self.error}
