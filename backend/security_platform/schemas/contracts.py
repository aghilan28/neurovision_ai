"""Entity contracts for the Security domain (DRP5-M; no undocumented objects).

For each entity: Schema (required fields) · Validation Rules · Lineage Rule · Audit Rule.
``validate_entity`` checks an entity's serialized form against its schema. Mirrors
``backend.persistence_platform.schemas.contracts``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    SECURITY_DOMAIN_VERSION, SECURITY_IDENTITY_VERSION, SECURITY_CREDENTIAL_VERSION,
    SECURITY_AUTHENTICATION_VERSION, SECURITY_AUTHORIZATION_VERSION, SECURITY_POLICY_VERSION,
    SECURITY_REGISTRY_VERSION, SECURITY_AUDIT_VERSION, SECURITY_LINEAGE_VERSION,
    SECURITY_VALIDATION_VERSION, SECURITY_READINESS_VERSION, SECURITY_REPORT_VERSION,
)


@dataclass(frozen=True)
class EntityContract:
    name: str
    version: str
    required_fields: tuple[str, ...]
    validation_rules: tuple[str, ...]
    lineage_rule: str
    audit_rule: str

    def to_dict(self) -> dict:
        return {
            "name": self.name, "version": self.version,
            "required_fields": list(self.required_fields),
            "validation_rules": list(self.validation_rules),
            "lineage_rule": self.lineage_rule, "audit_rule": self.audit_rule,
        }


ENTITY_CONTRACTS: dict[str, EntityContract] = {
    "SecurityUserRecord": EntityContract(
        "SecurityUserRecord", SECURITY_DOMAIN_VERSION, ("user_id", "username", "role", "status"),
        ("role + status are closed vocabularies",), "user node is the lineage root",
        "user creation audited"),
    "CredentialRecord": EntityContract(
        "CredentialRecord", SECURITY_CREDENTIAL_VERSION,
        ("credential_id", "user_id", "algorithm", "iterations", "salt_hex", "hash_hex", "status"),
        ("salted PBKDF2-HMAC-SHA256; stores hash + salt, NEVER plaintext",
         "content signature excludes plaintext"),
        "credential node parents the user node", "credential events audited"),
    "SessionRecord": EntityContract(
        "SessionRecord", SECURITY_DOMAIN_VERSION,
        ("session_id", "user_id", "credential_id", "token_fingerprint", "status", "ttl_steps"),
        ("stores a token fingerprint, NEVER the raw token",
         "expiry is a deterministic logical-step window (no wall-clock)"),
        "session derives from the credential", "session events audited"),
    "AuthenticationRecord": EntityContract(
        "AuthenticationRecord", SECURITY_AUTHENTICATION_VERSION,
        ("authentication_id", "user_id", "credential_id", "outcome"),
        ("outcome in {success, failure}; never raises on bad password",),
        "authentication node parents the credential node", "authentication events audited"),
    "AuthorizationRecord": EntityContract(
        "AuthorizationRecord", SECURITY_AUTHORIZATION_VERSION,
        ("authorization_id", "user_id", "role", "resource_type", "resource_id", "action",
         "decision"),
        ("RBAC, explicit permissions only, default-deny",
         "a PERMITTED decision cites >= 1 matched policy"),
        "authorization node parents the authentication node", "authorization events audited"),
    "SecurityPolicyRecord": EntityContract(
        "SecurityPolicyRecord", SECURITY_POLICY_VERSION,
        ("policy_id", "name", "role", "resource_type", "action", "effect", "status", "version"),
        ("declarative (role, resource_type, action) -> effect; version-aware",),
        "n/a", "policy events audited"),
    "AccessControlRecord": EntityContract(
        "AccessControlRecord", SECURITY_DOMAIN_VERSION,
        ("identity", "user_id", "role", "credential_id", "session_id", "authentication_id",
         "authorization_id", "resource_type", "resource_id", "action", "decision", "validation",
         "readiness_id", "version"),
        ("immutable (frozen) once decided", "least privilege; default-deny",
         "binds user + credential + auth + authz + decision + resource"),
        "resource-access node parents the access-decision node "
        "(User -> ... -> Resource Access)", "every security event audited"),
    "SecurityValidationRecord": EntityContract(
        "SecurityValidationRecord", SECURITY_VALIDATION_VERSION, ("validation_id", "ok", "checks"),
        ("checks: credential/session/authorization/policy",
         "structured (name, passed, detail); never exceptions; never echoes secrets"),
        "n/a", "validation recorded in the audit trail"),
    "SecurityReadinessRecord": EntityContract(
        "SecurityReadinessRecord", SECURITY_READINESS_VERSION,
        ("readiness_id", "target_id", "score", "classification", "dimensions"),
        ("seven dimensions (authn/authz/policy/registry/audit/lineage/validation)",
         "READY requires all present + validation passes"),
        "n/a", "readiness audited"),
    "SecurityRegistryRecord": EntityContract(
        "SecurityRegistryRecord", SECURITY_REGISTRY_VERSION,
        ("access_id", "user_id", "session_id", "authentication_id", "authorization_id",
         "resource_type", "resource_id", "action", "decision", "version", "lineage_id"),
        ("no access exists outside the registry; no orphans; silent overwrite forbidden",),
        "lineage_id references the resource-access node", "registry changes audited"),
    "SecurityAuditRecord": EntityContract(
        "SecurityAuditRecord", SECURITY_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links to the previous event (chain)"),
        "n/a", "immutable; append-only; tamper-evident (shared ImmutableAuditLog)"),
    "SecurityLineageRecord": EntityContract(
        "SecurityLineageRecord", SECURITY_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "parents reference the upstream lineage node", "lineage event audited"),
    "SecurityIdentity": EntityContract(
        "SecurityIdentity", SECURITY_IDENTITY_VERSION,
        ("access_id", "user_id", "session_id", "authentication_id", "authorization_id"),
        ("access_id matches /^access_control\\+[0-9a-f]{16}$/",), "anchors the access record",
        "minted-once; never modified"),
    "SecurityReport": EntityContract(
        "SecurityReport", SECURITY_REPORT_VERSION, ("report_type", "security_report_version"),
        ("deterministic; reproducible; never echoes secret material",), "n/a", "n/a"),
}


def contract_for(name: str) -> EntityContract:
    if name not in ENTITY_CONTRACTS:
        raise KeyError(f"no contract for entity {name!r}")
    return ENTITY_CONTRACTS[name]


def validate_entity(name: str, entity_dict: dict) -> tuple[bool, list]:
    """Check an entity's serialized form against its contract's required fields."""
    contract = contract_for(name)
    missing = [f for f in contract.required_fields
               if f not in entity_dict or entity_dict[f] in (None, "")]
    return (len(missing) == 0), missing


__all__ = ["EntityContract", "ENTITY_CONTRACTS", "contract_for", "validate_entity"]
