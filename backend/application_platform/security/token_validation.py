"""``backend/application_platform/security/token_validation.py`` — token validation
hardening (DBE5-C).

Deterministic, never-crashing classification of an inbound bearer credential into a
**closed vocabulary** of failure modes. This is *authentication reliability* hardening
over the existing operative auth (``backend.application_backend.auth.AuthService``); it is
**not** a new authentication framework and it issues no tokens. The platform's live tokens
remain opaque session tokens (64-hex); this module only *validates / classifies / rejects*
what arrives at the HTTP boundary so that a malicious or accidental invalid token can never
reach business logic (and therefore can never produce an HTTP 500).

Design rules (all enforced here):

* **Closed vocabulary.** Every invalid credential maps to exactly one
  :class:`TokenFailureCode`. There are no free-form failure strings.
* **Deterministic.** The same header + auth state always yields the same classification
  and the same human-readable message (no wall-clock, no randomness).
* **Never raises.** Any unexpected internal condition is contained as
  ``UNKNOWN_TOKEN_FAILURE`` (a controlled 401), never an exception.
* **Auditable / traceable.** The classification carries a token *fingerprint* (a hash,
  never the raw token) so a security event can reference it without leaking the secret.
"""

from __future__ import annotations

import base64
import json
import string
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from backend.application_backend.auth import token_fingerprint  # reuse (no reinvented crypto)
from backend.application_backend.version import TOKEN_BYTES


# =============================================================================
# Closed vocabulary (exactly the DBE-5 directive set; no free-form states)
# =============================================================================
class TokenFailureCode(str, Enum):
    """The closed set of authentication / authorization failure classifications."""

    MISSING_TOKEN = "MISSING_TOKEN"
    EMPTY_TOKEN = "EMPTY_TOKEN"
    MALFORMED_TOKEN = "MALFORMED_TOKEN"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    INVALID_ISSUER = "INVALID_ISSUER"
    INVALID_AUDIENCE = "INVALID_AUDIENCE"
    EXPIRED_TOKEN = "EXPIRED_TOKEN"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    UNKNOWN_TOKEN_FAILURE = "UNKNOWN_TOKEN_FAILURE"


# The only failure that is an *authorization* (403) outcome; everything else is 401.
_FORBIDDEN_CODES = frozenset({TokenFailureCode.FORBIDDEN})

# Static, deterministic human messages — never include the token, a stack trace, or any
# internal exception text (DBE5-D: no internal leakage).
_MESSAGES: dict[TokenFailureCode, str] = {
    TokenFailureCode.MISSING_TOKEN: "Authentication required: no bearer token was provided.",
    TokenFailureCode.EMPTY_TOKEN: "Authentication required: the bearer token was empty.",
    TokenFailureCode.MALFORMED_TOKEN: "The bearer token is malformed and cannot be parsed.",
    TokenFailureCode.INVALID_SIGNATURE: "The bearer token signature is invalid.",
    TokenFailureCode.INVALID_ISSUER: "The bearer token issuer is not recognized.",
    TokenFailureCode.INVALID_AUDIENCE: "The bearer token audience is not accepted.",
    TokenFailureCode.EXPIRED_TOKEN: "The session for this token has expired or been revoked.",
    TokenFailureCode.UNAUTHORIZED: "The bearer token does not correspond to an active session.",
    TokenFailureCode.FORBIDDEN: "Your role is not permitted to perform this operation.",
    TokenFailureCode.UNKNOWN_TOKEN_FAILURE: "The bearer token could not be validated.",
}

# This platform issues *opaque* session tokens, never JWTs. A JWT-shaped credential is
# therefore necessarily foreign/forged; these constants name what we would have to see to
# even consider one, so issuer/audience mismatches classify deterministically.
EXPECTED_ISSUER = "neurovision"
EXPECTED_AUDIENCE = "neurovision-application-api"

_HEX = set(string.hexdigits.lower())
_OPAQUE_TOKEN_LEN = 2 * TOKEN_BYTES  # hex chars in a live session token (64)


def http_status_for(code: TokenFailureCode) -> int:
    """Map a failure code to its controlled HTTP status (401 auth, 403 authorization)."""
    return 403 if code in _FORBIDDEN_CODES else 401


def message_for(code: TokenFailureCode) -> str:
    """Return the static, deterministic message for a failure code."""
    return _MESSAGES.get(code, _MESSAGES[TokenFailureCode.UNKNOWN_TOKEN_FAILURE])


