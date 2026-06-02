"""Deterministic clinical identity generation, policies, validation, and lineage.

Design
------
An identity is ``"{kind}+{hash16}"`` where ``hash16`` is a sha256-derived digest of
a canonical payload: the kind, the identity-policy version, and the *deidentified*
component keys. Because the digest is a pure function of its inputs:

  * **Stable / deterministic** — same components ⇒ same id, forever.
  * **Collision resistant** — sha256 digest space.
  * **Versioned** — the policy version is part of the hashed payload, so a policy
    change yields new ids (and old ids remain valid records).
  * **Traceable** — non-patient identities embed their parent id (``derived_from``),
    giving Patient → Case → Study → … identity lineage.

Identities are **content-derived, never filename/folder-derived** (cardinal V2-P1
rule): a Case is portable across any future repository/storage layout.

Privacy note: ``patient_key`` and other ``*_key`` components MUST be **deidentified**
stable keys (no raw PHI). The identity system hashes them; it does not interpret PHI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import CASE_IDENTITY_VERSION

# valid id string: kind + '+' + 16 lowercase hex chars
_ID_RE = re.compile(r"^(patient|case|study|review|finding|decision)\+[0-9a-f]{16}$")


class IdentityError(ValueError):
    """Raised when identity minting or validation fails."""


@dataclass(frozen=True)
class IdentityPolicy:
    """Per-kind minting policy.

    ``parent_kind`` declares the identity-lineage parent (e.g. a case is derived
    from a patient). ``future`` marks kinds reserved for later versions; their
    policies exist so the identity system can *track* them, but V2-P1/P2 mint only
    patient/case/study (P1) and review (P2). Finding/Decision remain forbidden
    (V3+) and are never minted here.
    """

    kind: str
    required_components: tuple[str, ...]
    parent_kind: Optional[str]
    parent_component: Optional[str]  # which component carries the parent id
    future: bool = False
    identity_version: str = CASE_IDENTITY_VERSION


IDENTITY_POLICIES: dict[str, IdentityPolicy] = {
    "patient": IdentityPolicy("patient", ("patient_key",), None, None),
    "case": IdentityPolicy("case", ("patient_id", "case_key"), "patient", "patient_id"),
    "study": IdentityPolicy("study", ("case_id", "study_key"), "case", "case_id"),
    "review": IdentityPolicy("review", ("case_id", "review_key"), "case", "case_id"),
    # FUTURE (forbidden in V2-P1/P2 — not minted; present only so the identity
    # system can describe/track them, per the directive's identity list):
    "finding": IdentityPolicy("finding", ("review_id", "finding_key"), "review", "review_id", future=True),
    "decision": IdentityPolicy("decision", ("review_id", "decision_key"), "review", "review_id", future=True),
}


@dataclass(frozen=True)
class Identity:
    """A minted, content-addressed clinical identity."""

    id: str
    kind: str
    identity_version: str
    components: dict
    derived_from: Optional[str]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "identity_version": self.identity_version,
            "components": self.components,
            "derived_from": self.derived_from,
        }


def mint_identity(kind: str, components: Mapping[str, object], *, allow_future: bool = False) -> Identity:
    """Mint a deterministic identity for ``kind`` from ``components``."""
    policy = IDENTITY_POLICIES.get(kind)
    if policy is None:
        raise IdentityError(f"unknown identity kind {kind!r}")
    if policy.future and not allow_future:
        raise IdentityError(
            f"identity kind {kind!r} is reserved for a future version and must not be minted in V2-P1/P2"
        )
    missing = [c for c in policy.required_components if c not in components or components[c] in (None, "")]
    if missing:
        raise IdentityError(f"missing required components for {kind!r}: {missing}")

    # parent id (for non-root kinds) must itself be a valid identity of the parent kind
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
        id=f"{kind}+{digest}",
        kind=kind,
        identity_version=policy.identity_version,
        components=dict(components),
        derived_from=derived_from,
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
