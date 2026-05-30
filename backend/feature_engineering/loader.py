"""Load the processed-signal array of a P2 asset (read-only).

The feature layer reads the cleaned signal bytes produced by Productization P2 (via
the P2 ``ProcessedSignalStore``) and reconstructs the numeric array using the
``ProcessedEEGRecord``'s signal descriptor. It never writes to the processed store —
features are derived from, and traced back to, the immutable processed signal.
"""

from __future__ import annotations

import numpy as np

from ml.provenance import hash_array  # allowed: backend -> ml

from .version import FINGERPRINT_DECIMALS


class ProcessedSignalLoadError(RuntimeError):
    """Raised when the processed signal bytes cannot be reconstructed."""


def load_processed_signal(processed_store, processed_record) -> tuple[np.ndarray, float, tuple[str, ...]]:
    """Reconstruct ``(data[n_ch, n_samp], sfreq, ch_names)`` for a processed asset."""
    sig = processed_record.processed_signal
    n_ch, n_samp = int(sig.n_channels), int(sig.n_samples)
    try:
        raw = processed_store.read_bytes(processed_record.storage)
        arr = np.frombuffer(raw, dtype=np.float64)
    except (OSError, ValueError) as exc:
        raise ProcessedSignalLoadError(f"cannot read processed bytes: {exc}") from exc
    if arr.size != n_ch * n_samp:
        raise ProcessedSignalLoadError(
            f"processed byte count {arr.size} != n_channels*n_samples {n_ch * n_samp}")
    data = np.ascontiguousarray(arr.reshape(n_ch, n_samp))
    return data, float(sig.sampling_frequency), tuple(sig.channel_labels)


def feature_array_fingerprint(data: np.ndarray) -> str:
    """A stable content fingerprint of a (quantized) array (for cross-checks)."""
    return hash_array(np.round(np.ascontiguousarray(data, dtype=np.float64), FINGERPRINT_DECIMALS))
