"""File-signature detection for EEG containers.

Version 1 supports EDF and EDF+ only. This module classifies a file's container
format from its header bytes so that out-of-scope formats (e.g. BDF) are detected
and *reported* as ``UNSUPPORTED`` rather than mis-parsed (V1 directive; Rule NR-13).

The classification is structural, not extension-based: the bytes decide, never the
filename. This keeps ingestion honest about what a file actually is.
"""

from __future__ import annotations

from datasets.ingestion.edf_reader import MAIN_HEADER_BYTES
from datasets.schemas.enums import FileFormat

# EDF main header version field is "0" (0x30) padded with spaces.
_EDF_VERSION_BYTE = 0x30
# BDF (BioSemi) — explicitly unsupported in V1; detected to report clearly.
_BDF_MAGIC = b"\xffBIOSEMI"


def sniff_signature(path: str) -> bytes:
    """Return the first 8 bytes of ``path`` (the EDF version field region)."""
    with open(path, "rb") as handle:
        return handle.read(8)


def detect_format(path: str) -> FileFormat:
    """Detect the container format of ``path`` from its header bytes.

    Returns one of :class:`~datasets.schemas.enums.FileFormat`. EDF+ continuity is
    distinguished via the reserved field (``"EDF+C"`` / ``"EDF+D"``). Anything that
    is not recognizably EDF is ``UNSUPPORTED`` (known magic, e.g. BDF) or
    ``UNKNOWN`` (unrecognized).
    """
    with open(path, "rb") as handle:
        head = handle.read(MAIN_HEADER_BYTES)

    if len(head) >= 8 and head[:8] == _BDF_MAGIC:
        return FileFormat.UNSUPPORTED  # BDF — out of scope for V1
    if len(head) < MAIN_HEADER_BYTES:
        return FileFormat.UNKNOWN
    if head[0] != _EDF_VERSION_BYTE:
        return FileFormat.UNKNOWN

    version_field = head[0:8].decode("latin-1").strip()
    if version_field != "0":
        return FileFormat.UNKNOWN

    reserved = head[192:236].decode("latin-1").strip().upper()
    if reserved.startswith("EDF+D"):
        return FileFormat.EDF_PLUS_D
    if reserved.startswith("EDF+C") or reserved.startswith("EDF+"):
        return FileFormat.EDF_PLUS_C
    return FileFormat.EDF
