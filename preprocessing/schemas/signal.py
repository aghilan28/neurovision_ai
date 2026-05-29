"""Signal contracts: the standardized input and processed output of the pipeline.

``RawRecording`` is the preprocessing layer's **own** input contract — a minimal,
self-describing in-memory EEG representation (a 2-D ``float64`` array plus channel
names and a sampling rate). The layer defines this itself rather than importing a
data-layer type, so it remains the dependency-graph leaf (Rule NR-8). The
``datasets`` layer (which sits above preprocessing and *may* import it) is free to
adapt its EDF reading into a ``RawRecording``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from preprocessing._canonical import array_fingerprint


class SignalShapeError(ValueError):
    """Raised when a signal array does not match its channel/axis contract."""


def _coerce_signals(signals: np.ndarray, channel_names: tuple[str, ...]) -> np.ndarray:
    arr = np.asarray(signals, dtype=np.float64)
    if arr.ndim != 2:
        raise SignalShapeError(f"signals must be 2-D (channels, samples); got {arr.ndim}-D")
    if arr.shape[0] != len(channel_names):
        raise SignalShapeError(
            f"signals has {arr.shape[0]} channels but {len(channel_names)} channel names"
        )
    return arr


@dataclass(frozen=True, eq=False)
class RawRecording:
    """Standardized EEG input: ``signals`` shaped ``(n_channels, n_samples)``.

    Attributes
    ----------
    signals:
        ``float64`` array, channels on axis 0, time on axis 1.
    channel_names:
        Canonical channel labels, one per row of ``signals``.
    sampling_rate_hz:
        Uniform sampling rate for all channels (Hz).
    units:
        Physical units of the samples (default ``"uV"``).
    record_id / patient_id / source_fingerprint:
        Optional provenance linking this recording to its data-layer origin.
    """

    signals: np.ndarray
    channel_names: tuple[str, ...]
    sampling_rate_hz: float
    units: str = "uV"
    record_id: str | None = None
    patient_id: str | None = None
    source_fingerprint: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        signals: np.ndarray,
        channel_names: tuple[str, ...],
        sampling_rate_hz: float,
        **kwargs: Any,
    ) -> RawRecording:
        """Construct after coercing to ``float64`` and validating the shape contract."""
        arr = _coerce_signals(signals, tuple(channel_names))
        return cls(
            signals=arr,
            channel_names=tuple(channel_names),
            sampling_rate_hz=float(sampling_rate_hz),
            **kwargs,
        )

    @property
    def n_channels(self) -> int:
        return self.signals.shape[0]

    @property
    def n_samples(self) -> int:
        return self.signals.shape[1]

    @property
    def duration_seconds(self) -> float:
        if self.sampling_rate_hz <= 0:
            return 0.0
        return self.n_samples / self.sampling_rate_hz

    def channel_index(self, name: str) -> int:
        return self.channel_names.index(name)

    def fingerprint(self) -> str:
        """Deterministic fingerprint of the signal content + key metadata."""
        return array_fingerprint(self.signals)

    def metadata_dict(self) -> dict[str, Any]:
        """JSON-serializable metadata (no array payload)."""
        return {
            "channel_names": list(self.channel_names),
            "sampling_rate_hz": self.sampling_rate_hz,
            "units": self.units,
            "n_channels": self.n_channels,
            "n_samples": self.n_samples,
            "duration_seconds": self.duration_seconds,
            "record_id": self.record_id,
            "patient_id": self.patient_id,
            "source_fingerprint": self.source_fingerprint,
            "signal_fingerprint": self.fingerprint(),
        }


@dataclass(frozen=True, eq=False)
class ProcessedSignal:
    """A signal after one or more transformations (pre-windowing).

    Mirrors :class:`RawRecording` but carries ``applied_stages`` for at-a-glance
    provenance. Full provenance lives in the pipeline lineage.
    """

    signals: np.ndarray
    channel_names: tuple[str, ...]
    sampling_rate_hz: float
    units: str = "uV"
    record_id: str | None = None
    patient_id: str | None = None
    applied_stages: tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        signals: np.ndarray,
        channel_names: tuple[str, ...],
        sampling_rate_hz: float,
        **kwargs: Any,
    ) -> ProcessedSignal:
        arr = _coerce_signals(signals, tuple(channel_names))
        return cls(
            signals=arr,
            channel_names=tuple(channel_names),
            sampling_rate_hz=float(sampling_rate_hz),
            **kwargs,
        )

    @property
    def n_channels(self) -> int:
        return self.signals.shape[0]

    @property
    def n_samples(self) -> int:
        return self.signals.shape[1]

    @property
    def duration_seconds(self) -> float:
        if self.sampling_rate_hz <= 0:
            return 0.0
        return self.n_samples / self.sampling_rate_hz

    def fingerprint(self) -> str:
        return array_fingerprint(self.signals)

    def with_signals(
        self, signals: np.ndarray, *, sampling_rate_hz: float | None = None, stage: str | None = None
    ) -> ProcessedSignal:
        """Return a new ProcessedSignal with replaced data (channels unchanged)."""
        return ProcessedSignal.create(
            signals,
            self.channel_names,
            sampling_rate_hz if sampling_rate_hz is not None else self.sampling_rate_hz,
            units=self.units,
            record_id=self.record_id,
            patient_id=self.patient_id,
            applied_stages=self.applied_stages + ((stage,) if stage else ()),
        )

    @classmethod
    def from_raw(cls, raw: RawRecording) -> ProcessedSignal:
        return cls.create(
            raw.signals,
            raw.channel_names,
            raw.sampling_rate_hz,
            units=raw.units,
            record_id=raw.record_id,
            patient_id=raw.patient_id,
        )
