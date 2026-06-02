"""Shared fixtures for the preprocessing test suite."""

from __future__ import annotations

import numpy as np
import pytest

from preprocessing.schemas.signal import RawRecording

# Canonical electrode set that satisfies the longitudinal bipolar "double banana".
DOUBLE_BANANA_CHANNELS = (
    "FP1", "F7", "T7", "P7", "O1", "FP2", "F8", "T8", "P8", "O2",
    "F3", "C3", "P3", "F4", "C4", "P4", "FZ", "CZ", "PZ",
)


def synth_signal(
    channel_names: tuple[str, ...],
    fs: float,
    duration_s: float,
    *,
    base_freq: float = 10.0,
    line_freq: float = 60.0,
    line_amp: float = 0.5,
    drift: float = 0.0,
) -> np.ndarray:
    """Deterministic synthetic multi-channel EEG (sinusoid + optional line noise/drift)."""
    n = int(round(fs * duration_s))
    t = np.arange(n, dtype=np.float64) / fs
    rows = []
    for i in range(len(channel_names)):
        x = np.sin(2 * np.pi * (base_freq + 0.1 * i) * t)
        if line_amp:
            x = x + line_amp * np.sin(2 * np.pi * line_freq * t)
        if drift:
            x = x + drift * t
        rows.append(x)
    return np.ascontiguousarray(np.stack(rows, axis=0), dtype=np.float64)


@pytest.fixture
def make_recording():
    """Factory creating a :class:`RawRecording` from synthetic signal."""

    def _make(
        channel_names: tuple[str, ...] = DOUBLE_BANANA_CHANNELS,
        fs: float = 256.0,
        duration_s: float = 30.0,
        **kwargs,
    ) -> RawRecording:
        sig = synth_signal(channel_names, fs, duration_s, **kwargs)
        return RawRecording.create(
            sig, channel_names, fs, record_id="rec-test", patient_id="patient-test",
            source_fingerprint="src-fp",
        )

    return _make
