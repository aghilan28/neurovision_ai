"""``backend/eeg_foundation/identity`` — deterministic, content-addressed EEG ids.

An EEG asset id is ``eeg+{hash16}`` derived from its case + a content fingerprint
of the file (never the filename). Mirrors the platform identity scheme used by
``clinical_cases`` so Patient -> Case -> EEG identity lineage is checkable.
"""

from __future__ import annotations

from .identity import (
    Identity,
    IdentityError,
    IdentityPolicy,
    IDENTITY_POLICIES,
    mint_identity,
    parse_identity,
    validate_identity,
)

__all__ = [
    "Identity",
    "IdentityError",
    "IdentityPolicy",
    "IDENTITY_POLICIES",
    "mint_identity",
    "parse_identity",
    "validate_identity",
]
