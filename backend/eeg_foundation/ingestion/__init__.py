"""EEG ingestion (Productization P1)."""

from __future__ import annotations

from .raw import RawEEG, RawChannel
from .ingestion import load_eeg
from .formats import detect_format, detect_format_path

__all__ = ["RawEEG", "RawChannel", "load_eeg", "detect_format", "detect_format_path"]
