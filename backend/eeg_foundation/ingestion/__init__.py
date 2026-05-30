"""``backend/eeg_foundation/ingestion`` — real EEG file ingestion (P1-B).

Reads actual EDF/EDF+/BDF/BDF+/FIF/SET files via MNE-Python (no mocks, no fake
parsers) and detects the precise format from the file's bytes. Ingestion never
raises: an undecodable file becomes a ``ParsedEEG`` with ``parse_ok=False`` so the
validation engine can report a structured finding.
"""

from __future__ import annotations

from .formats import (
    detect_format,
    detect_format_from_bytes,
    declared_format_from_extension,
)
from .reader import ParsedEEG, ParsedChannel, load_eeg

__all__ = [
    "detect_format",
    "detect_format_from_bytes",
    "declared_format_from_extension",
    "ParsedEEG",
    "ParsedChannel",
    "load_eeg",
]
