"""Version identities for the Real Dataset Platform subsystem (Track 1).

This subsystem turns the DRP-1 *dataset framework* into a *real dataset platform*: it
acquires real public EEG corpora locally, validates them from the **actual files**
(not manifests), extracts real metadata + labels, builds inventories, scores
**training readiness**, and tracks lineage + audit — reusing the platform's shared
systems (``ml.lineage``, the shared ``ImmutableAuditLog``, ``ml.validation``,
``ml.provenance`` and the ``eeg_foundation`` real-file reader).

It acquires + validates + registers + verifies + prepares datasets for training.
It trains no models and modifies no other subsystem.
"""

from __future__ import annotations

DATASET_ACQUISITION_VERSION: str = "dataset-acquisition@1.0.0"

ACQUISITION_DOMAIN_VERSION: str = "acquisition-domain@1.0.0"
ACQUISITION_IDENTITY_VERSION: str = "acquisition-identity@1.0.0"
ACQUISITION_SOURCES_VERSION: str = "acquisition-sources@1.0.0"
ACQUISITION_DOWNLOAD_VERSION: str = "acquisition-download@1.0.0"
ACQUISITION_STORAGE_VERSION: str = "acquisition-storage@1.0.0"
ACQUISITION_CONNECTOR_VERSION: str = "acquisition-connector@1.0.0"
ACQUISITION_VALIDATION_VERSION: str = "acquisition-validation@1.0.0"
ACQUISITION_LABELS_VERSION: str = "acquisition-labels@1.0.0"
ACQUISITION_INVENTORY_VERSION: str = "acquisition-inventory@1.0.0"
ACQUISITION_READINESS_VERSION: str = "acquisition-readiness@1.0.0"
ACQUISITION_REGISTRY_VERSION: str = "acquisition-registry@1.0.0"
ACQUISITION_AUDIT_VERSION: str = "acquisition-audit@1.0.0"
ACQUISITION_LINEAGE_VERSION: str = "acquisition-lineage@1.0.0"
ACQUISITION_REPORT_VERSION: str = "acquisition-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
