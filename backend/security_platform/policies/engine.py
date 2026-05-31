"""Security policy engine (DRP5-F).

Registers, evaluates, validates, and versions security policies. A policy is declarative data
``(role, resource_type, action) -> effect`` (ALLOW/DENY). Evaluation is **default-deny**: a
DENY match denies; otherwise an ALLOW match permits; **no match denies**. Deterministic and
version-aware (every policy is content-addressed).
"""

from __future__ import annotations

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..identity import mint_identity
from ..models.domain import (
    Action, AccessDecision, PolicyEffect, PolicyStatus, ResourceType, Role, SecurityPolicyRecord,
)
from ..version import DETERMINISTIC_EPOCH


class PolicyError(ValueError):
    """Raised on an invalid policy registration."""


class PolicyEngine:
    """An in-memory registry + evaluator of declarative RBAC policies (default-deny)."""

    def __init__(self) -> None:
        self._policies: dict[str, SecurityPolicyRecord] = {}

    # --- registration ---------------------------------------------------------
    def register(self, name: str, role: Role, resource_type: ResourceType, action: Action,
                 effect: PolicyEffect, *, created_at: str = DETERMINISTIC_EPOCH) -> SecurityPolicyRecord:
        version = hash_obj({"name": name, "role": role.value, "resource_type": resource_type.value,
                            "action": action.value, "effect": effect.value})
        policy_id = mint_identity("security_policy", {
            "name": name, "role": role.value, "resource_type": resource_type.value,
            "action": action.value, "effect": effect.value}).id
        record = SecurityPolicyRecord(
            policy_id=policy_id, name=name, role=role, resource_type=resource_type, action=action,
            effect=effect, status=PolicyStatus.ACTIVE, version=version, created_at=created_at)
        self._policies[policy_id] = record
        return record

    def install_default_policies(self, *, created_at: str = DETERMINISTIC_EPOCH) -> list:
        """A least-privilege default policy set across the protected resource types."""
        defaults = [
            ("admin_all_administrative", Role.ADMIN, ResourceType.ADMINISTRATIVE, Action.ADMINISTER,
             PolicyEffect.ALLOW),
            ("engineer_read_model", Role.ENGINEER, ResourceType.MODEL, Action.READ, PolicyEffect.ALLOW),
            ("engineer_execute_serving", Role.ENGINEER, ResourceType.SERVING, Action.EXECUTE,
             PolicyEffect.ALLOW),
            ("engineer_read_persistence", Role.ENGINEER, ResourceType.PERSISTENCE, Action.READ,
             PolicyEffect.ALLOW),
            ("researcher_read_dataset", Role.RESEARCHER, ResourceType.DATASET, Action.READ,
             PolicyEffect.ALLOW),
            ("researcher_execute_serving", Role.RESEARCHER, ResourceType.SERVING, Action.EXECUTE,
             PolicyEffect.ALLOW),
            ("service_execute_serving", Role.SERVICE, ResourceType.SERVING, Action.EXECUTE,
             PolicyEffect.ALLOW),
            ("auditor_read_persistence", Role.AUDITOR, ResourceType.PERSISTENCE, Action.READ,
             PolicyEffect.ALLOW),
            ("auditor_read_administrative", Role.AUDITOR, ResourceType.ADMINISTRATIVE, Action.READ,
             PolicyEffect.ALLOW),
            # an explicit prohibition: non-admins may never administer
            ("deny_researcher_admin", Role.RESEARCHER, ResourceType.ADMINISTRATIVE, Action.ADMINISTER,
             PolicyEffect.DENY),
        ]
        return [self.register(*d, created_at=created_at) for d in defaults]

    # --- evaluation (default-deny) -------------------------------------------
    def evaluate(self, role: Role, resource_type: ResourceType, action: Action
                 ) -> tuple[AccessDecision, tuple[str, ...], str]:
        matches = [p for p in self._active()
                   if p.role == role and p.resource_type == resource_type and p.action == action]
        denies = [p for p in matches if p.effect == PolicyEffect.DENY]
        allows = [p for p in matches if p.effect == PolicyEffect.ALLOW]
        if denies:
            return (AccessDecision.DENIED, tuple(sorted(p.policy_id for p in denies)),
                    "explicit deny policy")
        if allows:
            return (AccessDecision.PERMITTED, tuple(sorted(p.policy_id for p in allows)),
                    "explicit allow policy")
        return (AccessDecision.DENIED, (), "default deny (no matching allow policy)")

    # --- accessors ------------------------------------------------------------
    def _active(self) -> list:
        return [p for p in self._policies.values() if p.status == PolicyStatus.ACTIVE]

    def get(self, policy_id: str) -> SecurityPolicyRecord:
        return self._policies[policy_id]

    def list_policies(self) -> list[str]:
        return sorted(self._policies)

    def validate(self) -> tuple[bool, list]:
        """Every policy is well-formed (closed vocabularies + a version)."""
        problems = []
        for pid, p in self._policies.items():
            if not p.version or p.effect not in (PolicyEffect.ALLOW, PolicyEffect.DENY):
                problems.append(pid)
        return (len(problems) == 0), problems

    def to_dict(self) -> dict:
        return {"n_policies": len(self._policies),
                "policies": {p: r.to_dict() for p, r in sorted(self._policies.items())}}


__all__ = ["PolicyEngine", "PolicyError"]
