"""Window schemas: deterministic fixed-length analysis windows.

``WindowSet`` holds the windowed signal as a single 3-D ``float64`` array
``(n_windows, n_channels, window_samples)`` plus per-window
:class:`WindowMetadata`. Windowing is the unit of analysis downstream models will
consume; it is fully deterministic and each window is traceable to its source
samples/time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from preprocessing._canonical import array_fingerprint


@dataclass(frozen=True, slots=True)
class WindowMetadata:
    """Provenance for a single window."""

    index: int
    start_sample: int
    end_sample: int  # exclusive
    start_time_s: float
    end_time_s: float
    padded_samples: int = 0  # number of zero-padded samples (BoundaryPolicy.PAD)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "start_sample": self.start_sample,
            "end_sample": self.end_sample,
            "start_time_s": self.start_time_s,
            "end_time_s": self.end_time_s,
            "padded_samples": self.padded_samples,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WindowMetadata:
        return cls(
            index=int(data["index"]),
            start_sample=int(data["start_sample"]),
            end_sample=int(data["end_sample"]),
            start_time_s=float(data["start_time_s"]),
            end_time_s=float(data["end_time_s"]),
            padded_samples=int(data.get("padded_samples", 0)),
        )


@dataclass(frozen=True, eq=False)
class WindowSet:
    """A set of fixed-length windows derived from a (processed) recording.

    Attributes
    ----------
    data:
        ``float64`` array ``(n_windows, n_channels, window_samples)``.
    channel_names:
        Channel labels, one per axis-1 row.
    sampling_rate_hz:
        Sampling rate of the windowed signal.
    windows:
        Per-window metadata (length == ``n_windows``).
    """

    data: np.ndarray
    channel_names: tuple[str, ...]
    sampling_rate_hz: float
    windows: tuple[WindowMetadata, ...]
    units: str = "uV"
    record_id: str | None = None
    patient_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def n_windows(self) -> int:
        return self.data.shape[0]

    @property
    def n_channels(self) -> int:
        return self.data.shape[1] if self.data.ndim == 3 else 0

    @property
    def window_samples(self) -> int:
        return self.data.shape[2] if self.data.ndim == 3 else 0

    def fingerprint(self) -> str:
        return array_fingerprint(self.data)

    def metadata_dict(self) -> dict[str, Any]:
        return {
            "channel_names": list(self.channel_names),
            "sampling_rate_hz": self.sampling_rate_hz,
            "units": self.units,
            "n_windows": self.n_windows,
            "n_channels": self.n_channels,
            "window_samples": self.window_samples,
            "record_id": self.record_id,
            "patient_id": self.patient_id,
            "data_fingerprint": self.fingerprint(),
            "windows": [w.to_dict() for w in self.windows],
        }
