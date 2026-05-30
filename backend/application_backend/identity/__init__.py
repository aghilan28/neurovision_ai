"""``backend/application_backend/identity`` — deterministic application-entity ids (P6-B).

Mints content-addressed ``user``/``session``/``upload``/``request``/``response``/
``workflow``/``analysis``/``api`` ids (``{kind}+{hash16}``) and validates the upstream
platform ids it references, so the application identity lineage stays checkable.
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
