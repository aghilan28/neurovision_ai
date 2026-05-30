"""Version identities for the EEG Foundation (Productization P1).

Every EEG-foundation artifact (asset, metadata record, validation result, storage
record, registry record, audit event, lineage node, report) records the exact
versions that produced it, so a real EEG asset is reproducible and auditable for
its entire lifetime (AP-5/AP-6/AP-9, NR-10/NR-11). Bump a version when the named
behaviour or contract changes.

This mirrors ``backend.clinical_cases.version`` and ``ml.version`` so the EEG layer
speaks the same versioning language as the rest of the platform.
"""

from __future__ import annotations

# The EEG-foundation subsystem as a whole.
EEG_FOUNDATION_VERSION: str = "eeg-foundation@1.0.0"

# Component versions.
EEG_DOMAIN_VERSION: str = "eeg-domain@1.0.0"
EEG_IDENTITY_VERSION: str = "eeg-identity@1.0.0"
EEG_INGESTION_VERSION: str = "eeg-ingestion@1.0.0"
EEG_VALIDATION_VERSION: str = "eeg-validation@1.0.0"
EEG_METADATA_VERSION: str = "eeg-metadata@1.0.0"
EEG_STORAGE_VERSION: str = "eeg-storage@1.0.0"
EEG_REGISTRY_VERSION: str = "eeg-registry@1.0.0"
EEG_AUDIT_VERSION: str = "eeg-audit@1.0.0"
EEG_LINEAGE_VERSION: str = "eeg-lineage@1.0.0"
EEG_REPORT_VERSION: str = "eeg-report@1.0.0"

# A fixed, deterministic default timestamp used wherever a "created_at" must NOT
# perturb reproducibility hashes. Real wall-clock time (or a recording's own start
# time read from the file) is recorded as NON-hashed metadata only. Mirrors
# ``ml.version.DETERMINISTIC_EPOCH`` / ``clinical_cases.version.DETERMINISTIC_EPOCH``.
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
