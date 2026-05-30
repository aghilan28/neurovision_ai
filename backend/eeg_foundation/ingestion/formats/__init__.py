"""Real, spec-compliant EEG format readers (Productization P1)."""

from __future__ import annotations

from .detect import detect_format, detect_format_path
from .edf import read_edf, is_edf_family
from .fif import read_fif, is_fif
from .setfile import read_set, is_set

__all__ = ["detect_format", "detect_format_path", "read_edf", "is_edf_family",
           "read_fif", "is_fif", "read_set", "is_set"]
