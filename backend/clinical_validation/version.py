"""Version identities for the Clinical Validation & Evidence Platform (DRP-6).

Every validation artifact (benchmark, performance, reliability, calibration, comparison,
evidence, readiness, registry, audit, lineage, report) records the exact versions that
produced it, so the evidence is reproducible and auditable for its entire lifetime
(AP-5/AP-6/AP-9, NR-10/NR-11). Bump a version when the named behaviour or contract changes.

Mirrors ``backend.security_platform.version`` so the validation layer speaks the same
versioning language as the rest of the platform (NR-6).
"""

from __future__ import annotations

# The clinical validation platform as a whole.
CLINICAL_VALIDATION_VERSION: str = "clinical-validation@1.0.0"

# Component versions.
CLINICAL_DOMAIN_VERSION: str = "clinical-domain@1.0.0"
CLINICAL_IDENTITY_VERSION: str = "clinical-identity@1.0.0"
CLINICAL_BENCHMARK_VERSION: str = "clinical-benchmark@1.0.0"
CLINICAL_PERFORMANCE_VERSION: str = "clinical-performance@1.0.0"
CLINICAL_RELIABILITY_VERSION: str = "clinical-reliability@1.0.0"
CLINICAL_CALIBRATION_VERSION: str = "clinical-calibration@1.0.0"
CLINICAL_COMPARISON_VERSION: str = "clinical-comparison@1.0.0"
CLINICAL_EVIDENCE_VERSION: str = "clinical-evidence@1.0.0"
CLINICAL_READINESS_VERSION: str = "clinical-readiness@1.0.0"
CLINICAL_REGISTRY_VERSION: str = "clinical-registry@1.0.0"
CLINICAL_AUDIT_VERSION: str = "clinical-audit@1.0.0"
CLINICAL_LINEAGE_VERSION: str = "clinical-lineage@1.0.0"
CLINICAL_VALIDATION_RECORD_VERSION: str = "clinical-validation-record@1.0.0"
CLINICAL_REPORT_VERSION: str = "clinical-report@1.0.0"

# Fixed, deterministic default "created_at" (never enters a reproducibility hash).
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"

# Float quantization (decimals) before fingerprinting metrics (NR-10).
FINGERPRINT_DECIMALS: int = 9
