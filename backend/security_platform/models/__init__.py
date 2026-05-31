"""Security Platform domain model (DRP5-B) — closed vocabularies + records."""

from __future__ import annotations

from .domain import (
    Role, Action, ResourceType, AccessDecision, PolicyEffect, PolicyStatus, CredentialStatus,
    SessionStatus, AuthOutcome, UserStatus, ReadinessClass, ReadinessDimension, EntityKind,
    SecurityIdentity, SecurityVersion, SecurityUserRecord, CredentialRecord, SessionRecord,
    AuthenticationRecord, AuthorizationRecord, SecurityPolicyRecord, SecurityValidationRecord,
    SecurityReadinessRecord, SecurityAuditRecord, SecurityLineageRecord, SecurityRegistryRecord,
    AccessControlRecord,
)

__all__ = [
    "Role", "Action", "ResourceType", "AccessDecision", "PolicyEffect", "PolicyStatus",
    "CredentialStatus", "SessionStatus", "AuthOutcome", "UserStatus", "ReadinessClass",
    "ReadinessDimension", "EntityKind", "SecurityIdentity", "SecurityVersion", "SecurityUserRecord",
    "CredentialRecord", "SessionRecord", "AuthenticationRecord", "AuthorizationRecord",
    "SecurityPolicyRecord", "SecurityValidationRecord", "SecurityReadinessRecord",
    "SecurityAuditRecord", "SecurityLineageRecord", "SecurityRegistryRecord", "AccessControlRecord",
]
