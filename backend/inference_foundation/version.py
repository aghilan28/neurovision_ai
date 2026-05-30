"""Version identities for the Clinical Inference Foundation (Productization P5).

Every inference artifact (prediction, confidence, calibration, explanation, registry
record, audit event, lineage node, validation record, report) records the exact
versions that produced it, so a prediction is reproducible and auditable for its
entire lifetime (AP-5/AP-6/AP-9, NR-10/NR-11). Bump a version when the named
behaviour or contract changes.

Mirrors ``backend.model_foundation.version`` so the inference layer speaks the same
versioning language as the rest of the platform.
"""

from __future__ import annotations

# The inference-foundation subsystem as a whole.
INFERENCE_FOUNDATION_VERSION: str = "inference-foundation@1.0.0"

# Component versions.
INFERENCE_DOMAIN_VERSION: str = "inference-domain@1.0.0"
INFERENCE_IDENTITY_VERSION: str = "inference-identity@1.0.0"
INFERENCE_EXECUTION_VERSION: str = "inference-execution@1.0.0"
INFERENCE_PREDICTION_VERSION: str = "inference-prediction@1.0.0"
INFERENCE_CONFIDENCE_VERSION: str = "inference-confidence@1.0.0"
INFERENCE_CALIBRATION_VERSION: str = "inference-calibration@1.0.0"
INFERENCE_EXPLAINABILITY_VERSION: str = "inference-explainability@1.0.0"
INFERENCE_REGISTRY_VERSION: str = "inference-registry@1.0.0"
INFERENCE_AUDIT_VERSION: str = "inference-audit@1.0.0"
INFERENCE_LINEAGE_VERSION: str = "inference-lineage@1.0.0"
INFERENCE_VALIDATION_VERSION: str = "inference-validation@1.0.0"
INFERENCE_REPORT_VERSION: str = "inference-report@1.0.0"

# Fixed, deterministic default timestamp for "created_at" fields that must NOT
# perturb reproducibility hashes (mirrors the rest of the platform).
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"

# Float quantization (decimals) applied before fingerprinting predictions / scores so
# an inference asset's content id is stable for identical inputs (NR-10).
FINGERPRINT_DECIMALS: int = 9
