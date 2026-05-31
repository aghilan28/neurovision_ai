"""Version identities for the Production Model Program (DRP-2).

Every production-model artifact (training experiment, model, benchmark, evaluation,
readiness assessment, registry record, audit event, lineage node, validation record,
report) records the exact versions that produced it, so a production-candidate model is
reproducible and auditable for its entire lifetime (AP-5/AP-6/AP-9, NR-10/NR-11). Bump a
version when the named behaviour or contract changes.

Mirrors ``backend.model_foundation.version`` so the production-model layer speaks the same
versioning language as the rest of the platform (NR-6).
"""

from __future__ import annotations

# The production-models subsystem as a whole.
PRODUCTION_MODELS_VERSION: str = "production-models@1.0.0"

# Component versions.
PRODUCTION_DOMAIN_VERSION: str = "production-model-domain@1.0.0"
PRODUCTION_IDENTITY_VERSION: str = "production-model-identity@1.0.0"
PRODUCTION_ARCH_VERSION: str = "production-model-arch@1.0.0"
PRODUCTION_TRAINING_VERSION: str = "production-model-training@1.0.0"
PRODUCTION_BENCHMARK_VERSION: str = "production-model-benchmark@1.0.0"
PRODUCTION_EVALUATION_VERSION: str = "production-model-evaluation@1.0.0"
PRODUCTION_READINESS_VERSION: str = "production-model-readiness@1.0.0"
PRODUCTION_REGISTRY_VERSION: str = "production-model-registry@1.0.0"
PRODUCTION_AUDIT_VERSION: str = "production-model-audit@1.0.0"
PRODUCTION_LINEAGE_VERSION: str = "production-model-lineage@1.0.0"
PRODUCTION_VALIDATION_VERSION: str = "production-model-validation@1.0.0"
PRODUCTION_REPORT_VERSION: str = "production-model-report@1.0.0"

# Fixed, deterministic default timestamp for "created_at" fields that must NOT
# perturb reproducibility hashes (mirrors the rest of the platform).
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"

# The default deterministic training seed. Training is seeded so every run is
# bit-for-bit reproducible (NR-9). Callers may override per experiment.
DEFAULT_SEED: int = 20240517

# Float quantization (decimals) applied before fingerprinting weights / metrics so an
# artifact's content id is stable for identical inputs (NR-10).
FINGERPRINT_DECIMALS: int = 9
