"""``backend/decision_support`` — Decision Support Layer (V2-P6).

Structured, **explainable decision support** for clinical reviewers. It helps a
reviewer understand **what matters, why it matters, what evidence supports it, and
what uncertainty exists** — and nothing more. It **never** diagnoses, treats,
prescribes, issues clinical orders, or acts autonomously; the clinician is always
the decision-maker. These limits are enforced mechanically by the
``DecisionScopeGuard`` (the gate's risk validation + the validator's
``decision_scope_integrity`` check).

Per case it produces: a deterministic ``DecisionContext``; an ``EvidenceBundle``
that surfaces *all* evidence ranked (nothing hidden); an explainable ``RiskContext``
(review-attention risk aggregated from the **recorded** V1 uncertainty + V2
completeness — never recomputed); an explainable ``PrioritizationRecord`` (factor
contributions sum to the score); a process-only ``GuidanceRecord``; and a
``DecisionSupportRecord`` tying them together. Every artifact is versioned,
governed, immutably audited, and lineage-tracked back to the patient roots.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and the
sibling V2 subsystems (incl. ``multi_case_intelligence`` for the population view).
It never imports ``frontend``. Scope is strictly V2-P6 — no diagnosis engines, no
treatment/medication, no clinical orders, no autonomy, no FHIR/HL7/EMR, no
real-time. See ``.gcc/decisions/ADR-0005``.
"""

from __future__ import annotations

from .version import (
    DECISION_SUPPORT_VERSION, DECISION_DOMAIN_VERSION, DECISION_IDENTITY_VERSION,
    DECISION_CONTEXT_VERSION, DECISION_EVIDENCE_VERSION, DECISION_RISK_VERSION,
    DECISION_PRIORITIZATION_VERSION, DECISION_GUIDANCE_VERSION, DECISION_REGISTRY_VERSION,
    DECISION_AUDIT_VERSION, DECISION_LINEAGE_VERSION, DECISION_VALIDATION_VERSION,
    DECISION_REPORT_VERSION,
)
from .models import (
    RiskBand, PriorityLevel, GuidanceCategory,
    DecisionContext, EvidenceSummary, EvidenceBundle, RiskComponent, RiskContext,
    PriorityFactor, PrioritizationRecord, GuidanceItem, GuidanceRecord,
    DecisionSupportRecord, DecisionReport,
    DecisionAuditRecord, DecisionVersion, DecisionLineageRecord, DecisionRegistryRecord,
)
from .identity import (
    DecisionIdentity, DecisionIdentityError, mint_context, mint_evidence_bundle, mint_risk_context,
    mint_prioritization, mint_guidance, mint_decision_support, mint_report, validate_identity,
)
from .context import ContextAggregator
from .evidence import EvidenceBundler
from .risk import RiskContextAggregator
from .prioritization import Prioritizer
from .guidance import GuidanceGenerator
from .audit import make_decision_audit_log
from .registry import DecisionRegistry
from .validation import (
    DecisionScopeGuard, DecisionGovernanceGate, DecisionValidator, DecisionValidationError,
)
from .service import DecisionSupportService, DecisionBundle

__all__ = [
    "DECISION_SUPPORT_VERSION", "DECISION_DOMAIN_VERSION", "DECISION_IDENTITY_VERSION",
    "DECISION_CONTEXT_VERSION", "DECISION_EVIDENCE_VERSION", "DECISION_RISK_VERSION",
    "DECISION_PRIORITIZATION_VERSION", "DECISION_GUIDANCE_VERSION", "DECISION_REGISTRY_VERSION",
    "DECISION_AUDIT_VERSION", "DECISION_LINEAGE_VERSION", "DECISION_VALIDATION_VERSION",
    "DECISION_REPORT_VERSION",
    "RiskBand", "PriorityLevel", "GuidanceCategory",
    "DecisionContext", "EvidenceSummary", "EvidenceBundle", "RiskComponent", "RiskContext",
    "PriorityFactor", "PrioritizationRecord", "GuidanceItem", "GuidanceRecord",
    "DecisionSupportRecord", "DecisionReport",
    "DecisionAuditRecord", "DecisionVersion", "DecisionLineageRecord", "DecisionRegistryRecord",
    "DecisionIdentity", "DecisionIdentityError", "mint_context", "mint_evidence_bundle",
    "mint_risk_context", "mint_prioritization", "mint_guidance", "mint_decision_support",
    "mint_report", "validate_identity",
    "ContextAggregator", "EvidenceBundler", "RiskContextAggregator", "Prioritizer",
    "GuidanceGenerator", "make_decision_audit_log", "DecisionRegistry",
    "DecisionScopeGuard", "DecisionGovernanceGate", "DecisionValidator", "DecisionValidationError",
    "DecisionSupportService", "DecisionBundle",
]
