"""Deterministic temporal-artifact identity generation (V3-P2).

An identity is ``"{kind}+{hash16}"`` — a sha256 digest of a canonical payload
(kind, identity version, scope). Stable, deterministic, collision resistant,
versioned.

  * ``timeline``        — derived from a timeline scope (entity kind + id).
  * ``history``         — derived from a history scope.
  * ``evolution``       — derived from an evolution scope.
  * ``temporal_analytics`` — derived from an analytics scope.
  * ``temporal_report`` — derived from report type + scope.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import TEMPORAL_IDENTITY_VERSION

_KINDS = ("timeline", "history", "evolution", "temporal_analytics", "temporal_report")
_ID_RE = re.compile(
    r"^(timeline|history|evolution|temporal_analytics|temporal_report)\+[0-9a-f]{16}$")


class TemporalIdentityError(ValueError):
    """Raised when temporal-artifact identity minting or validation fails."""


@dataclass(frozen=True)
class TemporalIdentity:
    id: str
    kind: str
    scope: str
    identity_version: str = TEMPORAL_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "scope": self.scope,
                "identity_version": self.identity_version}


def _mint(kind: str, scope: str) -> TemporalIdentity:
    if kind not in _KINDS:
        raise TemporalIdentityError(f"unknown temporal identity kind {kind!r}")
    if not scope:
        raise TemporalIdentityError("scope must be non-empty")
    payload = {"kind": kind, "identity_version": TEMPORAL_IDENTITY_VERSION, "scope": scope}
    return TemporalIdentity(id=f"{kind}+{hash_obj(payload)}", kind=kind, scope=scope)


def mint_timeline(scope: str) -> TemporalIdentity:
    return _mint("timeline", scope)


def mint_history(scope: str) -> TemporalIdentity:
    return _mint("history", scope)


def mint_evolution(scope: str) -> TemporalIdentity:
    return _mint("evolution", scope)


def mint_analytics(scope: str) -> TemporalIdentity:
    return _mint("temporal_analytics", scope)


def mint_report(report_type: str, scope: str) -> TemporalIdentity:
    if not report_type:
        raise TemporalIdentityError("report_type must be non-empty")
    return _mint("temporal_report", f"{report_type}:{scope}")


def validate_identity(id_str: str, expected_kind: Optional[str] = None) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed temporal identity {id_str!r}"
    kind = id_str.split("+", 1)[0]
    if expected_kind is not None and kind != expected_kind:
        return False, f"expected kind {expected_kind!r}, got {kind!r}"
    return True, "ok"