# =============================================================================
# Bearer extraction
# =============================================================================
def extract_bearer(authorization: Optional[str]) -> tuple[bool, str]:
    """Parse an ``Authorization`` header into ``(present, token)`` — never raises.

    * ``present`` is ``False`` only when the header is absent / not a string.
    * A present header always yields ``present=True``; the token may be ``""`` (which the
      caller classifies as ``EMPTY_TOKEN``).
    * Accepts ``"Bearer <token>"`` (case-insensitive scheme) and, for backward
      compatibility with the prior endpoint behaviour, a raw token with no scheme.
    """
    if authorization is None or not isinstance(authorization, str):
        return False, ""
    if authorization.strip() == "":
        return True, ""  # header present but whitespace-only -> EMPTY_TOKEN
    low = authorization.lower()
    if low.startswith("bearer "):
        return True, authorization[7:].strip()
    if low == "bearer":
        return True, ""  # scheme with no token
    return True, authorization.strip()


# =============================================================================
# Structured (JWT-shaped) credential classification — foreign-token hardening
# =============================================================================
def looks_like_jwt(token: str) -> bool:
    """A compact JWS/JWT has exactly three non-empty ``.``-separated segments.

    Opaque session tokens are pure hex with no ``.``, so this never misfires on them.
    """
    if "." not in token:
        return False
    parts = token.split(".")
    return len(parts) == 3 and all(parts)


def _b64url_json(segment: str) -> Optional[dict]:
    """Best-effort base64url-decode of a JWT segment into a JSON object; ``None`` on any
    failure (so malformed structured tokens classify as ``MALFORMED_TOKEN``)."""
    try:
        padded = segment + "=" * (-len(segment) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        obj = json.loads(raw.decode("utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:  # noqa: BLE001 — any decode error => malformed (never raise)
        return None


def classify_structured_token(token: str) -> TokenFailureCode:
    """Classify a JWT-shaped (foreign) credential deterministically.

    The platform never issues JWTs, so a structurally valid JWT is necessarily foreign:
    we check issuer then audience (so a forged claim set is reported precisely) and
    otherwise report an invalid signature. Order is fixed for determinism + testability.
    """
    header_seg, payload_seg, signature_seg = token.split(".")
    header = _b64url_json(header_seg)
    payload = _b64url_json(payload_seg)
    if header is None or payload is None or not signature_seg:
        return TokenFailureCode.MALFORMED_TOKEN
    if payload.get("iss") != EXPECTED_ISSUER:
        return TokenFailureCode.INVALID_ISSUER
    if payload.get("aud") != EXPECTED_AUDIENCE:
        return TokenFailureCode.INVALID_AUDIENCE
    # Well-formed JWT claiming our issuer + audience — but we never signed it.
    return TokenFailureCode.INVALID_SIGNATURE


def is_wellformed_opaque(token: str) -> bool:
    """True iff ``token`` has the exact shape of a live opaque session token (64 lower-hex)."""
    return len(token) == _OPAQUE_TOKEN_LEN and all(c in _HEX for c in token.lower())


# =============================================================================
# Classification result
# =============================================================================
@dataclass(frozen=True)
class TokenClassification:
    """The deterministic outcome of validating a bearer credential for an operation.

    ``ok`` means *authenticated and authorized*; otherwise ``code`` is the closed-vocabulary
    reason and ``http_status`` is the controlled response status (401 or 403).
    """

    code: Optional[TokenFailureCode]
    token: str = ""
    session: object = None
    user: object = None
    operation: str = ""

    @property
    def ok(self) -> bool:
        return self.code is None

    @property
    def http_status(self) -> int:
        return 200 if self.code is None else http_status_for(self.code)

    @property
    def message(self) -> str:
        return "" if self.code is None else message_for(self.code)

    @property
    def token_fingerprint(self) -> Optional[str]:
        """A hash of the token (never the raw token) for auditing; ``None`` when no token."""
        if not self.token:
            return None
        try:
            return token_fingerprint(self.token)
        except Exception:  # noqa: BLE001
            return None

    def to_response_body(self) -> dict:
        """The deterministic, leakage-free JSON body for a failed classification (DBE5-D)."""
        status = self.http_status
        return {
            "error": "forbidden" if status == 403 else "unauthorized",
            "code": self.code.value if self.code else None,
            "message": self.message,
            "status": status,
            "operation": self.operation,
        }


__all__ = [
    "TokenFailureCode", "TokenClassification", "extract_bearer", "looks_like_jwt",
    "classify_structured_token", "is_wellformed_opaque", "http_status_for", "message_for",
    "EXPECTED_ISSUER", "EXPECTED_AUDIENCE",
]
