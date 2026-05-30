"""``backend/operational_recommendations`` — Operational Recommendation Layer (V3-P6).

Creates **explainable operational recommendations**: guidance, prioritization,
optimization suggestions, and escalation candidates. This is **not** clinical
decision support, medical advice, diagnosis, or treatment — it operates
**exclusively on operational intelligence** (V3-P5 analytics + V3-P3 workflows +
V3-P4 graph + V3-P1/P2 events/temporal).

Every recommendation is **explainable, traceable, auditable, lineage-tracked,
governed, evidence-linked, analytics-linked, workflow-linked and graph-linked** —
no black-box recommendations. The governance gate's **risk** dimension fails any
recommendation that is not both evidence-linked and analytics-linked. Each
recommendation is a **suggestion only**: nothing is executed, nothing is
auto-escalated. Its lineage parents are the analytics nodes it cites, so
``verify_chain`` spans Patient -> ... -> Analytics -> Recommendation. Shares the
platform's single ``ml.lineage.LineageTracker`` and the shared ``ImmutableAuditLog``
— no parallel lineage/audit.

Engines: context (aggregate analytics/workflow/graph/temporal/risk/health context
bundles), guidance (workflow/review-queue/escalation/operational/resource-awareness
guidance, each citing evidence), prioritization (explainable priority levels +
reasons + supporting signals), optimization (workflow/dependency/queue/process
suggestions — no execution), and escalation (candidates + reasons + evidence + risk
context + priority — no automatic escalation).

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and the
sibling V3 subsystems it derives from; never imports ``frontend``. Scope is strictly
V3-P6 — no dashboards, no realtime/autonomous execution, no auto escalation, no
clinical recommendations/diagnosis/treatment, no FHIR/HL7/EMR, no V4. See
``.gcc/decisions/ADR-0009``.
"""

from __future__ import annotations

from .version import (
    OPERATIONAL_RECOMMENDATIONS_VERSION, RECOMMENDATION_DOMAIN_VERSION,
    RECOMMENDATION_IDENTITY_VERSION, RECOMMENDATION_CONTEXT_VERSION,
    RECOMMENDATION_EVIDENCE_VERSION, RECOMMENDATION_PRIORITY_VERSION,
    RECOMMENDATION_REGISTRY_VERSION, RECOMMENDATION_AUDIT_VERSION,
    RECOMMENDATION_LINEAGE_VERSION, RECOMMENDATION_VALIDATION_VERSION,
    RECOMMENDATION_REPORT_VERSION,
)
from .identity import (
    RecommendationIdentity, RecommendationIdentityError, mint_recommendation, validate_identity,
)
from .models import (
    RecommendationKind, RecommendationKindError, RECOMMENDATION_KINDS,
    PriorityLevel, PRIORITY_RANK, PRIORITY_LEVELS, is_kind, validate_kind, is_priority,
    priority_rank, RecommendationEvidence, RecommendationContext, RecommendationPriority,
    RecommendationRecord, RecommendationAuditRecord, RecommendationVersion,
    RecommendationLineageRecord, RecommendationRegistryRecord,
)
from .models.source import RecommendationSourceView
from .context import ContextEngine
from .guidance import GuidanceEngine
from .prioritization import PrioritizationEngine, level_for_score
from .optimization import OptimizationEngine
from .escalation import EscalationEngine, ESCALATION_THRESHOLD
from .audit import make_recommendation_audit_log
from .registry import RecommendationRegistry
from .validation import (
    RecommendationGovernanceGate, RecommendationValidator, RecommendationValidationError,
)
from .service import OperationalRecommendationService

__all__ = [
    "OPERATIONAL_RECOMMENDATIONS_VERSION", "RECOMMENDATION_DOMAIN_VERSION",
    "RECOMMENDATION_IDENTITY_VERSION", "RECOMMENDATION_CONTEXT_VERSION",
    "RECOMMENDATION_EVIDENCE_VERSION", "RECOMMENDATION_PRIORITY_VERSION",
    "RECOMMENDATION_REGISTRY_VERSION", "RECOMMENDATION_AUDIT_VERSION",
    "RECOMMENDATION_LINEAGE_VERSION", "RECOMMENDATION_VALIDATION_VERSION",
    "RECOMMENDATION_REPORT_VERSION",
    "RecommendationIdentity", "RecommendationIdentityError", "mint_recommendation",
    "validate_identity",
    "RecommendationKind", "RecommendationKindError", "RECOMMENDATION_KINDS",
    "PriorityLevel", "PRIORITY_RANK", "PRIORITY_LEVELS", "is_kind", "validate_kind",
    "is_priority", "priority_rank",
    "RecommendationEvidence", "RecommendationContext", "RecommendationPriority",
    "RecommendationRecord", "RecommendationAuditRecord", "RecommendationVersion",
    "RecommendationLineageRecord", "RecommendationRegistryRecord", "RecommendationSourceView",
    "ContextEngine", "GuidanceEngine", "PrioritizationEngine", "level_for_score",
    "OptimizationEngine", "EscalationEngine", "ESCALATION_THRESHOLD",
    "make_recommendation_audit_log", "RecommendationRegistry",
    "RecommendationGovernanceGate", "RecommendationValidator", "RecommendationValidationError",
    "OperationalRecommendationService",
]
