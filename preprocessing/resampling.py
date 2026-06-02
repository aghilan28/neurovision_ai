"""``preprocessing.resampling`` — deterministic, anti-aliased resampling.

Standardizes recordings to a common target sampling rate so downstream consumers
see a uniform time base. Uses SciPy polyphase resampling (``resample_poly``), whose
FIR prototype provides inherent anti-aliasing (no separate anti-alias filter is
needed, and none is hidden). The up/down ratio is derived exactly from the
rational approximation of ``target / original`` so the operation is deterministic.

Resampling is a single-module stage (it has no submodules); it lives at the package
root and is invoked by the pipeline like the other stages.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import numpy as np
from scipy import signal as sp_signal

#: Version of the resampling operation (recorded on lineage).
RESAMPLE_OP_VERSION = "1.0.0"

# Bound the denominator of the rational up/down ratio so the polyphase filter
# stays tractable while remaining an exact, deterministic approximation.
_MAX_RATIO_DENOMINATOR = 1000


class ResampleError(ValueError):
    """Raised when resampling parameters are invalid."""


def _ratio(target_hz: float, original_hz: float) -> tuple[int, int]:
    frac = Fraction(target_hz / original_hz).limit_denominator(_MAX_RATIO_DENOMINATOR)
    up, down = frac.numerator, frac.denominator
    if up <= 0 or down <= 0:
        raise ResampleError(f"degenerate resample ratio {up}/{down}")
    return up, down


def resample_signal(
    signals: np.ndarray,
    original_hz: float,
    target_hz: float,
    *,
    method: str = "polyphase",
) -> tuple[np.ndarray, dict[str, Any]]:
    """Resample ``signals`` (channels × samples) from ``original_hz`` to ``target_hz``.

    Returns ``(resampled, info)`` where ``info`` records the exact up/down ratio
    and effective rate used (for lineage). If the rates are equal the signal is
    returned unchanged. Anti-aliasing is inherent to the polyphase filter.
    """
    if method != "polyphase":
        raise ResampleError(f"unsupported resampling method {method!r}")
    if original_hz <= 0 or target_hz <= 0:
        raise ResampleError("sampling rates must be positive")

    arr = np.ascontiguousarray(np.asarray(signals, dtype=np.float64))

    if abs(original_hz - target_hz) < 1e-12:
        return arr, {
            "up": 1,
            "down": 1,
            "original_hz": original_hz,
            "target_hz": target_hz,
            "effective_hz": original_hz,
            "method": method,
            "anti_alias": True,
            "changed": False,
        }

    up, down = _ratio(target_hz, original_hz)
    resampled = (
        arr
        if arr.shape[-1] == 0
        else sp_signal.resample_poly(arr, up, down, axis=-1)
    )
    effective_hz = original_hz * up / down

    return np.ascontiguousarray(resampled, dtype=np.float64), {
        "up": up,
        "down": down,
        "original_hz": original_hz,
        "target_hz": target_hz,
        "effective_hz": effective_hz,
        "method": method,
        "anti_alias": True,
        "changed": True,
    }
