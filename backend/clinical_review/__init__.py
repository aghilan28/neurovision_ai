"""``backend/clinical_review`` — Clinical Review Workflow (V2-P2).

Introduces structured human **review** as a first-class platform object. Where V1
produced outputs, V2 manages the human review of those outputs:

    Case → Study → Inference Artifacts → Review Session → Review Lifecycle →
    Audit Trail → Lineage Trail

A Review is versioned, traceable, auditable, recoverable, governed, linked to a Case
(V2-P1), and forward-linked to future Findings/Decisions (later versions). It
integrates with the V1 inference/artifact/lineage systems and the V2-P1 case system.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and the
sibling ``backend.clinical_cases`` subsystem; integrates with
``backend.offline_inference``. It never imports ``frontend``. Scope is strictly
V2-P2 (no findings/decisions/knowledge layers, no FHIR/EMR/hospital integration).
See ``.gcc/decisions/ADR-0003``.
"""

from __future__ import annotations

from .version import (
    CLINICAL_REVIEW_VERSION, REVIEW_DOMAIN_VERSION, REVIEW_IDENTITY_VERSION,
    REVIEW_WORKFLOW_VERSION, REVIEW_SESSION_VERSION, REVIEW_ASSIGNMENT_VERSION,
    REVIEW_TRACKING_VERSION, REVIEW_REGISTRY_VERSION, REVIEW_AUDIT_VERSION,
    REVIEW_LINEAGE_VERSION, REVIEW_VALIDATION_VERSION, REVIEW_REPORT_VERSION,
)
from .models import (
    ReviewStatus, ReviewIdentity, ReviewSession, ReviewAssignment, ReviewHistory,
    ReviewAuditRecord, ReviewLineageRecord, ReviewVersion, ReviewRegistryRecord, Review,
)
from .workflow import ReviewLifecycle, REVIEW_TRANSITIONS, ReviewLifecycleError, is_allowed_transition
from .sessions import SessionManager
from .assignment import AssignmentManager, AssignmentError, VALID_PRIORITIES
from .tracking import ReviewTracker
from .audit import make_review_audit_log
from .registry import ReviewRegistry
from .validation import ReviewValidator, ReviewValidationError
from .service import ReviewService

__all__ = [
    "CLINICAL_REVIEW_VERSION", "REVIEW_DOMAIN_VERSION", "REVIEW_IDENTITY_VERSION",
    "REVIEW_WORKFLOW_VERSION", "REVIEW_SESSION_VERSION", "REVIEW_ASSIGNMENT_VERSION",
    "REVIEW_TRACKING_VERSION", "REVIEW_REGISTRY_VERSION", "REVIEW_AUDIT_VERSION",
    "REVIEW_LINEAGE_VERSION", "REVIEW_VALIDATION_VERSION", "REVIEW_REPORT_VERSION",
    "ReviewStatus", "ReviewIdentity", "ReviewSession", "ReviewAssignment", "ReviewHistory",
    "ReviewAuditRecord", "ReviewLineageRecord", "ReviewVersion", "ReviewRegistryRecord", "Review",
    "ReviewLifecycle", "REVIEW_TRANSITIONS", "ReviewLifecycleError", "is_allowed_transition",
    "SessionManager", "AssignmentManager", "AssignmentError", "VALID_PRIORITIES",
    "ReviewTracker", "make_review_audit_log", "ReviewRegistry",
    "ReviewValidator", "ReviewValidationError", "ReviewService",
]
