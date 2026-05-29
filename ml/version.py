"""Canonical version identities for the ML layer (V1-P5 / V1-P6).

Versions are the backbone of governance (AP-9), traceability (AP-5), and
reproducibility (AP-6). Every artifact the ML layer produces records the exact
versions that produced it, so a result can always be regenerated and audited.

Bump a version whenever the *behaviour or contract* it names changes.
"""

from __future__ import annotations

# The ML subsystem as a whole.
ML_LAYER_VERSION: str = "ml@1.0.0"

# Baseline model architecture versions (V1-P5).
ARCHITECTURE_VERSIONS: dict[str, str] = {
    "simple_cnn": "simple_cnn@1.0.0",
    "eegnet": "eegnet@1.0.0",
    "tcn": "tcn@1.0.0",
}

# Training framework version (V1-P5).
TRAINING_FRAMEWORK_VERSION: str = "training@1.0.0"

# Model contract / schema version (V1-P5).
CONTRACT_VERSION: str = "model-contract@1.0.0"

# Registry / artifact / lineage / benchmarking schema versions (V1-P5).
REGISTRY_VERSION: str = "model-registry@1.0.0"
ARTIFACT_VERSION: str = "artifact@1.0.0"
LINEAGE_VERSION: str = "lineage@1.0.0"
BENCHMARK_VERSION: str = "benchmark@1.0.0"

# Uncertainty subsystem versions (V1-P6).
CALIBRATION_VERSION: str = "calibration@1.0.0"
CONFORMAL_VERSION: str = "conformal@1.0.0"
COVERAGE_VERSION: str = "coverage@1.0.0"
RISK_VERSION: str = "risk@1.0.0"
UNCERTAINTY_REGISTRY_VERSION: str = "uncertainty-registry@1.0.0"

# A fixed, deterministic default timestamp used wherever a "created_at" field is
# required but must NOT perturb reproducibility hashes. Real wall-clock time may
# be recorded as *non-hashed* metadata (e.g. registry training_date) where audit
# needs it; it never enters a content hash (NR-10).
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
