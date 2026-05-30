"""Deterministic application-entity identity generation, policy, and validation.

An identity is ``"{kind}+{hash16}"`` (the platform-wide scheme, NR-6). The application
layer mints the ``user``/``session``/``upload``/``request``/``response``/``workflow``/
``analysis``/``api`` kinds, each content-derived from its components (never time- or
filename-derived) so the same logical entity always yields the same id (idempotent).

It also *validates* (but never mints) the upstream platform ids it references
(``prediction``/``model``/``feature``/``signal``/``eeg``/``case``/``patient``), so the
User -> Upload -> ... -> Prediction identity lineage is checkable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import APPLICATION_IDENTITY_VERSION

# Application-minted kinds + referenced-only upstream kinds.
_APP_KINDS = "user|session|upload|request|response|workflow|analysis|api"
_UPSTREAM_KINDS = "prediction|model|training_run|dataset|feature|signal|eeg|case|patient"
_ID_RE = re.compile(rf"^({_APP_KINDS}|{_UPSTREAM_KINDS})\+[0-9a-f]{{16}}$")


class IdentityError(ValueError):
    """Raised when identity minting or validation fails."""


@dataclass(frozen=True)
class IdentityPolicy:
    kind: str
    required_components: tuple[str, ...]
    parent_kind: Optional[str]
    parent_component: Optional[str]
    mintable: bool = True
    identity_version: str = APPLICATION_IDENTITY_VERSION


IDENTITY_POLICIES: dict[str, IdentityPolicy] = {
    # --- application-minted kinds ---
    "user": IdentityPolicy("user", ("username",), None, None),
    "session": IdentityPolicy("session", ("user_id", "session_key"), "user", "user_id"),
    "upload": IdentityPolicy("upload", ("user_id", "upload_key"), "user", "user_id"),
    "workflow": IdentityPolicy("workflow", ("upload_id", "workflow_key"), "upload", "upload_id"),
    "analysis": IdentityPolicy("analysis", ("workflow_id", "analysis_key"), "workflow", "workflow_id"),
    # requests may be unauthenticated (register/login), so they have no parent kind.
    "request": IdentityPolicy("request", ("operation", "request_key"), None, None),
    "response": IdentityPolicy("response", ("request_id", "response_key"), "request", "request_id"),
    "api": IdentityPolicy("api", ("name", "api_version"), None, None),
    # --- referenced-only upstream kinds (minted by P1-P5; here only validated) ---
    "prediction": IdentityPolicy("prediction", (), None, None, mintable=False),
    "model": IdentityPolicy("model", (), None, None, mintable=False),
    "feature": IdentityPolicy("feature", (), None, None, mintable=False),
    "signal": IdentityPolicy("signal", (), None, None, mintable=False),
    "eeg": IdentityPolicy("eeg", (), None, None, mintable=False),
    "case": IdentityPolicy("case", (), None, None, mintable=False),
    "patient": IdentityPolicy("patient", (), None, None, mintable=False),
}


@dataclass(frozen=True)
class Identity:
    id: str
    kind: str
    identity_version: str
    components: dict
    derived_from: Optional[str]

    def to_dict(self) -> dict:
        return {
            "id": self.id, "kind": self.kind, "identity_version": self.identity_version,
            "components": self.components, "derived_from": self.derived_from,
        }


def mint_identity(kind: str, components: Mapping[str, object]) -> Identity:
    policy = IDENTITY_POLICIES.get(kind)
    if policy is None:
        raise IdentityError(f"unknown identity kind {kind!r}")
    if not policy.mintable:
        raise IdentityError(f"identity kind {kind!r} is referenced-only and must not be minted here")
    missing = [c for c in policy.required_components
               if c not in components or components[c] in (None, "")]
    if missing:
        raise IdentityError(f"missing required components for {kind!r}: {missing}")

    derived_from = None
    if policy.parent_component is not None:
        derived_from = str(components[policy.parent_component])
        ok, detail = validate_identity(derived_from, expected_kind=policy.parent_kind)
        if not ok:
            raise IdentityError(f"invalid parent identity for {kind!r}: {detail}")

    payload = {
        "kind": kind, "identity_version": policy.identity_version,
        "components": {k: components[k] for k in policy.required_components},
    }
    digest = hash_obj(payload)
    return Identity(id=f"{kind}+{digest}", kind=kind, identity_version=policy.identity_version,
                    components=dict(components), derived_from=derived_from)


def parse_identity(id_str: str) -> tuple[str, str]:
    if not _ID_RE.match(id_str or ""):
        raise IdentityError(f"malformed identity string {id_str!r}")
    kind, digest = id_str.rsplit("+", 1)
    return kind, digest


def validate_identity(id_str: str, expected_kind: Optional[str] = None) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed identity {id_str!r}"
    kind = id_str.rsplit("+", 1)[0]
    if expected_kind is not None and kind != expected_kind:
        return False, f"expected kind {expected_kind!r}, got {kind!r}"
    return True, "ok"
