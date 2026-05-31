"""``backend/dataset_acquisition`` — Real Dataset Platform (Track 1).

Turns the DRP-1 *dataset framework* into a *real dataset platform*. It **acquires** real
public EEG corpora locally (OPEN sources only; approval-gated corpora are reported, never
auto-downloaded), **validates** them from the **actual files** (not manifests), extracts
**real metadata + labels**, builds inventories, scores **training readiness**
(NOT_READY / PARTIALLY_READY / READY_FOR_TRAINING), and tracks lineage + audit.

It reuses the platform's shared systems — the ``eeg_foundation`` real-file MNE reader,
``ml.lineage``, the shared ``ImmutableAuditLog``, ``ml.validation``, ``ml.provenance`` —
and creates **no parallel systems**. It manages datasets; it trains no models and modifies
no other subsystem. Boundary: imports ``ml`` + sibling ``backend`` only; never ``frontend``.
"""

from __future__ import annotations

from .version import (
    ACQUISITION_AUDIT_VERSION, ACQUISITION_CONNECTOR_VERSION, ACQUISITION_DOMAIN_VERSION,
    ACQUISITION_DOWNLOAD_VERSION, ACQUISITION_IDENTITY_VERSION, ACQUISITION_INVENTORY_VERSION,
    ACQUISITION_LABELS_VERSION, ACQUISITION_LINEAGE_VERSION, ACQUISITION_READINESS_VERSION,
    ACQUISITION_REGISTRY_VERSION, ACQUISITION_REPORT_VERSION, ACQUISITION_SOURCES_VERSION,
    ACQUISITION_STORAGE_VERSION, ACQUISITION_VALIDATION_VERSION, DATASET_ACQUISITION_VERSION,
    DETERMINISTIC_EPOCH,
)
from .models import (
    AccessRequirement, AcquisitionItem, AcquisitionRecord, AcquisitionRegistryRecord,
    AcquisitionSourceSpec, AvailabilityRecord, AvailabilityState, DatasetSource, EntityKind,
    InventoryRecord, LabelRecord, LabelScheme, LabelValue, LabelVerificationRecord,
    LocalFileRecord, PatientRecord, RealDatasetRecord, RecordingFormat, RecordingRecord,
    SeizureInterval, StructureValidationRecord, TrainingReadinessClass, TrainingReadinessRecord,
    ValidationFinding, ValidationSeverity,
)
from .identity import Identity, IdentityError, mint_identity, validate_identity
from .sources import MANDATORY_SOURCES, SOURCE_SPECS, all_specs, spec_for
from .acquisition import acquire, acquire_source, plan_all, spec_signature
from .storage import (
    DatasetAvailabilityTracker, DatasetLocationRegistry, DatasetStorageManager,
    DatasetVerificationManager, default_data_root,
)
from .connectors import (
    ChbMitConnector, ConnectorResult, EdfDirectoryConnector, RealDatasetConnector,
    connector_for, parse_chb_summary,
)
from .validation import StructureValidator
from .labels import LabelVerifier
from .inventory import InventoryBuilder
from .readiness import TrainingReadinessEngine
from .registry import RealDatasetRegistry, RegistryError
from .audit import AuditError, ImmutableAuditLog, make_acquisition_audit_log
from .schemas import ENTITY_CONTRACTS, validate_entity
from .service import RealDatasetError, RealDatasetOutcome, RealDatasetService

__all__ = [
    # versions
    "DATASET_ACQUISITION_VERSION", "ACQUISITION_DOMAIN_VERSION", "ACQUISITION_IDENTITY_VERSION",
    "ACQUISITION_SOURCES_VERSION", "ACQUISITION_DOWNLOAD_VERSION", "ACQUISITION_STORAGE_VERSION",
    "ACQUISITION_CONNECTOR_VERSION", "ACQUISITION_VALIDATION_VERSION", "ACQUISITION_LABELS_VERSION",
    "ACQUISITION_INVENTORY_VERSION", "ACQUISITION_READINESS_VERSION", "ACQUISITION_REGISTRY_VERSION",
    "ACQUISITION_AUDIT_VERSION", "ACQUISITION_LINEAGE_VERSION", "ACQUISITION_REPORT_VERSION",
    "DETERMINISTIC_EPOCH",
    # domain
    "AccessRequirement", "AcquisitionItem", "AcquisitionRecord", "AcquisitionRegistryRecord",
    "AcquisitionSourceSpec", "AvailabilityRecord", "AvailabilityState", "DatasetSource",
    "EntityKind", "InventoryRecord", "LabelRecord", "LabelScheme", "LabelValue",
    "LabelVerificationRecord", "LocalFileRecord", "PatientRecord", "RealDatasetRecord",
    "RecordingFormat", "RecordingRecord", "SeizureInterval", "StructureValidationRecord",
    "TrainingReadinessClass", "TrainingReadinessRecord", "ValidationFinding", "ValidationSeverity",
    # identity / sources / engines / infra
    "Identity", "IdentityError", "mint_identity", "validate_identity",
    "MANDATORY_SOURCES", "SOURCE_SPECS", "all_specs", "spec_for",
    "acquire", "acquire_source", "plan_all", "spec_signature",
    "DatasetAvailabilityTracker", "DatasetLocationRegistry", "DatasetStorageManager",
    "DatasetVerificationManager", "default_data_root",
    "ChbMitConnector", "ConnectorResult", "EdfDirectoryConnector", "RealDatasetConnector",
    "connector_for", "parse_chb_summary",
    "StructureValidator", "LabelVerifier", "InventoryBuilder", "TrainingReadinessEngine",
    "RealDatasetRegistry", "RegistryError", "AuditError", "ImmutableAuditLog",
    "make_acquisition_audit_log", "ENTITY_CONTRACTS", "validate_entity",
    "RealDatasetError", "RealDatasetOutcome", "RealDatasetService",
]
