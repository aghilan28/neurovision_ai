"""``backend/clinical_cases`` — Clinical Case Foundation (V2-P1).

Introduces the **Case** as the platform's first-class organizational object. The
platform stops thinking in files and starts thinking in:

    Patient → Case → Study → (Review → Finding → Decision, in later phases)

A Case is a permanent, versioned, traceable, auditable, recoverable, reviewable,
governed, lineage-tracked record that never depends on filenames or folder
structure and survives future architecture evolution.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` (for
provenance/lineage/validation) and integrates with ``backend.offline_inference``
(V1). It never imports ``frontend``. Scope is strictly V2-P1 (no findings/decisions/
knowledge layers, no FHIR/EMR/hospital integration). See ``.gcc/decisions/ADR-0003``.
"""

from __future__ import annotations

from .version import (
    CLINICAL_CASES_VERSION, CASE_DOMAIN_VERSION, CASE_IDENTITY_VERSION,
    CASE_LIFECYCLE_VERSION, CASE_REGISTRY_VERSION, CASE_AUDIT_VERSION,
    CASE_LINEAGE_VERSION, CASE_VALIDATION_VERSION, CASE_REPORT_VERSION,
)
from .models import (
    CaseStatus, PatientIdentity, CaseIdentity, StudyIdentity, CaseMetadata,
    CaseState, CaseAuditRecord, CaseLineageRecord, CaseVersion, CaseRegistryRecord, Case,
)
from .identity import Identity, mint_identity, validate_identity, IDENTITY_POLICIES, IdentityError
from .lifecycle import CaseLifecycle, CASE_TRANSITIONS, LifecycleError, is_allowed_transition
from .audit import ImmutableAuditLog, AuditError
from .registry import CaseRegistry
from .validation import CaseValidator, CaseValidationError
from .service import CaseService

__all__ = [
    "CLINICAL_CASES_VERSION", "CASE_DOMAIN_VERSION", "CASE_IDENTITY_VERSION",
    "CASE_LIFECYCLE_VERSION", "CASE_REGISTRY_VERSION", "CASE_AUDIT_VERSION",
    "CASE_LINEAGE_VERSION", "CASE_VALIDATION_VERSION", "CASE_REPORT_VERSION",
    "CaseStatus", "PatientIdentity", "CaseIdentity", "StudyIdentity", "CaseMetadata",
    "CaseState", "CaseAuditRecord", "CaseLineageRecord", "CaseVersion", "CaseRegistryRecord", "Case",
    "Identity", "mint_identity", "validate_identity", "IDENTITY_POLICIES", "IdentityError",
    "CaseLifecycle", "CASE_TRANSITIONS", "LifecycleError", "is_allowed_transition",
    "ImmutableAuditLog", "AuditError",
    "CaseRegistry", "CaseValidator", "CaseValidationError", "CaseService",
]
