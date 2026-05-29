"""Determinism helpers for the ML layer (AP-3 / AP-6 / NR-9 / NR-10).

All randomness in the ML layer flows through an explicitly seeded NumPy
``Generator``. There is no global, implicit, or wall-clock-derived randomness on
any reproducible path. Two runs with the same seeds produce identical results.
"""

from __future__ import annotations

import numpy as np


def make_rng(seed: int) -> np.random.Generator:
    """Return a fresh, explicitly-seeded NumPy generator.

    Using ``default_rng`` (PCG64) with an integer seed makes the entire random
    stream a pure function of the seed.
    """
    return np.random.default_rng(int(seed))


def derive_seed(*parts: object, base: int = 0) -> int:
    """Derive a stable child seed from arbitrary content + an optional base.

    Deterministic: identical inputs always yield the same seed. Used to give each
    sub-component (feature extractor, head init, fold) an independent but
    reproducible stream.
    """
    import hashlib

    h = hashlib.sha256()
    h.update(str(base).encode("utf-8"))
    for p in parts:
        h.update(b"\x00")
        h.update(repr(p).encode("utf-8"))
    # 63-bit non-negative integer seed
    return int.from_bytes(h.digest()[:8], "big") & 0x7FFFFFFFFFFFFFFF
