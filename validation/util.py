"""Deterministic helpers for the validation layer (stdlib only).

Validation separates **deterministic** evidence (output fingerprints, success/failure
counts, metric values) from **informational** performance measures (wall-clock latency,
peak memory). Only the deterministic evidence enters a ``signature`` — timings never do,
so reproducibility holds (mirrors the V1 offline-inference convention).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from typing import Any, Sequence


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def fingerprint(obj: Any, *, n: int = 16) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()[:n]


def mean(values: Sequence[float]) -> float:
    vals = list(values)
    return float(sum(vals) / len(vals)) if vals else 0.0


def stdev(values: Sequence[float]) -> float:
    vals = list(values)
    if len(vals) < 2:
        return 0.0
    mu = mean(vals)
    return float(math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1)))


def population_stats(values: Sequence[float]) -> dict:
    vals = [float(v) for v in values]
    if not vals:
        return {"count": 0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    return {"count": len(vals), "mean": mean(vals), "std": stdev(vals),
            "min": min(vals), "max": max(vals)}


def l1_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """L1 distance between two equal-length vectors (0.0 on length mismatch guard)."""
    a, b = list(a), list(b)
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    return float(sum(abs(a[i] - b[i]) for i in range(n)))


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def peak_memory_kb() -> int:
    """Best-effort process peak memory in KiB.

    The value is informational only and is excluded from deterministic signatures.
    Linux/POSIX keeps the existing ``resource.getrusage`` behavior. Windows does not
    provide ``resource``, so use the process peak working set from the native API.
    """
    try:
        import resource

        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception:
        pass

    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ok = ctypes.windll.psapi.GetProcessMemoryInfo(
                handle, ctypes.byref(counters), counters.cb)
            if ok:
                return int(counters.PeakWorkingSetSize // 1024)
        except Exception:
            pass

    return 0


__all__ = ["canonical_json", "fingerprint", "mean", "stdev", "population_stats",
           "l1_distance", "clamp01", "peak_memory_kb"]
