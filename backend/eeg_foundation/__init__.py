"""``backend/eeg_foundation`` — Real EEG Foundation Layer (Productization P1).

The platform's first **real-EEG** capability. A real EEG file enters and the platform:
loads it (real bytes), validates it (structured findings), parses it, extracts
normalized metadata, fingerprints + stores it (by reference), mints an identity,
records lineage (parented by the Case node, so the chain reaches the patient), writes
an immutable audit trail, registers it, and reports on it. **Nothing more** — no signal
filtering, artifact removal, feature extraction, inference, analytics, APIs, auth, or
deployment (those are out of scope for P1).

Supported formats (closed set): EDF, EDF+, BDF, BDF+, FIF, SET. Readers are
spec-compliant **pure-Python + NumPy** implementations that read the real bytes of real
files — preserving the platform's framework-free, pinned, bit-for-bit reproducible
runtime (NR-10 / AP-6); no new third-party dependency is introduced.

Required chain realized: **Patient → Case → EEG Asset** (via ``backend.clinical_cases``
+ the shared ``ml.lineage.LineageTracker``). Reuses the shared ``ImmutableAuditLog`` —
no parallel audit/lineage.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` + sibling
``backend`` subsystems; never imports ``frontend``.
"""

from __future__ import annotations

from .version import (
    EEG_FOUNDATION_VERSION, EEG_DOMAIN_VERSION, EEG_IDENTITY_VERSION, EEG_INGESTION_VERSION,
    EEG_METADATA_VERSION, EEG_VALIDATION_VERSION, EEG_STORAGE_VERSION, EEG_REGISTRY_VERSION,
    EEG_AUDIT_VERSION, EEG_LINEAGE_VERSION, EEG_REPORT_VERSION,
)
from .identity import EEGIdentity, EEGIdentityError, mint_eeg, validate_eeg_identity
from .models.domain import (
    EEGFormat, SUPPORTED_FORMATS, FORMAT_EXTENSIONS, EEGAssetStatus, EEGChannel, EEGChannelSet,
    EEGAnnotation, EEGSource, EEGMetadata, EEGStorageRecord, EEGAuditRecord, EEGLineageRecord,
    EEGRegistryRecord, EEGRecord,
)
from .ingestion import RawEEG, RawChannel, load_eeg, detect_format, detect_format_path
from .validation import (
    EEGValidator, EEGValidationReport, EEGValidationResult, EEGValidationFinding,
    EEGValidationSeverity,
)
from .metadata import normalize
from .storage import LocalEEGStore, sha256_file, fingerprint_for
from .registry import EEGRegistry
from .audit import make_eeg_audit_log
from .service import EEGFoundationService

__all__ = [
    "EEG_FOUNDATION_VERSION", "EEG_DOMAIN_VERSION", "EEG_IDENTITY_VERSION",
    "EEG_INGESTION_VERSION", "EEG_METADATA_VERSION", "EEG_VALIDATION_VERSION",
    "EEG_STORAGE_VERSION", "EEG_REGISTRY_VERSION", "EEG_AUDIT_VERSION", "EEG_LINEAGE_VERSION",
    "EEG_REPORT_VERSION",
    "EEGIdentity", "EEGIdentityError", "mint_eeg", "validate_eeg_identity",
    "EEGFormat", "SUPPORTED_FORMATS", "FORMAT_EXTENSIONS", "EEGAssetStatus", "EEGChannel",
    "EEGChannelSet", "EEGAnnotation", "EEGSource", "EEGMetadata", "EEGStorageRecord",
    "EEGAuditRecord", "EEGLineageRecord", "EEGRegistryRecord", "EEGRecord",
    "RawEEG", "RawChannel", "load_eeg", "detect_format", "detect_format_path",
    "EEGValidator", "EEGValidationReport", "EEGValidationResult", "EEGValidationFinding",
    "EEGValidationSeverity", "normalize", "LocalEEGStore", "sha256_file", "fingerprint_for",
    "EEGRegistry", "make_eeg_audit_log", "EEGFoundationService",
]
