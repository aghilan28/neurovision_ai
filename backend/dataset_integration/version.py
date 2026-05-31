"""Version identities for the Real Dataset Integration subsystem (DRP-1).

This subsystem governs the **lifecycle of external EEG datasets** (inventory, registration,
validation, governance metadata, readiness, lineage, audit). It manages datasets; it does
not train models or modify any other subsystem. Every artifact records the versions that
produced it so the dataset lifecycle is reproducible and auditable.
"""

from __future__ import annotations

DATASET_INTEGRATION_VERSION: str = "dataset-integration@1.0.0"

DATASET_DOMAIN_VERSION: str = "dataset-domain@1.0.0"
DATASET_IDENTITY_VERSION: str = "dataset-identity@1.0.0"
DATASET_INVENTORY_VERSION: str = "dataset-inventory@1.0.0"
DATASET_REGISTRATION_VERSION: str = "dataset-registration@1.0.0"
DATASET_VALIDATION_VERSION: str = "dataset-validation@1.0.0"
DATASET_GOVERNANCE_VERSION: str = "dataset-governance@1.0.0"
DATASET_READINESS_VERSION: str = "dataset-readiness@1.0.0"
DATASET_REGISTRY_VERSION: str = "dataset-registry@1.0.0"
DATASET_AUDIT_VERSION: str = "dataset-audit@1.0.0"
DATASET_LINEAGE_VERSION: str = "dataset-lineage@1.0.0"
DATASET_REPORT_VERSION: str = "dataset-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
