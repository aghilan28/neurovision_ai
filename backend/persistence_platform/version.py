"""Version identities for the Persistence Platform (DRP-4).

Every persistence artifact (storage record, repository, registry/audit/lineage/execution
snapshot, persistence record, recovery event, validation, readiness, report) records the
exact versions that produced it, so a persisted + recovered platform state is reproducible
and auditable for its entire lifetime (AP-5/AP-6/AP-9, NR-10/NR-11). Bump a version when the
named behaviour or contract changes.

Mirrors ``backend.serving_platform.version`` so the persistence layer speaks the same
versioning language as the rest of the platform (NR-6).
"""

from __future__ import annotations

# The persistence platform as a whole.
PERSISTENCE_PLATFORM_VERSION: str = "persistence-platform@1.0.0"

# Component versions.
PERSISTENCE_DOMAIN_VERSION: str = "persistence-domain@1.0.0"
PERSISTENCE_IDENTITY_VERSION: str = "persistence-identity@1.0.0"
PERSISTENCE_STORAGE_VERSION: str = "persistence-storage@1.0.0"
PERSISTENCE_REPOSITORY_VERSION: str = "persistence-repository@1.0.0"
PERSISTENCE_REGISTRY_STORAGE_VERSION: str = "persistence-registry-storage@1.0.0"
PERSISTENCE_AUDIT_STORAGE_VERSION: str = "persistence-audit-storage@1.0.0"
PERSISTENCE_LINEAGE_STORAGE_VERSION: str = "persistence-lineage-storage@1.0.0"
PERSISTENCE_EXECUTION_STORAGE_VERSION: str = "persistence-execution-storage@1.0.0"
PERSISTENCE_RECOVERY_VERSION: str = "persistence-recovery@1.0.0"
PERSISTENCE_VALIDATION_VERSION: str = "persistence-validation@1.0.0"
PERSISTENCE_READINESS_VERSION: str = "persistence-readiness@1.0.0"
PERSISTENCE_AUDIT_VERSION: str = "persistence-audit@1.0.0"
PERSISTENCE_LINEAGE_VERSION: str = "persistence-lineage@1.0.0"
PERSISTENCE_REPORT_VERSION: str = "persistence-report@1.0.0"

# Fixed, deterministic default timestamp for "created_at" fields that must NOT
# perturb reproducibility hashes (mirrors the rest of the platform).
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"

# Float quantization (decimals) applied before fingerprinting so an artifact's content id
# is stable for identical inputs (NR-10).
FINGERPRINT_DECIMALS: int = 9
