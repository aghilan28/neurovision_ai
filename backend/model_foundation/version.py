"""Version identities for the Model Foundation Platform (Productization P4).

Every model-foundation artifact (dataset, training run, evaluation, experiment, model,
registry record, audit event, lineage node, validation record, report) records the
exact versions that produced it, so a trained model is reproducible and auditable for
its entire lifetime (AP-5/AP-6/AP-9, NR-10/NR-11). Bump a version when the named
behaviour or contract changes.

Mirrors ``backend.feature_engineering.version`` so the model layer speaks the same
versioning language as the rest of the platform.
"""

from __future__ import annotations

# The model-foundation subsystem as a whole.
MODEL_FOUNDATION_VERSION: str = "model-foundation@1.0.0"

# Component versions.
MODEL_DOMAIN_VERSION: str = "model-domain@1.0.0"
MODEL_IDENTITY_VERSION: str = "model-identity@1.0.0"
MODEL_DATASET_VERSION: str = "model-dataset@1.0.0"
MODEL_TRAINING_VERSION: str = "model-training@1.0.0"
MODEL_EVALUATION_VERSION: str = "model-evaluation@1.0.0"
MODEL_EXPERIMENT_VERSION: str = "model-experiment@1.0.0"
MODEL_ARCH_VERSION: str = "model-arch@1.0.0"
MODEL_REGISTRY_VERSION: str = "model-registry@1.0.0"
MODEL_AUDIT_VERSION: str = "model-audit@1.0.0"
MODEL_LINEAGE_VERSION: str = "model-lineage@1.0.0"
MODEL_VALIDATION_VERSION: str = "model-validation@1.0.0"
MODEL_REPORT_VERSION: str = "model-report@1.0.0"

# Fixed, deterministic default timestamp for "created_at" fields that must NOT
# perturb reproducibility hashes (mirrors the rest of the platform).
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"

# The default deterministic training seed. Training is seeded so every run is
# bit-for-bit reproducible (NR-9). Callers may override per experiment.
DEFAULT_SEED: int = 20240517

# Float quantization (decimals) applied before fingerprinting weights / metrics so a
# model's content id is stable for identical inputs (NR-10).
FINGERPRINT_DECIMALS: int = 9
