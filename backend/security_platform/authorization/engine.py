"""Authorization engine (DRP5-D).

Role-Based Access Control with **explicit permissions only** and **default deny**: it asks
the policy engine whether the user's role may perform an action on a resource type, and emits
a traceable :class:`AuthorizationRecord` carrying the decision, the matched policies, and the
reason.
"""

from __future__ import annotations

from ..identity import mint_identity
from ..models.domain import (
    Action, AuthorizationRecord, ResourceType, Role,
)
from ..policies import PolicyEngine
from ..version import DETERMINISTIC_EPOCH


class AuthorizationEngine:
    """Evaluates RBAC permissions via the policy engine (default-deny)."""

    def authorize(self, *, authentication_id: str, user_id: str, role: Role,
                  resource_type: ResourceType, resource_id: str, action: Action,
                  policy_engine: PolicyEngine,
                  created_at: str = DETERMINISTIC_EPOCH) -> AuthorizationRecord:
        decision, matched, reason = policy_engine.evaluate(role, resource_type, action)
        authorization_id = mint_identity("authorization", {
            "authentication_id": authentication_id, "resource_id": resource_id,
            "action": action.value, "decision": decision.value}).id
        return AuthorizationRecord(
            authorization_id=authorization_id, user_id=user_id, role=role,
            resource_type=resource_type, resource_id=resource_id, action=action, decision=decision,
            matched_policies=matched, reason=reason, created_at=created_at)


__all__ = ["AuthorizationEngine"]
