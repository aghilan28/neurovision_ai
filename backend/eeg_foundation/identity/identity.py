"""Deterministic EEG-asset identity generation (Productization P1).

Every EEG artifact has a content-derived identity — a sha256-derived digest of a
canonical payload (the file fingerprint + format + normalized key fields). Because the
digest is a pure function of its inputs it is stable/deterministic, collision-resistant,
versioned (the identity version is part of the hashed payload), and traceable. The same
file always mints the same ``eeg+{hash16}`` id.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import EEG_IDENTITY_VERSION

_EEG_ID_RE = re.compile(r"^eeg\+[0-9a-f]{16}$")
_STORAGE_ID_RE = re.compile(r"^eegblob\+[0-9a-f]{16}$")


class EEGIdentityError(ValueError):
    """Raised when EEG identity minting or validation fails."""


@dataclass(frozen=True)
class EEGIdentity:
    id: str
    fmt: str
    fingerprint: str
    identity_version: str = EEG_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "format": self.fmt, "fingerprint": self.fingerprint,
                "identity_version": self.identity_version}


def mint_eeg(fmt: str, fingerprint: str) -> EEGIdentity:
    if not (fmt and fingerprint):
        raise EEGIdentityError("EEG identity requires format and fingerprint")
    payload = {"kind": "eeg", "identity_version": EEG_IDENTITY_VERSION,
               "format": fmt, "fingerprint": fingerprint}
    return EEGIdentity(id=f"eeg+{hash_obj(payload)}", fmt=fmt, fingerprint=fingerprint)


def mint_storage_id(checksum: str) -> str:
    if not checksum:
        raise EEGIdentityError("storage id requires a checksum")
    payload = {"kind": "eegblob", "identity_version": EEG_IDENTITY_VERSION, "checksum": checksum}
    return f"eegblob+{hash_obj(payload)}"


def validate_eeg_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _EEG_ID_RE.match(id_str):
        return False, f"malformed EEG identity {id_str!r}"
    return True, "ok"


def validate_storage_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _STORAGE_ID_RE.match(id_str):
        return False, f"malformed EEG storage identity {id_str!r}"
    return True, "ok"
