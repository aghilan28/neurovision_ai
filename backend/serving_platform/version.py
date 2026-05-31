"""Version identities for the Production Serving Platform (DRP-3).

Every serving artifact (request, execution, response, lifecycle, validation, readiness,
registry, audit, lineage, report) records the exact versions that produced it, so a served
prediction is reproducible and auditable for its entire lifetime (AP-5/AP-6/AP-9,
NR-10/NR-11). Bump a version when the named behaviour or contract changes.

Mirrors ``backend.inference_foundation.version`` / ``backend.production_models.version`` so
the serving layer speaks the same versioning language as the rest of the platform (NR-6).
"""

from __future__ import annotations

# The serving platform as a whole.
SERVING_PLATFORM_VERSION: str = "serving-platform@1.0.0"

# Component versions.
SERVING_DOMAIN_VERSION: str = "serving-domain@1.0.0"
SERVING_IDENTITY_VERSION: str = "serving-identity@1.0.0"
SERVING_EXECUTION_VERSION: str = "serving-execution@1.0.0"
SERVING_PREDICTION_VERSION: str = "serving-prediction@1.0.0"
SERVING_ROUTING_VERSION: str = "serving-routing@1.0.0"
SERVING_LIFECYCLE_VERSION: str = "serving-lifecycle@1.0.0"
SERVING_CONTRACT_VERSION: str = "serving-contract@1.0.0"
SERVING_REGISTRY_VERSION: str = "serving-registry@1.0.0"
SERVING_READINESS_VERSION: str = "serving-readiness@1.0.0"
SERVING_AUDIT_VERSION: str = "serving-audit@1.0.0"
SERVING_LINEAGE_VERSION: str = "serving-lineage@1.0.0"
SERVING_VALIDATION_VERSION: str = "serving-validation@1.0.0"
SERVING_REPORT_VERSION: str = "serving-report@1.0.0"

# Fixed, deterministic default timestamp for "created_at" fields that must NOT
# perturb reproducibility hashes (mirrors the rest of the platform).
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"

# Float quantization (decimals) applied before fingerprinting so an artifact's content id
# is stable for identical inputs (NR-10).
FINGERPRINT_DECIMALS: int = 9
