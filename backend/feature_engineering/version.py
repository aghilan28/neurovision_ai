"""Version identities for the Feature Engineering Platform (Productization P3).

Every feature-engineering artifact (feature asset, feature vector, metadata,
registry record, audit event, lineage node, validation record, report) records the
exact versions that produced it, so a feature asset is reproducible and auditable
for its entire lifetime (AP-5/AP-6/AP-9, NR-10/NR-11). Bump a version when the named
behaviour or contract changes.

Mirrors ``backend.signal_processing.version`` / ``backend.eeg_foundation.version`` so
the feature layer speaks the same versioning language as the rest of the platform.
"""

from __future__ import annotations

# The feature-engineering subsystem as a whole.
FEATURE_ENGINEERING_VERSION: str = "feature-engineering@1.0.0"

# Component versions.
FEATURE_DOMAIN_VERSION: str = "feature-domain@1.0.0"
FEATURE_IDENTITY_VERSION: str = "feature-identity@1.0.0"
FEATURE_FREQUENCY_VERSION: str = "feature-frequency@1.0.0"
FEATURE_TEMPORAL_VERSION: str = "feature-temporal@1.0.0"
FEATURE_CONNECTIVITY_VERSION: str = "feature-connectivity@1.0.0"
FEATURE_SPECTRAL_VERSION: str = "feature-spectral@1.0.0"
FEATURE_TOPOGRAPHY_VERSION: str = "feature-topography@1.0.0"
FEATURE_REGISTRY_VERSION: str = "feature-registry@1.0.0"
FEATURE_AUDIT_VERSION: str = "feature-audit@1.0.0"
FEATURE_LINEAGE_VERSION: str = "feature-lineage@1.0.0"
FEATURE_VALIDATION_VERSION: str = "feature-validation@1.0.0"
FEATURE_REPORT_VERSION: str = "feature-report@1.0.0"

# Fixed, deterministic default timestamp for "created_at" fields that must NOT
# perturb reproducibility hashes (mirrors signal_processing / eeg_foundation / ml).
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"

# Float quantization (decimals) applied before fingerprinting feature values so a
# feature vector's content id is stable for identical inputs (NR-10).
FINGERPRINT_DECIMALS: int = 9
