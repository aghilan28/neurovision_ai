"""Deterministic EEG-asset identity generation, policy, and validation.

An identity is ``"{kind}+{hash16}"`` where ``hash16`` is a sha256-derived digest of
a canonical payload (kind + identity-policy version + component keys). This is the
exact scheme used by ``backend.clinical_cases.identity`` (NR-6: one identity
pattern, platform-wide) — re-stated here so the EEG layer stays decoupled from the
clinical-case package while remaining byte-compatible with case/patient ids.

Cardinal rule: an EEG asset id is **content-derived, never filename/folder-derived**.
The ``eeg_key`` component is a content fingerprint of the file's bytes, so the same
recording under the same case always yields the same ``asset_id`` (idempotent
ingestion), and a renamed/moved file is still the same asset.

The EEG layer mints only the ``eeg`` kind; it *validates* (but never mints) the
``case``/``patient`` ids it derives from, so the Patient -> Case -> EEG identity
lineage is checkable end-to-end.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import EEG_IDENTITY_VERSION

# valid id string: a supported kind + '+' + 16 lowercase hex chars
_ID_RE = re.compile(r"^(eeg|case|patient)\+[0-9a-f]{16}$")


class IdentityError(ValueError):
    """Raised when identity minting or validation fails."""


@dataclass(frozen=True)
class IdentityPolicy:
    """Per-kind minting policy. ``parent_kind`` declares the identity-lineage parent."""

    kind: str
    required_components: tuple[str, ...]
    parent_kind: Optional[str]
    parent_component: Optional[str]
    mintable: bool = True
    identity_version: str = EEG_IDENTITY_VERSION


IDENTITY_POLICIES: dict[str, IdentityPolicy] = {
    # The only kind the EEG layer mints: an asset derived from a case.
    "eeg": IdentityPolicy("eeg", ("case_id", "eeg_key"), "case", "case_id"),
    # Referenced-only kinds (minted by clinical_cases). Present so the EEG layer can
    # *validate* the parent/grandparent ids it derives from; never minted here.
    "case": IdentityPolicy("case", ("patient_id", "case_key"), "patient", "patient_id", mintable=False),
    "patient": IdentityPolicy("patient", ("patient_key",), None, None, mintable=False),
}


@dataclass(frozen=True)
class Identity:
    """A minted, content-addressed EEG identity."""

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
    """Mint a deterministic identity for ``kind`` from ``components``."""
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
        "kind": kind,
        "identity_version": policy.identity_version,
        "components": {k: components[k] for k in policy.required_components},
    }
    digest = hash_obj(payload)  # 16 lowercase hex
    return Identity(
        id=f"{kind}+{digest}", kind=kind, identity_version=policy.identity_version,
        components=dict(components), derived_from=derived_from,
    )


def parse_identity(id_str: str) -> tuple[str, str]:
    """Return ``(kind, digest)`` for a well-formed identity string."""
    if not _ID_RE.match(id_str or ""):
        raise IdentityError(f"malformed identity string {id_str!r}")
    kind, digest = id_str.split("+", 1)
    return kind, digest


def validate_identity(id_str: str, expected_kind: Optional[str] = None) -> tuple[bool, str]:
    """Validate an identity string's format (+ optional kind). Returns (ok, detail)."""
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed identity {id_str!r}"
    kind = id_str.split("+", 1)[0]
    if expected_kind is not None and kind != expected_kind:
        return False, f"expected kind {expected_kind!r}, got {kind!r}"
    return True, "ok"
