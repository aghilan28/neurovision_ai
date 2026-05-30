"""``backend/feature_engineering/identity`` — deterministic feature-asset ids.

A feature asset id is ``feature+{hash16}`` derived from the processed ``signal``
asset id + the feature-extraction fingerprint (never filename-derived). Mirrors the
platform identity scheme so Patient -> Case -> EEG -> Processed -> Feature identity
lineage is checkable.
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
