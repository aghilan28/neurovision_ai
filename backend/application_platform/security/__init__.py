"""``backend/application_platform/security`` — authentication reliability layer (DBE-5).

Hardens the *existing* operative authentication (``backend.application_backend.auth``) at the
HTTP boundary so that **no invalid-token or authorization-failure path can ever produce an
HTTP 500**. It introduces **no** new authentication/authorization framework and issues no
tokens — it only validates, classifies, and rejects inbound bearer credentials with
controlled, documented 401/403 responses, and emits security audit events for failures.

Pieces:

* :mod:`token_validation` — the closed-vocabulary :class:`TokenFailureCode`, bearer
  extraction, foreign (JWT-shaped) classification, and the :class:`TokenClassification`
  result (deterministic, never raises).
* :mod:`classifier` — :func:`classify_request`, which reuses the real ``AuthService`` and the
  existing ``OPERATION_ROLES`` policy to classify a credential for an operation.
* :mod:`responses` — :class:`AuthenticationFailure` + the FastAPI exception handlers that
  render controlled responses (no stack traces, no internal leakage).
* :mod:`readiness` — :func:`assess_security_readiness` + :class:`SecurityReadinessReport`.
"""

from __future__ import annotations

from .token_validation import (
    EXPECTED_AUDIENCE, EXPECTED_ISSUER, TokenClassification, TokenFailureCode,
    classify_structured_token, extract_bearer, http_status_for, is_wellformed_opaque,
    looks_like_jwt, message_for,
)
from .classifier import classify_request
from .responses import AuthenticationFailure, register_security_exception_handlers
from .readiness import SecurityReadinessReport, assess_security_readiness

__all__ = [
    "TokenFailureCode", "TokenClassification", "extract_bearer", "looks_like_jwt",
    "classify_structured_token", "is_wellformed_opaque", "http_status_for", "message_for",
    "EXPECTED_ISSUER", "EXPECTED_AUDIENCE",
    "classify_request",
    "AuthenticationFailure", "register_security_exception_handlers",
    "SecurityReadinessReport", "assess_security_readiness",
]
