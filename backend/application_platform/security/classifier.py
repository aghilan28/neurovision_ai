"""``backend/application_platform/security/classifier.py`` — request authentication
classifier (DBE5-C / DBE5-E).

The single, deterministic, never-crashing function that turns an inbound ``Authorization``
header + the target operation into a :class:`TokenClassification`, by **reusing** the
operative ``AuthService`` (opaque session tokens) and the existing **authorization policy**
(``OPERATION_ROLES`` from ``application_backend.validation``). No new auth/authz architecture
is introduced — this is the hardened boundary guard that guarantees an invalid token is
classified and rejected with a controlled response *before* any business logic runs.
"""

from __future__ import annotations

from typing import Optional

from backend.application_backend.models.domain import ApiOperation
from backend.application_backend.validation import OPERATION_ROLES, is_public

from .token_validation import (
    TokenClassification, TokenFailureCode, classify_structured_token, extract_bearer,
    is_wellformed_opaque, looks_like_jwt,
)


def classify_request(*, auth_service, authorization: Optional[str],
                     operation: ApiOperation) -> TokenClassification:
    """Classify a bearer credential for ``operation`` — deterministic, never raises.

    Returns an ``ok`` classification (with the validated session + user) only when the
    token authenticates to an active session **and** the user's role is permitted for the
    operation. Every other path returns a closed-vocabulary :class:`TokenFailureCode`.
    """
    op_value = getattr(operation, "value", str(operation))

    try:
        present, token = extract_bearer(authorization)
        if not present:
            return TokenClassification(TokenFailureCode.MISSING_TOKEN, operation=op_value)
        if token == "":
            return TokenClassification(TokenFailureCode.EMPTY_TOKEN, operation=op_value)

        # Foreign structured (JWT-shaped) credential: classify precisely (never trusted).
        if looks_like_jwt(token):
            code = classify_structured_token(token)
            return TokenClassification(code, token=token, operation=op_value)

        # Opaque session token: authoritative, read-only state classification via the
        # real AuthService (reused; not reimplemented).
        try:
            state, session = auth_service.classify_session_token(token)
        except Exception:  # noqa: BLE001 — contain any unexpected internal error
            return TokenClassification(TokenFailureCode.UNKNOWN_TOKEN_FAILURE, token=token,
                                       operation=op_value)

        if state == "active":
            return _authorize(auth_service, session, token, operation, op_value)
        if state == "revoked":
            return TokenClassification(TokenFailureCode.EXPIRED_TOKEN, token=token,
                                       session=session, operation=op_value)
        if state == "inactive_user":
            return TokenClassification(TokenFailureCode.UNAUTHORIZED, token=token,
                                       session=session, operation=op_value)
        # state == "unknown": well-formed-but-unknown opaque token -> UNAUTHORIZED;
        # anything not shaped like a live token -> MALFORMED_TOKEN.
        if is_wellformed_opaque(token):
            return TokenClassification(TokenFailureCode.UNAUTHORIZED, token=token,
                                       operation=op_value)
        return TokenClassification(TokenFailureCode.MALFORMED_TOKEN, token=token,
                                   operation=op_value)
    except Exception:  # noqa: BLE001 — absolute containment: never crash the classifier
        return TokenClassification(TokenFailureCode.UNKNOWN_TOKEN_FAILURE, operation=op_value)


def _authorize(auth_service, session, token: str, operation: ApiOperation,
               op_value: str) -> TokenClassification:
    """Resolve the user and enforce the existing role policy (default-deny). Never raises."""
    if is_public(operation):
        # Public operations need no authorization, but an authenticated session is still fine.
        user = _safe_user(auth_service, session)
        return TokenClassification(None, token=token, session=session, user=user,
                                   operation=op_value)
    user = _safe_user(auth_service, session)
    if user is None:
        return TokenClassification(TokenFailureCode.UNAUTHORIZED, token=token, session=session,
                                   operation=op_value)
    allowed = OPERATION_ROLES.get(operation, frozenset())
    if not any(r in allowed for r in getattr(user, "roles", ())):
        return TokenClassification(TokenFailureCode.FORBIDDEN, token=token, session=session,
                                   user=user, operation=op_value)
    return TokenClassification(None, token=token, session=session, user=user, operation=op_value)


def _safe_user(auth_service, session):
    try:
        return auth_service.users.get_user(session.user_id)
    except Exception:  # noqa: BLE001
        return None


__all__ = ["classify_request"]
