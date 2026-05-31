"""``backend/dataset_integration`` — Real Dataset Integration subsystem (DRP-1).

Closes the audit's #1 critical blocker — *no real datasets integrated* — by adding a
governed **external-dataset lifecycle**: inventory, registration, validation, governance
metadata, readiness scoring, lineage, and audit, for the mandatory corpora (TUH EEG,
CHB-MIT, Temple/TUSZ, Siena Scalp, Bonn) and any future EEG dataset — **from local manifests
only (never downloaded)**.

It manages datasets; it does **not** train models or modify any other subsystem. It reuses
the platform's shared ``ml.lineage`` tracker, the shared ``ImmutableAuditLog``,
``ml.validation``, and the model-foundation connector framework (integration, not
duplication). Boundary: imports ``ml`` + sibling ``backend`` only; never ``frontend``.
"""

from __future__ import annotations

from .version import (
    DATASET_INTEGRATION_VERSION, DATASET_DOMAIN_VERSION, DATASET_IDENTITY_VERSION,
    DATASET_INVENTORY_VERSION, DATASET_REGISTRATION_VERSION, DATASET_VALIDATION_VERSION,
    DATASET_GOVERNANCE_VERSION, DATASET_READINESS_VERSION, DATASET_REGISTRY_VERSION,
    DATASET_AUDIT_VERSION, DATASET_LINEAGE_VERSION, DATASET_REPORT_VERSION,
)
from .models import (
    EegDatasetSource, DatasetFormat, LicenseType, InventoryStatus, ValidationSeverity,
    GovernanceStatus, ReadinessClass, EntityKind, DatasetVersion, DatasetIdentity,
    DatasetSourceRecord, DatasetValidationRecord, DatasetGovernanceRecord, DatasetReadinessRecord,
    DatasetInventoryRecord, DatasetRecord, DatasetRegistryRecord, DatasetAuditRecord,
    DatasetLineageRecord,
)
from .identity import mint_identity, validate_identity, Identity, IdentityError
from .audit import make_dataset_audit_log, ImmutableAuditLog, AuditError
from .lineage import (
    make_source_lineage, make_dataset_lineage, make_version_lineage, LineageTracker,
)
from .registry import DatasetCatalogRegistry, RegistryError
from .inventory import (
    build_inventory_record, build_full_inventory, builtin_manifest, load_manifest,
    list_builtin_manifests, BUILTIN_CATALOG, MANIFEST_DIR,
)
from .validation import DatasetValidator
from .governance import DatasetGovernance
from .readiness import ReadinessEngine
from .registration import (
    manifest_fingerprint, canonical_manifest, delegate_to_model_foundation,
    has_model_foundation_connector,
)
from .schemas import ENTITY_CONTRACTS, validate_entity
from .service import (
    DatasetIntegrationService, DatasetIntegrationOutcome, DatasetIntegrationError,
)

__all__ = [
    "DATASET_INTEGRATION_VERSION", "DATASET_DOMAIN_VERSION", "DATASET_IDENTITY_VERSION",
    "DATASET_INVENTORY_VERSION", "DATASET_REGISTRATION_VERSION", "DATASET_VALIDATION_VERSION",
    "DATASET_GOVERNANCE_VERSION", "DATASET_READINESS_VERSION", "DATASET_REGISTRY_VERSION",
    "DATASET_AUDIT_VERSION", "DATASET_LINEAGE_VERSION", "DATASET_REPORT_VERSION",
    "EegDatasetSource", "DatasetFormat", "LicenseType", "InventoryStatus", "ValidationSeverity",
    "GovernanceStatus", "ReadinessClass", "EntityKind", "DatasetVersion", "DatasetIdentity",
    "DatasetSourceRecord", "DatasetValidationRecord", "DatasetGovernanceRecord",
    "DatasetReadinessRecord", "DatasetInventoryRecord", "DatasetRecord", "DatasetRegistryRecord",
    "DatasetAuditRecord", "DatasetLineageRecord",
    "mint_identity", "validate_identity", "Identity", "IdentityError",
    "make_dataset_audit_log", "ImmutableAuditLog", "AuditError",
    "make_source_lineage", "make_dataset_lineage", "make_version_lineage", "LineageTracker",
    "DatasetCatalogRegistry", "RegistryError",
    "build_inventory_record", "build_full_inventory", "builtin_manifest", "load_manifest",
    "list_builtin_manifests", "BUILTIN_CATALOG", "MANIFEST_DIR",
    "DatasetValidator", "DatasetGovernance", "ReadinessEngine",
    "manifest_fingerprint", "canonical_manifest", "delegate_to_model_foundation",
    "has_model_foundation_connector", "ENTITY_CONTRACTS", "validate_entity",
    "DatasetIntegrationService", "DatasetIntegrationOutcome", "DatasetIntegrationError",
]
