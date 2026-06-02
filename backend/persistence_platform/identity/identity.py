"""Deterministic persistence identity generation, policy, and validation.

An identity is ``"{kind}+{hash16}"`` (the platform-wide scheme, NR-6). This layer mints the
persistence-specific kinds — ``persistence_record``, ``recovery_event`` — each
content-addressed from its inputs (so identical inputs reproduce identical ids). The
upstream ``serving_response``/``serving_execution``/``model``/... ids are minted by their
owning subsystems (reused, not duplicated); this layer *validates* (but never mints) the
anchor id it references.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import PERSISTENCE_IDENTITY_VERSION

_ID_RE = re.compile(
    r"^(persistence_record|recovery_event"
    r"|serving_response|serving_execution|serving_request|model|prediction|feature|dataset)"
    r"\+[0-9a-f]{16}$")


class IdentityError(ValueError):
    """Raised when identity minting or validation fails."""


@dataclass(frozen=True)
class Identity:
    id: str
    kind: str
    identity_version: str
    components: dict
    derived_from: Optional[str]

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "identity_version": self.identity_version,
                "components": self.components, "derived_from": self.derived_from}


_MINTABLE = {
    "persistence_record": ("snapshot_fingerprint",),
    "recovery_event": ("persistence_id",),
}


def mint_identity(kind: str, components: Mapping[str, object]) -> Identity:
    if kind not in _MINTABLE:
        raise IdentityError(f"identity kind {kind!r} is not mintable here")
    required = _MINTABLE[kind]
    missing = [c for c in required if c not in components or components[c] in (None, "")]
    if missing:
        raise IdentityError(f"missing required components for {kind!r}: {missing}")
    derived_from = None
    if kind == "recovery_event":
        derived_from = str(components["persistence_id"])
        ok, detail = validate_identity(derived_from, expected_kind="persistence_record")
        if not ok:
            raise IdentityError(f"invalid parent identity for {kind!r}: {detail}")
    payload = {"kind": kind, "identity_version": PERSISTENCE_IDENTITY_VERSION,
               "components": {k: components[k] for k in required}}
    digest = hash_obj(payload)
    return Identity(id=f"{kind}+{digest}", kind=kind, identity_version=PERSISTENCE_IDENTITY_VERSION,
                    components=dict(components), derived_from=derived_from)


def validate_identity(id_str: str, expected_kind: Optional[str] = None) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed identity {id_str!r}"
    kind = id_str.rsplit("+", 1)[0]
    if expected_kind is not None and kind != expected_kind:
        return False, f"expected kind {expected_kind!r}, got {kind!r}"
    return True, "ok"
