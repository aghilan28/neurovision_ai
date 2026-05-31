"""``backend/security_platform`` — Security Hardening & Access Control Platform (DRP-5).

Closes the audit's *insufficient security readiness* blocker: turns the persistent platform
into a **secure platform** with authentication, authorization, access control, credential
protection, security auditing, and security validation. The scope is *security* and nothing
else:

    authenticate users -> authorize requests -> evaluate policies -> control access ->
    audit security events -> track security lineage -> score security readiness

No model / training / inference / serving / persistence / deployment / monitoring changes
(all out of scope) — it secures the platform without changing business logic.

Built strictly on the existing platform: it **reuses** the PBKDF2 hashing + injectable
entropy primitives (``backend.application_backend.auth``), the shared ``ml.lineage`` tracker,
and the shared ``ImmutableAuditLog`` (no parallel audit/lineage systems). A resource-access
record's lineage parents the access decision, which parents the authorization, which parents
the authentication, which parents the credential, which parents the user — so a single
``verify_chain`` proves

    User -> Credential -> Authentication -> Authorization -> Access Decision -> Resource Access

(and, when the accessed resource exposes a lineage node, additionally reaches the patient).

Boundary (NR-8): part of the ``backend`` Application layer. Imports ``ml`` + sibling
``backend`` only; never ``frontend``. No plaintext credential storage; secrets never enter a
content hash, report, or the audit/lineage trail. Tests live in the repository-root ``tests/``
(``tests/test_security_platform*.py``).
"""

from __future__ import annotations

from .version import (
    SECURITY_PLATFORM_VERSION, SECURITY_DOMAIN_VERSION, SECURITY_IDENTITY_VERSION,
    SECURITY_AUTHENTICATION_VERSION, SECURITY_AUTHORIZATION_VERSION, SECURITY_CREDENTIAL_VERSION,
    SECURITY_ACCESS_CONTROL_VERSION, SECURITY_POLICY_VERSION, SECURITY_REGISTRY_VERSION,
    SECURITY_READINESS_VERSION, SECURITY_AUDIT_VERSION, SECURITY_LINEAGE_VERSION,
    SECURITY_VALIDATION_VERSION, SECURITY_REPORT_VERSION,
)
from .models import (
    Role, Action, ResourceType, AccessDecision, PolicyEffect, PolicyStatus, CredentialStatus,
    SessionStatus, AuthOutcome, UserStatus, ReadinessClass, ReadinessDimension, EntityKind,
    SecurityIdentity, SecurityVersion, SecurityUserRecord, CredentialRecord, SessionRecord,
    AuthenticationRecord, AuthorizationRecord, SecurityPolicyRecord, SecurityValidationRecord,
    SecurityReadinessRecord, SecurityAuditRecord, SecurityLineageRecord, SecurityRegistryRecord,
    AccessControlRecord,
)
from .identity import Identity, IdentityError, mint_identity, validate_identity
from .credentials import CredentialManager, CredentialError
from .authentication import AuthenticationEngine
from .authorization import AuthorizationEngine
from .access_control import AccessControlEngine, AccessOutcome, PROTECTED_RESOURCES
from .policies import PolicyEngine, PolicyError
from .registry import SecurityRegistry, RegistryError
from .readiness import SecurityReadinessEngine
from .validation import SecurityContentValidator, SecurityIntegrityValidator
from .audit import make_security_audit_log, ImmutableAuditLog, AuditError
from .lineage import (
    make_user_lineage, make_credential_lineage, make_authentication_lineage,
    make_authorization_lineage, make_access_decision_lineage, make_resource_access_lineage,
)
from .schemas import ENTITY_CONTRACTS, validate_entity
from .service import SecurityPlatformService, SecurityOutcome, SecurityPlatformError

__all__ = [
    # versions
    "SECURITY_PLATFORM_VERSION", "SECURITY_DOMAIN_VERSION", "SECURITY_IDENTITY_VERSION",
    "SECURITY_AUTHENTICATION_VERSION", "SECURITY_AUTHORIZATION_VERSION", "SECURITY_CREDENTIAL_VERSION",
    "SECURITY_ACCESS_CONTROL_VERSION", "SECURITY_POLICY_VERSION", "SECURITY_REGISTRY_VERSION",
    "SECURITY_READINESS_VERSION", "SECURITY_AUDIT_VERSION", "SECURITY_LINEAGE_VERSION",
    "SECURITY_VALIDATION_VERSION", "SECURITY_REPORT_VERSION",
    # models / vocab
    "Role", "Action", "ResourceType", "AccessDecision", "PolicyEffect", "PolicyStatus",
    "CredentialStatus", "SessionStatus", "AuthOutcome", "UserStatus", "ReadinessClass",
    "ReadinessDimension", "EntityKind", "SecurityIdentity", "SecurityVersion", "SecurityUserRecord",
    "CredentialRecord", "SessionRecord", "AuthenticationRecord", "AuthorizationRecord",
    "SecurityPolicyRecord", "SecurityValidationRecord", "SecurityReadinessRecord",
    "SecurityAuditRecord", "SecurityLineageRecord", "SecurityRegistryRecord", "AccessControlRecord",
    # identity / engines
    "Identity", "IdentityError", "mint_identity", "validate_identity", "CredentialManager",
    "CredentialError", "AuthenticationEngine", "AuthorizationEngine", "AccessControlEngine",
    "AccessOutcome", "PROTECTED_RESOURCES", "PolicyEngine", "PolicyError",
    # registry / readiness / validation / audit / lineage / schemas
    "SecurityRegistry", "RegistryError", "SecurityReadinessEngine", "SecurityContentValidator",
    "SecurityIntegrityValidator", "make_security_audit_log", "ImmutableAuditLog", "AuditError",
    "make_user_lineage", "make_credential_lineage", "make_authentication_lineage",
    "make_authorization_lineage", "make_access_decision_lineage", "make_resource_access_lineage",
    "ENTITY_CONTRACTS", "validate_entity",
    # service
    "SecurityPlatformService", "SecurityOutcome", "SecurityPlatformError",
]
