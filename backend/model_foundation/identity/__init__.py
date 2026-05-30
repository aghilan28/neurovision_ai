"""``backend/model_foundation/identity`` — deterministic model-foundation ids.

Mints ``dataset`` / ``training_run`` / ``evaluation`` / ``experiment`` / ``model`` ids
(content-addressed). A model derives from a training run, which derives from a
dataset, so the Patient -> ... -> Dataset -> Training Run -> Model lineage is checkable.
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
