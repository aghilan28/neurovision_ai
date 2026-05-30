"""``backend/signal_processing/preprocessing`` — raw-signal loading + cleaning pipeline.

Loads the immutable raw EEG bytes (P1 store) into a numeric array via MNE, provides
deterministic fingerprints/serialization, and orchestrates the filtering + removal
engines into one tracked raw -> clean pipeline.
"""

from __future__ import annotations

from .loader import (
    load_raw_signal, RawSignalLoadError, array_fingerprint, signal_fingerprint,
    serialize_signal, quantize,
)
from .pipeline import ProcessingPipeline

__all__ = [
    "load_raw_signal", "RawSignalLoadError", "array_fingerprint", "signal_fingerprint",
    "serialize_signal", "quantize", "ProcessingPipeline",
]
