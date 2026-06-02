"""``backend/eeg_foundation`` — Real EEG Foundation Layer (Productization P1).

Transforms NeuroVision from a synthetic-data platform into one that can accept a
**real EEG file**. The scope is deliberately narrow: a real recording can

    enter -> be loaded -> validated -> parsed -> have metadata extracted ->
    become a NeuroVision EEG asset -> be stored -> tracked (lineage + audit) ->
    reported on

and *nothing more* (no signal processing, feature extraction, modelling,
inference, analytics, APIs, dashboards, or deployment — those are out of scope).

Supported formats (closed vocabulary): EDF, EDF+, BDF, BDF+, FIF, SET — read with
MNE-Python (the industry-standard reader; no mock/fake parsers).

Boundary (NR-8): part of the ``backend`` Application layer. Imports ``ml`` (for
provenance/lineage/validation) and reuses the platform's tamper-evident audit log
from ``backend.clinical_cases.audit`` (intra-backend reuse — no parallel audit or
lineage systems). It never imports ``frontend``. EEG assets attach to the existing
clinical ``Case`` so the platform-wide chain is Patient -> Case -> EEG Asset.

Tests live in the repository-root ``tests/`` (``tests/test_eeg_foundation*.py``) and
fixtures in ``tests/fixtures/eeg/``, matching the established platform convention
(e.g. ``clinical_cases``); design notes live in ``docs/``.
"""

from __future__ import annotations

from .version import (
    EEG_FOUNDATION_VERSION, EEG_DOMAIN_VERSION, EEG_IDENTITY_VERSION,
    EEG_INGESTION_VERSION, EEG_VALIDATION_VERSION, EEG_METADATA_VERSION,
    EEG_STORAGE_VERSION, EEG_REGISTRY_VERSION, EEG_AUDIT_VERSION,
    EEG_LINEAGE_VERSION, EEG_REPORT_VERSION,
)
from .models import (
    EEGFormat, SUPPORTED_EXTENSIONS, EEGChannelType, EEGAssetStatus,
    EEGValidationSeverity, EEGIdentity, EEGChannel, EEGChannelSet, EEGAnnotation,
    EEGSource, EEGMetadata, EEGValidationFinding, EEGValidationResult,
    EEGStorageRecord, EEGAuditRecord, EEGLineageRecord, EEGVersion,
    EEGRegistryRecord, EEGRecord,
)
from .identity import (
    Identity, mint_identity, validate_identity, parse_identity,
    IDENTITY_POLICIES, IdentityError,
)
from .ingestion import (
    load_eeg, detect_format, detect_format_from_bytes, ParsedEEG, ParsedChannel,
)
from .validation import EEGFileValidator, EEGIntegrityValidator, EEGIntegrityError
from .metadata import extract_metadata, compute_recording_id
from .storage import LocalEEGStore, fingerprint_of_checksum
from .registry import EEGRegistry
from .audit import make_eeg_audit_log, ImmutableAuditLog, AuditError
from .lineage import make_eeg_lineage, eeg_version_bundle, LineageTracker, LineageRecord
from .service import EEGFoundationService, IngestionOutcome, EEGFoundationError

__all__ = [
    # versions
    "EEG_FOUNDATION_VERSION", "EEG_DOMAIN_VERSION", "EEG_IDENTITY_VERSION",
    "EEG_INGESTION_VERSION", "EEG_VALIDATION_VERSION", "EEG_METADATA_VERSION",
    "EEG_STORAGE_VERSION", "EEG_REGISTRY_VERSION", "EEG_AUDIT_VERSION",
    "EEG_LINEAGE_VERSION", "EEG_REPORT_VERSION",
    # models / vocab
    "EEGFormat", "SUPPORTED_EXTENSIONS", "EEGChannelType", "EEGAssetStatus",
    "EEGValidationSeverity", "EEGIdentity", "EEGChannel", "EEGChannelSet", "EEGAnnotation",
    "EEGSource", "EEGMetadata", "EEGValidationFinding", "EEGValidationResult",
    "EEGStorageRecord", "EEGAuditRecord", "EEGLineageRecord", "EEGVersion",
    "EEGRegistryRecord", "EEGRecord",
    # identity
    "Identity", "mint_identity", "validate_identity", "parse_identity",
    "IDENTITY_POLICIES", "IdentityError",
    # ingestion
    "load_eeg", "detect_format", "detect_format_from_bytes", "ParsedEEG", "ParsedChannel",
    # validation
    "EEGFileValidator", "EEGIntegrityValidator", "EEGIntegrityError",
    # metadata
    "extract_metadata", "compute_recording_id",
    # storage
    "LocalEEGStore", "fingerprint_of_checksum",
    # registry
    "EEGRegistry",
    # audit / lineage
    "make_eeg_audit_log", "ImmutableAuditLog", "AuditError",
    "make_eeg_lineage", "eeg_version_bundle", "LineageTracker", "LineageRecord",
    # service
    "EEGFoundationService", "IngestionOutcome", "EEGFoundationError",
]
