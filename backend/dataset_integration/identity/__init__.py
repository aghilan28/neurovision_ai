"""Deterministic dataset-entity identity generation (DRP1-B / DRP1-D).

Mints content-addressed ``dataset_source`` / ``dataset`` / ``dataset_version`` ids
(``{kind}+{hash16}``) — the platform-wide scheme (NR-6). Ids are derived from the
source + manifest fingerprint, never from a filename or a download, so the same corpus
manifest always yields the same dataset id (idempotent + traceable).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import DATASET_IDENTITY_VERSION

_KINDS = "dataset_source|dataset_version|dataset"
_ID_RE = re.compile(rf"^({_KINDS})\+[0-9a-f]{{16}}$")


class IdentityError(ValueError):
    """Raised when identity minting or validation fails."""


@dataclass(frozen=True)
class _Policy:
    kind: str
    required: tuple
    parent_kind: Optional[str]
    parent_component: Optional[str]


_POLICIES = {
    "dataset_source": _Policy("dataset_source", ("source",), None, None),
    "dataset": _Policy("dataset", ("source", "dataset_key", "manifest_fingerprint"),
                       "dataset_source", "source_id"),
    "dataset_version": _Policy("dataset_version", ("dataset_id", "version_key"),
                               "dataset", "dataset_id"),
}


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
    policy = _POLICIES.get(kind)
    if policy is None:
        raise IdentityError(f"unknown identity kind {kind!r}")
    missing = [c for c in policy.required if c not in components or components[c] in (None, "")]
    if missing:
        raise IdentityError(f"missing required components for {kind!r}: {missing}")
    derived_from = None
    if policy.parent_component is not None:
        derived_from = str(components[policy.parent_component])
        ok, detail = validate_identity(derived_from, expected_kind=policy.parent_kind)
        if not ok:
            raise IdentityError(f"invalid parent identity for {kind!r}: {detail}")
    payload = {"kind": kind, "identity_version": DATASET_IDENTITY_VERSION,
               "components": {k: components[k] for k in policy.required}}
    digest = hash_obj(payload)
    return Identity(id=f"{kind}+{digest}", kind=kind, identity_version=DATASET_IDENTITY_VERSION,
                    components=dict(components), derived_from=derived_from)


def validate_identity(id_str: str, expected_kind: Optional[str] = None) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed identity {id_str!r}"
    kind = id_str.rsplit("+", 1)[0]
    if expected_kind is not None and kind != expected_kind:
        return False, f"expected kind {expected_kind!r}, got {kind!r}"
    return True, "ok"


__all__ = ["Identity", "mint_identity", "validate_identity", "IdentityError"]
