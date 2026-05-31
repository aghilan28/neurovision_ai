"""Deterministic identity generation for the Real Dataset Platform (Track 1).

Mints content-addressed ``{kind}+{hash16}`` ids — the platform-wide scheme (NR-6).
Ids are derived from real content (the dataset source, the local content
fingerprint over real file checksums, patient keys, recording ids) — never from a
download timestamp or an arbitrary counter — so the same files always yield the same
ids (idempotent + traceable).

``dataset_recording`` ids are **not** minted here: they are minted by the reused
``eeg_foundation`` metadata extractor (``recording+{hash16}``, content-addressed from
the real file), so the same recording is identified consistently across the platform.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import ACQUISITION_IDENTITY_VERSION

_KINDS = ("dataset_source", "real_dataset", "dataset_patient", "dataset_session",
          "dataset_label", "dataset_registry")
_ID_RE = re.compile(r"^([a-z_]+)\+[0-9a-f]{16}$")

_REQUIRED: dict[str, tuple] = {
    "dataset_source": ("source",),
    "real_dataset": ("source", "content_fingerprint"),
    "dataset_patient": ("source", "patient_key"),
    "dataset_session": ("source", "patient_key", "session_key"),
    "dataset_label": ("recording_id", "scheme", "value"),
    "dataset_registry": ("dataset_id",),
}


class IdentityError(ValueError):
    """Raised when identity minting or validation fails."""


@dataclass(frozen=True)
class Identity:
    id: str
    kind: str
    identity_version: str
    components: dict

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "identity_version": self.identity_version,
                "components": self.components}


def mint_identity(kind: str, components: Mapping[str, object]) -> Identity:
    if kind not in _REQUIRED:
        raise IdentityError(f"unknown identity kind {kind!r}")
    required = _REQUIRED[kind]
    missing = [c for c in required if c not in components or components[c] in (None, "")]
    if missing:
        raise IdentityError(f"missing required components for {kind!r}: {missing}")
    payload = {"kind": kind, "identity_version": ACQUISITION_IDENTITY_VERSION,
               "components": {k: components[k] for k in required}}
    digest = hash_obj(payload)
    return Identity(id=f"{kind}+{digest}", kind=kind,
                    identity_version=ACQUISITION_IDENTITY_VERSION, components=dict(components))


def validate_identity(id_str: str, expected_kind: Optional[str] = None) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed identity {id_str!r}"
    kind = id_str.rsplit("+", 1)[0]
    if expected_kind is not None and kind != expected_kind:
        return False, f"expected kind {expected_kind!r}, got {kind!r}"
    return True, "ok"


__all__ = ["Identity", "mint_identity", "validate_identity", "IdentityError"]
