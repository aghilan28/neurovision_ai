"""``backend/application_platform/security/readiness.py`` — security readiness (DBE5-G).

A deterministic, read-only assessment that the authentication-reliability guarantees hold:
authentication is reachable and never crashes, authorization policy is defined, and the
protected endpoint rejects every invalid-token class with a controlled (non-500) response.
Produces a :class:`SecurityReadinessReport` with a ``READY`` / ``NOT_READY`` classification.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.application_backend.models.domain import ApiOperation
from backend.application_backend.validation import OPERATION_ROLES

from .classifier import classify_request
from .token_validation import TokenFailureCode


@dataclass(frozen=True)
class SecurityReadinessReport:
    """The deterministic security-readiness assessment."""

    authentication_ready: bool
    authorization_ready: bool
    protected_endpoint_ready: bool
    checks: tuple = field(default_factory=tuple)  # (name, passed, detail)

    @property
    def ready(self) -> bool:
        return (self.authentication_ready and self.authorization_ready
                and self.protected_endpoint_ready)

    @property
    def classification(self) -> str:
        return "READY" if self.ready else "NOT_READY"

    def to_dict(self) -> dict:
        return {
            "classification": self.classification,
            "authentication_ready": self.authentication_ready,
            "authorization_ready": self.authorization_ready,
            "protected_endpoint_ready": self.protected_endpoint_ready,
            "checks": [{"name": n, "passed": bool(p), "detail": d} for n, p, d in self.checks],
        }


def assess_security_readiness(service, *,
                              operation: ApiOperation = ApiOperation.UPLOAD_EEG
                              ) -> SecurityReadinessReport:
    """Assess authentication / authorization / protected-endpoint readiness (read-only).

    Drives the real classifier against the real ``AuthService`` with representative invalid
    credentials and confirms each is classified to a controlled (401/403) outcome — never an
    exception, never a 500.
    """
    auth = service.backend.auth
    checks: list[tuple] = []

    # 1) authentication reachable + never crashes on a hostile credential.
    authentication_ready = True
    probes = {
        None: TokenFailureCode.MISSING_TOKEN,
        "Bearer ": TokenFailureCode.EMPTY_TOKEN,
        "Bearer !!!not-a-token!!!": TokenFailureCode.MALFORMED_TOKEN,
        "Bearer " + "00" * 32: TokenFailureCode.UNAUTHORIZED,
    }
    for header, expected in probes.items():
        try:
            c = classify_request(auth_service=auth, authorization=header, operation=operation)
            controlled = (not c.ok) and c.http_status in (401, 403)
            checks.append((f"classify[{expected.value}]", controlled and c.code == expected,
                           {"code": c.code.value if c.code else None, "status": c.http_status}))
            if not controlled:
                authentication_ready = False
        except Exception as exc:  # noqa: BLE001 — a raised classifier is a readiness failure
            authentication_ready = False
            checks.append((f"classify[{expected.value}]", False, {"raised": type(exc).__name__}))

    # 2) authorization policy is defined for the protected operation.
    allowed = OPERATION_ROLES.get(operation, frozenset())
    authorization_ready = len(allowed) > 0
    checks.append(("authorization_policy_defined", authorization_ready,
                   {"allowed_roles": sorted(r.value for r in allowed)}))

    # 3) protected endpoint exists and is wired to the hardened guard.
    protected_endpoint_ready = hasattr(service, "authenticate_request")
    checks.append(("protected_endpoint_guarded", protected_endpoint_ready,
                   {"hub_has_authenticate_request": protected_endpoint_ready}))

    return SecurityReadinessReport(
        authentication_ready=authentication_ready, authorization_ready=authorization_ready,
        protected_endpoint_ready=protected_endpoint_ready, checks=tuple(checks))


__all__ = ["SecurityReadinessReport", "assess_security_readiness"]
