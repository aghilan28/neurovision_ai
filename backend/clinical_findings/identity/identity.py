"""Deterministic finding/evidence/interpretation identity generation.

An identity is ``"{kind}+{hash16}"`` — a sha256-derived digest of a canonical
payload (kind, identity version, deidentified component keys). Properties: stable,
deterministic, versioned, collision-resistant, traceable (non-root ids embed their
parent via ``derived_from``).

  * ``finding``        — derived from a ``review`` id (the review that produced it).
  * ``evidence``       — derived from a ``finding`` id.
  * ``interpretation`` — derived from a ``finding`` id.

This is a separate minting authority from ``clinical_cases.identity`` (which is left
unchanged); it produces the same id *format*, so the case-system validator (whose
regex already recognises ``finding``) interoperates with finding ids.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from ml.provenance import hash_obj  # allowed: backend -> ml
from backend.clinical_cases.identity import validate_identity as validate_case_identity

from ..version import FINDING_IDENTITY_VERSION

_ID_RE = re.compile(r"^(finding|evidence|interpretation)\+[0-9a-f]{16}$")


class FindingIdentityError(ValueError):
    """Raised when finding-graph identity minting or validation fails."""


@dataclass(frozen=True)
class _Identity:
    id: str
    kind: str
    identity_version: str
    components: dict
    derived_from: Optional[str]

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "identity_version": self.identity_version,
                "components": self.components, "derived_from": self.derived_from}


def _mint(kind: str, components: Mapping[str, object]) -> _Identity:
    payload = {"kind": kind, "identity_version": FINDING_IDENTITY_VERSION,
               "components": dict(components)}
    return _Identity(id=f"{kind}+{hash_obj(payload)}", kind=kind,
                     identity_version=FINDING_IDENTITY_VERSION, components=dict(components),
                     derived_from=None)


def mint_finding(review_id: str, finding_key: str) -> _Identity:
    ok, detail = validate_case_identity(review_id, "review")
    if not ok:
        raise FindingIdentityError(f"invalid parent review identity: {detail}")
    if not finding_key:
        raise FindingIdentityError("finding_key must be non-empty")
    ident = _mint("finding", {"review_id": review_id, "finding_key": finding_key})
    return _replace_parent(ident, review_id)


def mint_evidence(finding_id: str, evidence_key: str) -> _Identity:
    ok, detail = validate_identity(finding_id, "finding")
    if not ok:
        raise FindingIdentityError(f"invalid parent finding identity: {detail}")
    if not evidence_key:
        raise FindingIdentityError("evidence_key must be non-empty")
    ident = _mint("evidence", {"finding_id": finding_id, "evidence_key": evidence_key})
    return _replace_parent(ident, finding_id)


def mint_interpretation(finding_id: str, interpretation_key: str) -> _Identity:
    ok, detail = validate_identity(finding_id, "finding")
    if not ok:
        raise FindingIdentityError(f"invalid parent finding identity: {detail}")
    if not interpretation_key:
        raise FindingIdentityError("interpretation_key must be non-empty")
    ident = _mint("interpretation", {"finding_id": finding_id, "interpretation_key": interpretation_key})
    return _replace_parent(ident, finding_id)


def _replace_parent(ident: _Identity, parent: str) -> _Identity:
    return _Identity(id=ident.id, kind=ident.kind, identity_version=ident.identity_version,
                     components=ident.components, derived_from=parent)


def parse_identity(id_str: str) -> tuple[str, str]:
    if not _ID_RE.match(id_str or ""):
        raise FindingIdentityError(f"malformed identity string {id_str!r}")
    kind, digest = id_str.split("+", 1)
    return kind, digest


def validate_identity(id_str: str, expected_kind: Optional[str] = None) -> tuple[bool, str]:
    """Validate a finding-graph identity string (+ optional kind)."""
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed identity {id_str!r}"
    kind = id_str.split("+", 1)[0]
    if expected_kind is not None and kind != expected_kind:
        return False, f"expected kind {expected_kind!r}, got {kind!r}"
    return True, "ok"
