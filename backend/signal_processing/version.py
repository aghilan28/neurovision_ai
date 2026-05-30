"""Version identities for the Signal Processing Foundation (Productization P2).

Every signal-processing artifact (processed asset, quality record, artifact record,
processing record, registry record, audit event, lineage node, report) records the
exact versions that produced it, so a cleaned EEG is reproducible and auditable for
its entire lifetime (AP-5/AP-6/AP-9, NR-10/NR-11). Bump a version when the named
behaviour or contract changes.

Mirrors ``backend.eeg_foundation.version`` / ``ml.version`` so the signal layer
speaks the same versioning language as the rest of the platform.
"""

from __future__ import annotations

# The signal-processing subsystem as a whole.
SIGNAL_PROCESSING_VERSION: str = "signal-processing@1.0.0"

# Component versions.
SIGNAL_DOMAIN_VERSION: str = "signal-domain@1.0.0"
SIGNAL_IDENTITY_VERSION: str = "signal-identity@1.0.0"
SIGNAL_FILTERING_VERSION: str = "signal-filtering@1.0.0"
SIGNAL_QUALITY_VERSION: str = "signal-quality@1.0.0"
SIGNAL_ARTIFACT_VERSION: str = "signal-artifact@1.0.0"
SIGNAL_REMOVAL_VERSION: str = "signal-removal@1.0.0"
SIGNAL_PREPROCESSING_VERSION: str = "signal-preprocessing@1.0.0"
SIGNAL_STORAGE_VERSION: str = "signal-storage@1.0.0"
SIGNAL_REGISTRY_VERSION: str = "signal-registry@1.0.0"
SIGNAL_AUDIT_VERSION: str = "signal-audit@1.0.0"
SIGNAL_LINEAGE_VERSION: str = "signal-lineage@1.0.0"
SIGNAL_REPORT_VERSION: str = "signal-report@1.0.0"

# Fixed, deterministic default timestamp for "created_at" fields that must NOT
# perturb reproducibility hashes (mirrors eeg_foundation / ml). Real wall-clock time
# is never used inside a content hash.
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"

# Deterministic seed for any algorithm that would otherwise be stochastic (e.g. the
# ICA decomposition). Fixed so artifact removal is bit-for-bit reproducible (NR-9).
DETERMINISTIC_SEED: int = 9743

# Float quantization (decimals) applied before fingerprinting signal arrays so a
# processed signal's content id is stable for identical inputs (NR-10).
FINGERPRINT_DECIMALS: int = 9
