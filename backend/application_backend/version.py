"""Version identities for the Application Backend Platform (Productization P6).

Every application artifact (user, session, upload, request, response, workflow,
analysis, api, registry record, audit event, lineage node, validation record, report)
records the exact versions that produced it, so it is reproducible and auditable for
its entire lifetime (AP-5/AP-6/AP-9, NR-10/NR-11). Bump a version when the named
behaviour or contract changes.

Mirrors ``backend.inference_foundation.version`` so the application layer speaks the
same versioning language as the rest of the platform.
"""

from __future__ import annotations

# The application-backend subsystem as a whole.
APPLICATION_BACKEND_VERSION: str = "application-backend@1.0.0"

# Component versions.
APPLICATION_DOMAIN_VERSION: str = "application-domain@1.0.0"
APPLICATION_IDENTITY_VERSION: str = "application-identity@1.0.0"
APPLICATION_AUTH_VERSION: str = "application-auth@1.0.0"
APPLICATION_USERS_VERSION: str = "application-users@1.0.0"
APPLICATION_WORKFLOW_VERSION: str = "application-workflow@1.0.0"
APPLICATION_API_VERSION: str = "application-api@1.0.0"
APPLICATION_STORAGE_VERSION: str = "application-storage@1.0.0"
APPLICATION_REGISTRY_VERSION: str = "application-registry@1.0.0"
APPLICATION_AUDIT_VERSION: str = "application-audit@1.0.0"
APPLICATION_LINEAGE_VERSION: str = "application-lineage@1.0.0"
APPLICATION_VALIDATION_VERSION: str = "application-validation@1.0.0"
APPLICATION_REPORT_VERSION: str = "application-report@1.0.0"

# The public, versioned API surface tag (the only API version this phase serves).
API_V1: str = "v1"

# Fixed, deterministic default timestamp for "created_at" fields that must NOT
# perturb reproducibility hashes (mirrors the rest of the platform).
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"

# Float quantization (decimals) applied before fingerprinting any scalar so a
# record's content id is stable for identical inputs (NR-10).
FINGERPRINT_DECIMALS: int = 9

# Password-hashing parameters (secure defaults). The salt + token entropy is the
# only non-deterministic input in the subsystem (secure by default, injectable for
# deterministic tests); it never enters a reproducibility/content hash.
PBKDF2_ITERATIONS: int = 200_000
SALT_BYTES: int = 16
TOKEN_BYTES: int = 32
