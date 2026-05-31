"""``backend/clinical_validation`` — Clinical Validation & Evidence Platform (DRP-6).

Closes the audit's *insufficient clinical validation evidence* blocker: turns the
production-candidate platform into an **evidence-supported** platform with benchmark,
performance, reliability, and calibration evidence + objective comparison + validation
readiness. The scope is *validation and evidence generation* and nothing else:

    benchmark models -> evaluate performance -> measure reliability -> measure calibration
    -> generate evidence -> track validation lineage -> score validation readiness

No model-architecture / training / serving / persistence / security / frontend / deployment
changes (all out of scope) — it validates and generates evidence without modifying business
logic.

Built strictly on the existing platform: it **reuses** the DRP-2 ``ProductionModelService``
(develop + benchmark + evaluate + compare), the shared ``ml.lineage`` tracker, and the shared
``ImmutableAuditLog`` (no parallel systems). A validation record's lineage parents the
evidence node, which parents the evaluation node, which parents the benchmark node, which
parents the production-model node — so a single ``verify_chain`` proves

    Dataset -> Model -> Benchmark -> Evaluation -> Evidence -> Readiness Assessment

and reaches the patient.

Boundary (NR-8): part of the ``backend`` Application layer. Imports ``ml`` + sibling
``backend`` only; never ``frontend``. Tests live in the repository-root ``tests/``
(``tests/test_clinical_validation*.py``).
"""

from __future__ import annotations

from .version import (
    CLINICAL_VALIDATION_VERSION, CLINICAL_DOMAIN_VERSION, CLINICAL_IDENTITY_VERSION,
    CLINICAL_BENCHMARK_VERSION, CLINICAL_PERFORMANCE_VERSION, CLINICAL_RELIABILITY_VERSION,
    CLINICAL_CALIBRATION_VERSION, CLINICAL_COMPARISON_VERSION, CLINICAL_EVIDENCE_VERSION,
    CLINICAL_READINESS_VERSION, CLINICAL_REGISTRY_VERSION, CLINICAL_AUDIT_VERSION,
    CLINICAL_LINEAGE_VERSION, CLINICAL_REPORT_VERSION,
)
from .models import (
    ValidationStatus, EvidenceKind, CalibrationQuality, ReadinessClass, ReadinessDimension,
    EntityKind, ClinicalValidationIdentity, ClinicalValidationVersion, BenchmarkRecord,
    PerformanceRecord, ReliabilityRecord, CalibrationRecord, ComparisonRecord, EvidenceRecord,
    ReadinessRecord, ValidationAuditRecord, ValidationLineageRecord, ValidationRegistryRecord,
    ClinicalValidationRecord,
)
from .identity import Identity, IdentityError, mint_identity, validate_identity
from .benchmarks import build_benchmark, sensitivity_specificity
from .calibration import build_calibration
from .reliability import build_reliability
from .comparison import build_comparison, ComparisonError
from .evidence import build_evidence
from .readiness import ValidationReadinessEngine
from .registry import EvidenceRegistry, RegistryError
from .validation import ValidationContentValidator, ValidationIntegrityValidator
from .audit import make_validation_audit_log, ImmutableAuditLog, AuditError
from .lineage import (
    make_benchmark_lineage, make_evaluation_lineage, make_evidence_lineage, make_readiness_lineage,
)
from .schemas import ENTITY_CONTRACTS, validate_entity
from .service import (
    ClinicalValidationService, ValidationRunOutcome, ModelValidationOutcome, ClinicalValidationError,
)

__all__ = [
    # versions
    "CLINICAL_VALIDATION_VERSION", "CLINICAL_DOMAIN_VERSION", "CLINICAL_IDENTITY_VERSION",
    "CLINICAL_BENCHMARK_VERSION", "CLINICAL_PERFORMANCE_VERSION", "CLINICAL_RELIABILITY_VERSION",
    "CLINICAL_CALIBRATION_VERSION", "CLINICAL_COMPARISON_VERSION", "CLINICAL_EVIDENCE_VERSION",
    "CLINICAL_READINESS_VERSION", "CLINICAL_REGISTRY_VERSION", "CLINICAL_AUDIT_VERSION",
    "CLINICAL_LINEAGE_VERSION", "CLINICAL_REPORT_VERSION",
    # models / vocab
    "ValidationStatus", "EvidenceKind", "CalibrationQuality", "ReadinessClass", "ReadinessDimension",
    "EntityKind", "ClinicalValidationIdentity", "ClinicalValidationVersion", "BenchmarkRecord",
    "PerformanceRecord", "ReliabilityRecord", "CalibrationRecord", "ComparisonRecord",
    "EvidenceRecord", "ReadinessRecord", "ValidationAuditRecord", "ValidationLineageRecord",
    "ValidationRegistryRecord", "ClinicalValidationRecord",
    # identity / engines
    "Identity", "IdentityError", "mint_identity", "validate_identity", "build_benchmark",
    "sensitivity_specificity", "build_calibration", "build_reliability", "build_comparison",
    "ComparisonError", "build_evidence", "ValidationReadinessEngine",
    # registry / validation / audit / lineage / schemas
    "EvidenceRegistry", "RegistryError", "ValidationContentValidator", "ValidationIntegrityValidator",
    "make_validation_audit_log", "ImmutableAuditLog", "AuditError", "make_benchmark_lineage",
    "make_evaluation_lineage", "make_evidence_lineage", "make_readiness_lineage", "ENTITY_CONTRACTS",
    "validate_entity",
    # service
    "ClinicalValidationService", "ValidationRunOutcome", "ModelValidationOutcome",
    "ClinicalValidationError",
]
