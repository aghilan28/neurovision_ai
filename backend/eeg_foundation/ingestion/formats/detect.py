"""Content-based EEG format detection (Productization P1).

Detection inspects the real leading bytes (magic/structure), not just the extension.
Returns one of the closed supported formats, or ``"UNKNOWN"``.
"""

from __future__ import annotations

from ...models.domain import EEGFormat
from .edf import is_edf_family, _detect_family
from .fif import is_fif
from .setfile import is_set


def detect_format(head: bytes) -> str:
    """Detect the container format from the leading bytes."""
    if is_set(head[:19]):
        return EEGFormat.SET
    if is_fif(head[:4]):
        return EEGFormat.FIF
    if is_edf_family(head[:8]):
        fam = _detect_family(head[:8])
        return EEGFormat.BDF if fam == "BDF" else EEGFormat.EDF
    return "UNKNOWN"


def detect_format_path(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            head = fh.read(256)
    except OSError:
        return "UNKNOWN"
    return detect_format(head)
