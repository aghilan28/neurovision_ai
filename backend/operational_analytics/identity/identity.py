"""Deterministic analytics-artifact identity generation (V3-P5).

An analytics identity is ``"analytics+{hash16}"`` — a sha256 digest of a canonical
payload (kind, identity version, analytics category, scope). Stable, deterministic,
collision resistant, versioned. The logical identity is the *analytics definition*
(category + scope), so re-deriving the same analytics over more upstream artifacts
yields the same id with a new content version (auditable), never an orphan.

Analytics is **derived intelligence**, never a source of truth — its identity is a
function of *what it summarizes*, not of any independent state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import ANALYTICS_IDENTITY_VERSION

_ID_RE = re.compile(r"^analytics\+[0-9a-f]{16}$")


class AnalyticsIdentityError(ValueError):
    """Raised when analytics identity minting or validation fails."""


@dataclass(frozen=True)
class AnalyticsIdentity:
    id: str
    category: str
    scope: str
    identity_version: str = ANALYTICS_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "category": self.category, "scope": self.scope,
                "identity_version": self.identity_version}


def mint_analytics(category: str, scope: str) -> AnalyticsIdentity:
    if not category or not scope:
        raise AnalyticsIdentityError("category and scope must be non-empty")
    payload = {"kind": "analytics", "identity_version": ANALYTICS_IDENTITY_VERSION,
               "category": category, "scope": scope}
    return AnalyticsIdentity(id=f"analytics+{hash_obj(payload)}", category=category, scope=scope)


def validate_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed analytics identity {id_str!r}"
    return True, "ok"
