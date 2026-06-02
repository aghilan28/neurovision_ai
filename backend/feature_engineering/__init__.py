"""``backend/feature_engineering`` — Feature Engineering Platform (Productization P3).

Transforms a *processed* (clean) EEG asset (from Productization P2) into an
**immutable** validated **feature asset**. The scope is feature generation and
nothing else:

    load processed (read-only) -> generate features (frequency / temporal /
    connectivity / spectral / topography) -> validate -> create feature asset ->
    track (lineage + audit) -> report on

No model training, model registry, inference, predictions, classification, or
clinical decisions (all out of scope for this phase).

Built strictly on P1 + P2: it reads the immutable processed-signal bytes from the P2
store and references the P2 ``ProcessedEEGRecord``; it never redesigns, replaces, or
duplicates the EEG Foundation or Signal Processing layers. The feature asset's
lineage parents the processed-EEG node, so the platform-wide chain is
Patient -> Case -> EEG -> Processed -> Feature.

Boundary (NR-8): part of the ``backend`` Application layer. Imports ``ml``
(provenance/lineage/validation), reads the P2 store, and reuses the platform's
tamper-evident audit log from ``backend.clinical_cases.audit`` (intra-backend reuse —
no parallel audit or lineage systems). It never imports ``frontend``.

Tests live in the repository-root ``tests/`` (``tests/test_feature_engineering*.py``)
and reuse the P1/P2 assets + P1 EEG fixtures; design notes live in ``docs/``.
"""

from __future__ import annotations

from .version import (
    FEATURE_ENGINEERING_VERSION, FEATURE_DOMAIN_VERSION, FEATURE_IDENTITY_VERSION,
    FEATURE_FREQUENCY_VERSION, FEATURE_TEMPORAL_VERSION, FEATURE_CONNECTIVITY_VERSION,
    FEATURE_SPECTRAL_VERSION, FEATURE_TOPOGRAPHY_VERSION, FEATURE_REGISTRY_VERSION,
    FEATURE_AUDIT_VERSION, FEATURE_LINEAGE_VERSION, FEATURE_VALIDATION_VERSION,
    FEATURE_REPORT_VERSION,
)
from .models import (
    FeatureFamily, FeatureGroup, FeatureScope, FrequencyBand, FeatureAssetStatus,
    FeatureValidationSeverity, FeatureIdentity, FeatureVector, FeatureGroupRecord,
    FeatureMetadata, FeatureValidationRecord, FeatureAuditRecord, FeatureLineageRecord,
    FeatureVersion, FeatureRegistryRecord, FeatureRecord,
)
from .identity import (
    Identity, mint_identity, validate_identity, parse_identity, IdentityError,
)
from .frequency import FrequencyFeatureEngine
from .temporal import TemporalFeatureEngine
from .connectivity import ConnectivityFeatureEngine
from .spectral import SpectralRepresentationEngine
from .topography import TopographyRepresentationEngine
from .loader import load_processed_signal, ProcessedSignalLoadError, feature_array_fingerprint
from .registry import FeatureRegistry
from .audit import make_feature_audit_log, ImmutableAuditLog, AuditError
from .lineage import make_feature_lineage, feature_version_bundle, LineageTracker, LineageRecord
from .validation import FeatureContentValidator, FeatureIntegrityValidator
from .service import FeatureEngineeringService, FeatureOutcome, FeatureEngineeringError

__all__ = [
    # versions
    "FEATURE_ENGINEERING_VERSION", "FEATURE_DOMAIN_VERSION", "FEATURE_IDENTITY_VERSION",
    "FEATURE_FREQUENCY_VERSION", "FEATURE_TEMPORAL_VERSION", "FEATURE_CONNECTIVITY_VERSION",
    "FEATURE_SPECTRAL_VERSION", "FEATURE_TOPOGRAPHY_VERSION", "FEATURE_REGISTRY_VERSION",
    "FEATURE_AUDIT_VERSION", "FEATURE_LINEAGE_VERSION", "FEATURE_VALIDATION_VERSION",
    "FEATURE_REPORT_VERSION",
    # models / vocab
    "FeatureFamily", "FeatureGroup", "FeatureScope", "FrequencyBand", "FeatureAssetStatus",
    "FeatureValidationSeverity", "FeatureIdentity", "FeatureVector", "FeatureGroupRecord",
    "FeatureMetadata", "FeatureValidationRecord", "FeatureAuditRecord", "FeatureLineageRecord",
    "FeatureVersion", "FeatureRegistryRecord", "FeatureRecord",
    # identity
    "Identity", "mint_identity", "validate_identity", "parse_identity", "IdentityError",
    # engines
    "FrequencyFeatureEngine", "TemporalFeatureEngine", "ConnectivityFeatureEngine",
    "SpectralRepresentationEngine", "TopographyRepresentationEngine",
    # loader / registry / audit / lineage / validation
    "load_processed_signal", "ProcessedSignalLoadError", "feature_array_fingerprint",
    "FeatureRegistry", "make_feature_audit_log", "ImmutableAuditLog", "AuditError",
    "make_feature_lineage", "feature_version_bundle", "LineageTracker", "LineageRecord",
    "FeatureContentValidator", "FeatureIntegrityValidator",
    # service
    "FeatureEngineeringService", "FeatureOutcome", "FeatureEngineeringError",
]
