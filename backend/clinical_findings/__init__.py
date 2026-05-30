"""``backend/clinical_findings`` — Findings & Interpretation Layer (V2-P3).

Introduces the **Finding** as a first-class platform object: a *structured clinical
observation linked to evidence* — never a prediction, probability, diagnosis, or
recommendation. Findings are permanent, versioned, traceable, auditable, lineage-
tracked, review/case/evidence-linked, recoverable, governed records. Interpretations
are modelled as a **separate** entity (never merged into the finding).

    Patient → Case → Study → Review → Evidence → Finding → Interpretation

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and the
sibling ``backend.clinical_cases`` (for identity-format validation + the audit
primitive); integrates with ``backend.offline_inference`` (V1) and
``backend.clinical_review`` (V2-P2). It never imports ``frontend``. Scope is strictly
V2-P3 — no diagnosis engines, decision support, treatment recommendations, FHIR/HL7/
EMR. See ``.gcc/decisions/ADR-0004``.
"""

from __future__ import annotations

from .version import (
    CLINICAL_FINDINGS_VERSION, FINDING_DOMAIN_VERSION, FINDING_IDENTITY_VERSION,
    FINDING_LIFECYCLE_VERSION, FINDING_EVIDENCE_VERSION, FINDING_INTERPRETATION_VERSION,
    FINDING_REGISTRY_VERSION, FINDING_AUDIT_VERSION, FINDING_LINEAGE_VERSION,
    FINDING_VALIDATION_VERSION, FINDING_REPORT_VERSION,
)
from .models import (
    FindingStatus, FindingIdentity, FindingRecord, FindingMetadata, FindingEvidence,
    FindingInterpretation, FindingVersion, FindingAuditRecord, FindingLineageRecord,
    FindingRegistryRecord, Finding,
)
from .identity import mint_finding, mint_evidence, mint_interpretation, validate_identity, FindingIdentityError
from .lifecycle import FindingLifecycle, FINDING_TRANSITIONS, FindingLifecycleError, is_allowed_transition
from .evidence import EvidenceManager, evidence_spec, VALID_EVIDENCE_TYPES, EvidenceError
from .interpretation import InterpretationManager, VALID_INTERPRETATION_TYPES, InterpretationError
from .audit import make_finding_audit_log
from .registry import FindingRegistry
from .validation import FindingValidator, FindingValidationError
from .service import FindingService

__all__ = [
    "CLINICAL_FINDINGS_VERSION", "FINDING_DOMAIN_VERSION", "FINDING_IDENTITY_VERSION",
    "FINDING_LIFECYCLE_VERSION", "FINDING_EVIDENCE_VERSION", "FINDING_INTERPRETATION_VERSION",
    "FINDING_REGISTRY_VERSION", "FINDING_AUDIT_VERSION", "FINDING_LINEAGE_VERSION",
    "FINDING_VALIDATION_VERSION", "FINDING_REPORT_VERSION",
    "FindingStatus", "FindingIdentity", "FindingRecord", "FindingMetadata", "FindingEvidence",
    "FindingInterpretation", "FindingVersion", "FindingAuditRecord", "FindingLineageRecord",
    "FindingRegistryRecord", "Finding",
    "mint_finding", "mint_evidence", "mint_interpretation", "validate_identity", "FindingIdentityError",
    "FindingLifecycle", "FINDING_TRANSITIONS", "FindingLifecycleError", "is_allowed_transition",
    "EvidenceManager", "evidence_spec", "VALID_EVIDENCE_TYPES", "EvidenceError",
    "InterpretationManager", "VALID_INTERPRETATION_TYPES", "InterpretationError",
    "make_finding_audit_log", "FindingRegistry", "FindingValidator", "FindingValidationError",
    "FindingService",
]
