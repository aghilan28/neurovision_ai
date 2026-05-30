"""``backend/inference_foundation/identity`` — deterministic prediction-asset ids.

A prediction asset id is ``prediction+{hash16}`` derived from the ``model`` id + the
prediction fingerprint (never filename-derived). Mirrors the platform identity scheme
so Patient -> ... -> Model -> Prediction identity lineage is checkable.
"""

from __future__ import annotations

from .identity import (
    Identity, IdentityError, IdentityPolicy, IDENTITY_POLICIES,
    mint_identity, parse_identity, validate_identity,
)

__all__ = [
    "Identity", "IdentityError", "IdentityPolicy", "IDENTITY_POLICIES",
    "mint_identity", "parse_identity", "validate_identity",
]
