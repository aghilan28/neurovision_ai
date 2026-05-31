"""``backend/application_platform/security/responses.py`` — controlled authentication
responses (DBE5-D).

Translates a failed :class:`TokenClassification` into a **controlled HTTP response** — 401
Unauthorized or 403 Forbidden — with a deterministic, leakage-free JSON body. Registers
FastAPI exception handlers so that:

* an :class:`AuthenticationFailure` (raised at the hardened boundary) renders the controlled
  body, and
* any ``application_backend.auth.AuthError`` that might surface from anywhere is contained as
  a controlled 401 (defense-in-depth) instead of escaping as an HTTP 500.

No stack traces, no internal exception text, and no token material ever reach the client.
"""

from __future__ import annotations

from .token_validation import TokenClassification, TokenFailureCode, message_for


class AuthenticationFailure(Exception):
    """A controlled authentication/authorization failure carrying a classification.

    Raised by hardened endpoints; rendered to a 401/403 by the registered handler. It is
    never an internal server error.
    """

    def __init__(self, classification: TokenClassification):
        self.classification = classification
        super().__init__(classification.code.value if classification.code
                         else "AUTHENTICATION_FAILURE")

    @property
    def status_code(self) -> int:
        return self.classification.http_status

    def to_body(self) -> dict:
        return self.classification.to_response_body()


def register_security_exception_handlers(app) -> None:
    """Install the controlled-response handlers on a FastAPI app (idempotent per app)."""
    from fastapi.responses import JSONResponse

    @app.exception_handler(AuthenticationFailure)
    async def _on_auth_failure(_request, exc: AuthenticationFailure):  # noqa: ANN001
        return JSONResponse(status_code=exc.status_code, content=exc.to_body())

    # Defense-in-depth: a bare AuthError (by definition an authentication failure) must never
    # become a 500. Render it as a controlled, generic 401 (no internal text leaked).
    try:
        from backend.application_backend.auth import AuthError
    except Exception:  # noqa: BLE001 - if unavailable, skip (the boundary guard still applies)
        AuthError = None  # type: ignore

    if AuthError is not None:
        @app.exception_handler(AuthError)
        async def _on_auth_error(_request, _exc):  # noqa: ANN001
            code = TokenFailureCode.UNAUTHORIZED
            return JSONResponse(status_code=401, content={
                "error": "unauthorized", "code": code.value,
                "message": message_for(code), "status": 401, "operation": ""})


__all__ = ["AuthenticationFailure", "register_security_exception_handlers"]
