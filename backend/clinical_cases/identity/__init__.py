"""``backend/clinical_cases/identity`` — deterministic clinical identity system (V2-P1).

Mints stable, deterministic, versioned, collision-resistant, traceable identifiers
for the clinical object graph (Patient → Case → Study → Review → …). Identities are
content-derived (never filename- or folder-derived), so a Case survives any future
architecture evolution (a V2-P1 cardinal principle).
"""

from __future__ import annotations

from .identity import (
    Identity,
    IdentityPolicy,
    IDENTITY_POLICIES,
    mint_identity,
    validate_identity,
    parse_identity,
    IdentityError,
)

__all__ = [
    "Identity",
    "IdentityPolicy",
    "IDENTITY_POLICIES",
    "mint_identity",
    "validate_identity",
    "parse_identity",
    "IdentityError",
]
