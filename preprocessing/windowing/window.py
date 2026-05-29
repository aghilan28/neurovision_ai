"""Deterministic window generation."""

from __future__ import annotations

import numpy as np

from preprocessing.schemas.config import WindowConfig
from preprocessing.schemas.enums import BoundaryPolicy
from preprocessing.schemas.windows import WindowMetadata, WindowSet

#: Version of the windowing operation (recorded on lineage).
WINDOW_OP_VERSION = "1.0.0"


class WindowingError(ValueError):
    """Raised on invalid windowing parameters."""


def _window_samples(window_seconds: float, fs: float) -> int:
    n = int(round(window_seconds * fs))
    if n < 1:
        raise WindowingError(
            f"window of {window_seconds}s at {fs}Hz yields < 1 sample"
        )
    return n


def _step_samples(window_samples: int, overlap: float) -> int:
    if not (0.0 <= overlap < 1.0):
        raise WindowingError(f"overlap must be in [0, 1), got {overlap}")
    step = int(round(window_samples * (1.0 - overlap)))
    return max(1, step)


def plan_windows(
    n_samples: int, fs: float, config: WindowConfig
) -> list[tuple[int, int, int]]:
    """Return the deterministic window plan as ``(start, end, padded_samples)`` tuples.

    ``end`` is exclusive. With :class:`BoundaryPolicy.DROP` only full windows are
    produced; with ``PAD`` a trailing partial window is included and zero-padded.
    """
    window_samples = _window_samples(config.window_seconds, fs)
    step = _step_samples(window_samples, config.overlap)
    plan: list[tuple[int, int, int]] = []

    if n_samples < window_samples:
        if config.boundary_policy is BoundaryPolicy.PAD and n_samples > 0:
            plan.append((0, n_samples, window_samples - n_samples))
        return plan

    start = 0
    last_full_start = n_samples - window_samples
    while start <= last_full_start:
        plan.append((start, start + window_samples, 0))
        start += step

    if config.boundary_policy is BoundaryPolicy.PAD:
        covered_end = plan[-1][1] if plan else 0
        if covered_end < n_samples:
            tail_start = plan[-1][0] + step if plan else 0
            if tail_start < n_samples:
                real = n_samples - tail_start
                plan.append((tail_start, n_samples, window_samples - real))
    return plan


def generate_windows(
    signals: np.ndarray,
    channel_names: tuple[str, ...],
    fs: float,
    config: WindowConfig,
    *,
    units: str = "uV",
    record_id: str | None = None,
    patient_id: str | None = None,
) -> WindowSet:
    """Generate a :class:`WindowSet` from a 2-D ``(channels, samples)`` signal."""
    arr = np.ascontiguousarray(np.asarray(signals, dtype=np.float64))
    if arr.ndim != 2:
        raise WindowingError(f"signals must be 2-D (channels, samples); got {arr.ndim}-D")
    n_channels, n_samples = arr.shape
    window_samples = _window_samples(config.window_seconds, fs)

    plan = plan_windows(n_samples, fs, config)

    if not plan:
        data: np.ndarray = np.zeros((0, n_channels, window_samples), dtype=np.float64)
        return WindowSet(
            data=data,
            channel_names=tuple(channel_names),
            sampling_rate_hz=fs,
            windows=(),
            units=units,
            record_id=record_id,
            patient_id=patient_id,
        )

    blocks: list[np.ndarray] = []
    metas: list[WindowMetadata] = []
    for idx, (start, end, padded) in enumerate(plan):
        segment = arr[:, start:end]
        if padded > 0:
            segment = np.pad(segment, ((0, 0), (0, padded)), mode="constant")
        blocks.append(segment)
        metas.append(
            WindowMetadata(
                index=idx,
                start_sample=start,
                end_sample=end,
                start_time_s=start / fs,
                end_time_s=end / fs,
                padded_samples=padded,
            )
        )

    data = np.ascontiguousarray(np.stack(blocks, axis=0), dtype=np.float64)
    return WindowSet(
        data=data,
        channel_names=tuple(channel_names),
        sampling_rate_hz=fs,
        windows=tuple(metas),
        units=units,
        record_id=record_id,
        patient_id=patient_id,
    )
