"""EEG ingestion dispatch (Productization P1).

``load_eeg(path)`` detects the container format from the real bytes and delegates to
the matching spec-compliant reader. It always returns a :class:`RawEEG` (never raises):
unsupported or unreadable inputs yield ``RawEEG(ok=False, error=...)`` so the
validation engine can convert them into structured findings.
"""

from __future__ import annotations

import os

from ..models.domain import EEGFormat
from .raw import RawEEG
from .formats import detect_format, read_edf, read_fif, read_set


def load_eeg(path: str) -> RawEEG:
    """Load a real EEG file by detecting its format and parsing the real bytes."""
    if not os.path.exists(path):
        return RawEEG(ok=False, fmt="UNKNOWN", error=f"file not found: {path}")
    if not os.path.isfile(path):
        return RawEEG(ok=False, fmt="UNKNOWN", error=f"not a regular file: {path}")
    try:
        with open(path, "rb") as fh:
            head = fh.read(256)
    except OSError as exc:
        return RawEEG(ok=False, fmt="UNKNOWN", error=f"OS error: {exc}",
                      file_size_bytes=_safe_size(path))

    fmt = detect_format(head)
    if fmt in (EEGFormat.EDF, EEGFormat.BDF):
        return read_edf(path)
    if fmt == EEGFormat.FIF:
        return read_fif(path)
    if fmt == EEGFormat.SET:
        return read_set(path)
    return RawEEG(ok=False, fmt="UNKNOWN", file_size_bytes=_safe_size(path),
                  error="unsupported or unrecognized EEG format "
                        "(supported: EDF, EDF+, BDF, BDF+, FIF, SET)")


def _safe_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0
