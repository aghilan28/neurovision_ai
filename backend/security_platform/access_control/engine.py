"""Access control platform (DRP5-E).

Controls access to the protected resource types — dataset / model / serving / persistence /
administrative — enforcing **least privilege**: access is permitted only when the session is
valid **and** authorization permits it (default-deny everywhere else). Deterministic and
auditable; the engine returns a final decision + reason that the service records.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models.domain import AccessDecision, AuthorizationRecord, ResourceType


# the protected resource types this platform controls (DRP5-E)
PROTECTED_RESOURCES: tuple[ResourceType, ...] = (
    ResourceType.DATASET, ResourceType.MODEL, ResourceType.SERVING, ResourceType.PERSISTENCE,
    ResourceType.ADMINISTRATIVE,
)


@dataclass(frozen=True)
class AccessOutcome:
    decision: AccessDecision
    reason: str


class AccessControlEngine:
    """Combines session validity + authorization into a final least-privilege access decision."""

    def control(self, *, session_valid: bool, session_reason: str,
                authorization: AuthorizationRecord) -> AccessOutcome:
        if authorization.resource_type not in PROTECTED_RESOURCES:  # defensive (closed vocab)
            return AccessOutcome(AccessDecision.DENIED, "unprotected resource type")
        if not session_valid:
            return AccessOutcome(AccessDecision.DENIED, f"session_{session_reason}")
        if authorization.decision != AccessDecision.PERMITTED:
            return AccessOutcome(AccessDecision.DENIED, authorization.reason)
        return AccessOutcome(AccessDecision.PERMITTED, "least-privilege grant")


__all__ = ["AccessControlEngine", "AccessOutcome", "PROTECTED_RESOURCES"]
