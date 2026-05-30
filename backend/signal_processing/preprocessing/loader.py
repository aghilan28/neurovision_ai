"""Load the raw signal array of a P1 EEG asset + deterministic signal serialization.

The Signal Processing layer reads the *immutable* raw EEG bytes stored by
Productization P1 (via the P1 store), decodes them with MNE into a numeric array,
and never writes back to the raw store. It also provides deterministic fingerprints
(content ids) and a canonical byte serialization for persisting the processed
(clean) signal.
"""

from __future__ import annotations

import warnings

import numpy as np

from ml.provenance import content_id, hash_array  # allowed: backend -> ml

from ..version import FINGERPRINT_DECIMALS

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import mne  # type: ignore

    mne.set_log_level("ERROR")

_READERS = {
    "EDF": lambda p: mne.io.read_raw_edf(p, preload=True, verbose="ERROR"),
    "BDF": lambda p: mne.io.read_raw_bdf(p, preload=True, verbose="ERROR"),
    "FIF": lambda p: mne.io.read_raw_fif(p, preload=True, verbose="ERROR"),
    "SET": lambda p: mne.io.read_raw_eeglab(p, preload=True, verbose="ERROR"),
}


class RawSignalLoadError(RuntimeError):
    """Raised when the raw EEG bytes cannot be decoded into a signal array."""


def load_raw_signal(path: str, format_family: str) -> tuple[np.ndarray, float, tuple[str, ...]]:
    """Decode the raw EEG at ``path`` into ``(data[n_ch, n_samp], sfreq, ch_names)``.

    ``format_family`` is one of EDF/BDF/FIF/SET (``EEGFormat.family``). Raises
    ``RawSignalLoadError`` if the bytes cannot be decoded (e.g. a quarantined file).
    """
    reader = _READERS.get(format_family)
    if reader is None:
        raise RawSignalLoadError(f"no reader for format family {format_family!r}")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw = reader(path)
            data = np.ascontiguousarray(raw.get_data(), dtype=np.float64)
            sfreq = float(raw.info["sfreq"])
            ch_names = tuple(str(c) for c in raw.ch_names)
        return data, sfreq, ch_names
    except Exception as exc:  # decode failure -> typed error (service decides)
        raise RawSignalLoadError(f"{type(exc).__name__}: {exc}") from exc


def quantize(data: np.ndarray) -> np.ndarray:
    """Round to a fixed number of decimals so fingerprints are stable (NR-10)."""
    return np.round(np.ascontiguousarray(data, dtype=np.float64), FINGERPRINT_DECIMALS)


def array_fingerprint(data: np.ndarray) -> str:
    """A stable content fingerprint of a (quantized) signal array."""
    return hash_array(quantize(data))


def signal_fingerprint(data: np.ndarray, sfreq: float, channel_labels: tuple[str, ...]) -> str:
    """A content id for a signal = function of its samples + rate + channel labels."""
    return content_id("signal", {
        "array": array_fingerprint(data), "shape": list(data.shape),
        "sfreq": round(float(sfreq), 6), "channels": list(channel_labels)})


def serialize_signal(data: np.ndarray) -> bytes:
    """Deterministic byte serialization of a signal (quantized, C-order float64)."""
    return quantize(data).tobytes(order="C")
