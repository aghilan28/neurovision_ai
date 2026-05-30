"""Deterministic recommendation-artifact identity generation (V3-P6).

A recommendation identity is ``"recommendation+{hash16}"`` — a sha256 digest of a
canonical payload (kind, identity version, recommendation kind, scope). Stable,
deterministic, collision resistant, versioned. The logical identity is the
*recommendation definition* (kind + scope), so re-deriving the same recommendation
over refreshed analytics yields the same id with a new content version (auditable),
never an orphan.

Recommendations are **derived, explainable** outputs — their identity is a function
of *what they advise and for which scope*, not of any independent state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import RECOMMENDATION_IDENTITY_VERSION

_ID_RE = re.compile(r"^recommendation\+[0-9a-f]{16}$")


class RecommendationIdentityError(ValueError):
    """Raised when recommendation identity minting or validation fails."""


@dataclass(frozen=True)
class RecommendationIdentity:
    id: str
    kind: str
    scope: str
    identity_version: str = RECOMMENDATION_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "scope": self.scope,
                "identity_version": self.identity_version}


def mint_recommendation(kind: str, scope: str) -> RecommendationIdentity:
    if not kind or not scope:
        raise RecommendationIdentityError("kind and scope must be non-empty")
    payload = {"kind": "recommendation", "identity_version": RECOMMENDATION_IDENTITY_VERSION,
               "recommendation_kind": kind, "scope": scope}
    return RecommendationIdentity(id=f"recommendation+{hash_obj(payload)}", kind=kind, scope=scope)


def validate_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed recommendation identity {id_str!r}"
    return True, "ok"
