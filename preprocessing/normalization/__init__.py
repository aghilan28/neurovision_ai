"""``preprocessing.normalization`` — explicit, versioned normalization.

Standardizes amplitude scale with **no hidden steps**. Two methods are supported:

* **z-score** — ``(x - mean) / std`` per channel.
* **robust** — ``(x - median) / IQR`` per channel (heavy-tail resistant).

Scope is either per-channel-over-the-recording (default; applied before windowing)
or per-channel-within-each-window (applied during windowing). Both are deterministic
and recorded in lineage.
"""

from __future__ import annotations

from preprocessing.normalization.normalize import (
    NORMALIZATION_OP_VERSION,
    normalize_per_channel,
    normalize_per_window,
)

__all__ = [
    "NORMALIZATION_OP_VERSION",
    "normalize_per_channel",
    "normalize_per_window",
]
