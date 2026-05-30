"""EEG file-format detection by content (magic bytes), not by extension alone.

The platform must *understand* a real file: we classify it into the closed
``EEGFormat`` vocabulary by inspecting its bytes, and disambiguate the variants the
extension cannot (EDF vs EDF+, BDF vs BDF+ share an extension). The declared
extension is recorded separately so a mismatch can be surfaced by validation.

Detection rules (header inspection only — no signal decoding):
  * **BDF / BDF+** — byte 0 is 0xFF followed by ASCII ``BIOSEMI``. The 44-byte
    reserved field (offset 192) starting with ``BDF+C``/``BDF+D`` marks BDF+.
  * **EDF / EDF+** — the 8-byte version field is ASCII ``0`` (space-padded). The
    reserved field starting with ``EDF+C``/``EDF+D`` marks EDF+.
  * **FIF** — the first FIFF tag is ``FIFF_FILE_ID`` (kind 100), i.e. the file
    begins with the big-endian int32 ``100``.
  * **SET** — an EEGLAB container: a MATLAB v5 file (``MATLAB 5.0`` text header) or
    a MATLAB v7.3 file (HDF5 magic ``\\x89HDF``).
"""

from __future__ import annotations

import os
import struct
from typing import Optional

from ..models.domain import EEGFormat, SUPPORTED_EXTENSIONS

_HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"
_FIFF_FILE_ID = 100  # the kind of the first tag in every FIFF/.fif file


def declared_format_from_extension(path: str) -> Optional[EEGFormat]:
    """Return the format the file *claims* via its extension (``None`` if unknown)."""
    ext = os.path.splitext(path)[1].lower()
    return SUPPORTED_EXTENSIONS.get(ext)


def detect_format_from_bytes(header: bytes) -> Optional[EEGFormat]:
    """Classify a file from its leading bytes; ``None`` if not a supported format."""
    if not header:
        return None

    # --- BDF / BDF+ (BioSemi 24-bit) ---
    if header[:1] == b"\xff" and header[1:8] == b"BIOSEMI":
        reserved = header[192:236]
        if reserved[:5] in (b"BDF+C", b"BDF+D"):
            return EEGFormat.BDF_PLUS
        return EEGFormat.BDF

    # --- EDF / EDF+ (16-bit) ---
    # Version field is "0" left-justified, space padded to 8 bytes.
    if len(header) >= 256 and header[0:8].rstrip(b" ") == b"0":
        reserved = header[192:236]
        if reserved[:5] in (b"EDF+C", b"EDF+D"):
            return EEGFormat.EDF_PLUS
        return EEGFormat.EDF

    # --- FIF (FIFF) ---
    if len(header) >= 4:
        try:
            (kind,) = struct.unpack(">i", header[0:4])
            if kind == _FIFF_FILE_ID:
                return EEGFormat.FIF
        except struct.error:  # pragma: no cover - defensive
            pass

    # --- SET (EEGLAB: MATLAB v5 text header, or v7.3 HDF5) ---
    if header[:6] == b"MATLAB" or header[:8] == _HDF5_MAGIC:
        return EEGFormat.SET

    return None


def detect_format(path: str, *, header_bytes: int = 1024) -> tuple[Optional[EEGFormat], Optional[EEGFormat]]:
    """Return ``(detected_format, declared_format)`` for a file on disk.

    ``detected_format`` is from the bytes (authoritative); ``declared_format`` is
    from the extension (advisory). Either may be ``None``.
    """
    declared = declared_format_from_extension(path)
    with open(path, "rb") as fh:
        header = fh.read(header_bytes)
    detected = detect_format_from_bytes(header)
    return detected, declared
