"""Version identities for the Security Hardening & Access Control Platform (DRP-5).

Every security artifact (user, credential, authentication, authorization, access decision,
policy, validation, readiness, registry, audit, lineage, report) records the exact versions
that produced it, so a security decision is reproducible and auditable for its entire
lifetime (AP-5/AP-6/AP-9, NR-10/NR-11). Bump a version when the named behaviour or contract
changes.

Mirrors ``backend.persistence_platform.version`` so the security layer speaks the same
versioning language as the rest of the platform (NR-6).
"""

from __future__ import annotations

# The security platform as a whole.
SECURITY_PLATFORM_VERSION: str = "security-platform@1.0.0"

# Component versions.
SECURITY_DOMAIN_VERSION: str = "security-domain@1.0.0"
SECURITY_IDENTITY_VERSION: str = "security-identity@1.0.0"
SECURITY_AUTHENTICATION_VERSION: str = "security-authentication@1.0.0"
SECURITY_AUTHORIZATION_VERSION: str = "security-authorization@1.0.0"
SECURITY_CREDENTIAL_VERSION: str = "security-credential@1.0.0"
SECURITY_ACCESS_CONTROL_VERSION: str = "security-access-control@1.0.0"
SECURITY_POLICY_VERSION: str = "security-policy@1.0.0"
SECURITY_REGISTRY_VERSION: str = "security-registry@1.0.0"
SECURITY_READINESS_VERSION: str = "security-readiness@1.0.0"
SECURITY_AUDIT_VERSION: str = "security-audit@1.0.0"
SECURITY_LINEAGE_VERSION: str = "security-lineage@1.0.0"
SECURITY_VALIDATION_VERSION: str = "security-validation@1.0.0"
SECURITY_REPORT_VERSION: str = "security-report@1.0.0"

# Fixed, deterministic default "created_at" for fields that must NOT perturb
# reproducibility hashes (mirrors the rest of the platform).
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"

# Salt + token byte widths (secrets; never enter a content hash).
SALT_BYTES: int = 16
SESSION_TOKEN_BYTES: int = 32

# Default logical session lifetime, measured in deterministic logical steps (NOT wall-clock).
DEFAULT_SESSION_TTL_STEPS: int = 1000
