"""Deterministic security identity generation and validation.

An identity is ``"{kind}+{hash16}"`` (the platform-wide scheme, NR-6). This layer mints the
security kinds — ``security_user``, ``credential``, ``security_session``, ``authentication``,
``authorization``, ``access_control``, ``security_policy``, ``security_readiness`` — each
content-addressed from its inputs (identical inputs reproduce identical ids).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import SECURITY_IDENTITY_VERSION

_KINDS = (
    "security_user", "credential", "security_session", "authentication", "authorization",
    "access_control", "security_policy", "security_readiness",
)
_ID_RE = re.compile(r"^(" + "|".join(_KINDS) + r")\+[0-9a-f]{16}$")

# parent kind for each kind, to keep the identity lineage checkable
_PARENT = {
    "credential": ("security_user", "user_id"),
    "security_session": ("credential", "credential_id"),
    "authentication": ("credential", "credential_id"),
    "authorization": ("authentication", "authentication_id"),
    "access_control": ("authorization", "authorization_id"),
}
_REQUIRED = {
    "security_user": ("username",),
    "credential": ("user_id", "hash_hex"),
    "security_session": ("credential_id", "token_fingerprint"),
    "authentication": ("credential_id", "outcome"),
    "authorization": ("authentication_id", "resource_id", "action", "decision"),
    "access_control": ("authorization_id", "resource_id"),
    "security_policy": ("name", "role", "resource_type", "action", "effect"),
    "security_readiness": ("target_id",),
}


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


def mint_identity(kind: str, components: Mapping[str, object]) -> Identity:
    if kind not in _REQUIRED:
        raise IdentityError(f"unknown identity kind {kind!r}")
    missing = [c for c in _REQUIRED[kind] if c not in components or components[c] in (None, "")]
    if missing:
        raise IdentityError(f"missing required components for {kind!r}: {missing}")
    derived_from = None
    if kind in _PARENT:
        parent_kind, comp = _PARENT[kind]
        derived_from = str(components[comp])
        ok, detail = validate_identity(derived_from, expected_kind=parent_kind)
        if not ok:
            raise IdentityError(f"invalid parent identity for {kind!r}: {detail}")
    payload = {"kind": kind, "identity_version": SECURITY_IDENTITY_VERSION,
               "components": {k: components[k] for k in _REQUIRED[kind]}}
    digest = hash_obj(payload)
    return Identity(id=f"{kind}+{digest}", kind=kind, identity_version=SECURITY_IDENTITY_VERSION,
                    components=dict(components), derived_from=derived_from)


def validate_identity(id_str: str, expected_kind: Optional[str] = None) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed identity {id_str!r}"
    kind = id_str.rsplit("+", 1)[0]
    if expected_kind is not None and kind != expected_kind:
        return False, f"expected kind {expected_kind!r}, got {kind!r}"
    return True, "ok"
