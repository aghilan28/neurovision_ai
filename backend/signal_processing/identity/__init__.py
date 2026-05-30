"""``backend/signal_processing/identity`` — deterministic processed-EEG ids.

A processed asset id is ``signal+{hash16}`` derived from the raw ``eeg`` asset id +
the processing fingerprint (never the filename). Mirrors the platform identity
scheme so Patient -> Case -> EEG -> Processed identity lineage is checkable.
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
