"""``backend/signal_processing`` — Signal Processing Foundation (Productization P2).

Transforms a *raw* EEG asset (from Productization P1) into a *validated clean* EEG
asset. The scope is signal quality and nothing else:

    load raw (read-only) -> assess quality -> detect artifacts -> filter +
    remove artifacts -> generate clean EEG -> store -> track (lineage + audit) ->
    report on

No AI, model training, inference, classification, predictions, or clinical
decisions (all out of scope for this phase).

Built strictly on Productization P1: it reads the immutable raw EEG bytes from the
P1 store and references the P1 ``EEGRecord``; it never redesigns, replaces, or
duplicates the EEG Foundation. The raw EEG is never modified — the cleaned signal is
written to a *separate* content-addressed store, and the processed asset's lineage
parents the raw EEG node so the chain is Patient -> Case -> EEG -> Processed.

Boundary (NR-8): part of the ``backend`` Application layer. Imports ``ml``
(provenance/lineage/validation), ``backend.eeg_foundation`` types, and reuses the
platform's tamper-evident audit log from ``backend.clinical_cases.audit`` (intra-
backend reuse — no parallel audit or lineage systems). It never imports ``frontend``.

Tests live in the repository-root ``tests/`` (``tests/test_signal_processing*.py``)
and reuse the P1 EEG fixtures in ``tests/fixtures/eeg/``; design notes live in
``docs/``.
"""

from __future__ import annotations

from .version import (
    SIGNAL_PROCESSING_VERSION, SIGNAL_DOMAIN_VERSION, SIGNAL_IDENTITY_VERSION,
    SIGNAL_FILTERING_VERSION, SIGNAL_QUALITY_VERSION, SIGNAL_ARTIFACT_VERSION,
    SIGNAL_REMOVAL_VERSION, SIGNAL_PREPROCESSING_VERSION, SIGNAL_STORAGE_VERSION,
    SIGNAL_REGISTRY_VERSION, SIGNAL_AUDIT_VERSION, SIGNAL_LINEAGE_VERSION,
    SIGNAL_REPORT_VERSION, DETERMINISTIC_SEED,
)
from .models import (
    SignalKind, FilterType, ArtifactType, RemovalMethod, ArtifactSeverity,
    QualityFindingSeverity, QualityGrade, ProcessedAssetStatus,
    SignalIdentity, SignalRecord, ChannelQuality, SignalQualityFinding,
    SignalQualityRecord, SignalArtifactRecord, FilterConfig, SignalProcessingStep,
    SignalProcessingRecord, ProcessingHistory, ArtifactHistory, QualityHistory,
    ProcessedEEGStorageRecord, ProcessedEEGMetadata, SignalAuditRecord,
    SignalLineageRecord, SignalVersion, SignalRegistryRecord, ProcessedEEGRecord,
)
from .identity import (
    Identity, mint_identity, validate_identity, parse_identity, IdentityError,
)
from .filtering import FilteringEngine, FilteringError
from .quality import SignalQualityEngine
from .artifacts import ArtifactDetectionEngine, ArtifactRemovalEngine
from .preprocessing import (
    ProcessingPipeline, load_raw_signal, RawSignalLoadError, signal_fingerprint,
    array_fingerprint, serialize_signal,
)
from .storage import ProcessedSignalStore
from .registry import SignalRegistry
from .audit import make_signal_audit_log, ImmutableAuditLog, AuditError
from .lineage import make_signal_lineage, signal_version_bundle, LineageTracker, LineageRecord
from .validation import SignalIntegrityValidator
from .service import SignalProcessingService, ProcessingOutcome, SignalProcessingError

__all__ = [
    # versions
    "SIGNAL_PROCESSING_VERSION", "SIGNAL_DOMAIN_VERSION", "SIGNAL_IDENTITY_VERSION",
    "SIGNAL_FILTERING_VERSION", "SIGNAL_QUALITY_VERSION", "SIGNAL_ARTIFACT_VERSION",
    "SIGNAL_REMOVAL_VERSION", "SIGNAL_PREPROCESSING_VERSION", "SIGNAL_STORAGE_VERSION",
    "SIGNAL_REGISTRY_VERSION", "SIGNAL_AUDIT_VERSION", "SIGNAL_LINEAGE_VERSION",
    "SIGNAL_REPORT_VERSION", "DETERMINISTIC_SEED",
    # models / vocab
    "SignalKind", "FilterType", "ArtifactType", "RemovalMethod", "ArtifactSeverity",
    "QualityFindingSeverity", "QualityGrade", "ProcessedAssetStatus",
    "SignalIdentity", "SignalRecord", "ChannelQuality", "SignalQualityFinding",
    "SignalQualityRecord", "SignalArtifactRecord", "FilterConfig", "SignalProcessingStep",
    "SignalProcessingRecord", "ProcessingHistory", "ArtifactHistory", "QualityHistory",
    "ProcessedEEGStorageRecord", "ProcessedEEGMetadata", "SignalAuditRecord",
    "SignalLineageRecord", "SignalVersion", "SignalRegistryRecord", "ProcessedEEGRecord",
    # identity
    "Identity", "mint_identity", "validate_identity", "parse_identity", "IdentityError",
    # engines
    "FilteringEngine", "FilteringError", "SignalQualityEngine",
    "ArtifactDetectionEngine", "ArtifactRemovalEngine",
    # preprocessing
    "ProcessingPipeline", "load_raw_signal", "RawSignalLoadError", "signal_fingerprint",
    "array_fingerprint", "serialize_signal",
    # storage / registry / audit / lineage / validation
    "ProcessedSignalStore", "SignalRegistry", "make_signal_audit_log", "ImmutableAuditLog",
    "AuditError", "make_signal_lineage", "signal_version_bundle", "LineageTracker",
    "LineageRecord", "SignalIntegrityValidator",
    # service
    "SignalProcessingService", "ProcessingOutcome", "SignalProcessingError",
]
