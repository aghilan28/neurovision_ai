"""``preprocessing.windowing`` — deterministic fixed-length window generation.

Splits a (processed) recording into fixed-length, optionally-overlapping windows.
Generation is fully deterministic: window count and boundaries are an exact
function of signal length, sampling rate, window length, overlap, and boundary
policy. Each window records its source samples/time for traceability.
"""

from __future__ import annotations

from preprocessing.windowing.window import (
    WINDOW_OP_VERSION,
    WindowingError,
    generate_windows,
    plan_windows,
)

__all__ = [
    "WINDOW_OP_VERSION",
    "WindowingError",
    "generate_windows",
    "plan_windows",
]
