"""``backend/governance_intelligence`` — Governance Intelligence Layer (V4-P7).

Makes **governance a first-class intelligence system**: governance becomes
observable, analyzable, auditable, and explainable. This layer does **not** create
new governance rules, modify governance state, or bypass policy/approval workflows —
it creates *intelligence about governance*, derived deterministically from the
already-governed Version 4 artifacts (goals, policies, constraints, plans, tasks,
agents, executions).

It answers the questions the platform previously could not: *what governance risks
exist? what governance violations exist? which executions require intervention?
which approvals are bottlenecks? what operational state requires human review?* —
through approval intelligence, violation intelligence, escalation intelligence, a
governance risk engine, and governance analytics.

Every governance-intelligence record is versioned, traceable, auditable,
lineage-tracked, deterministic, governed, and explainable. Its lineage parents are
the lineage nodes of the artifacts it observed, so ``verify_chain`` reaches the
patient. Shares the platform's single ``ml.lineage.LineageTracker`` and the shared
``ImmutableAuditLog`` — no parallel lineage/audit/governance.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and
sibling ``backend`` subsystems; never imports ``frontend``. Scope is strictly V4-P7
— governance intelligence only (no governance-rule creation, no autonomous policy
updates, no simulation/scenario/forecasting engines, no Version 5 features).
"""

from __future__ import annotations

from .version import (
    GOVERNANCE_INTELLIGENCE_VERSION, GOVERNANCE_DOMAIN_VERSION, GOVERNANCE_IDENTITY_VERSION,
    GOVERNANCE_OBSERVATION_VERSION, GOVERNANCE_APPROVAL_VERSION, GOVERNANCE_VIOLATION_VERSION,
    GOVERNANCE_ESCALATION_VERSION, GOVERNANCE_RISK_VERSION, GOVERNANCE_ANALYTICS_VERSION,
    GOVERNANCE_METRIC_VERSION, GOVERNANCE_GOVERNANCE_VERSION, GOVERNANCE_REGISTRY_VERSION,
    GOVERNANCE_AUDIT_VERSION, GOVERNANCE_LINEAGE_VERSION, GOVERNANCE_VALIDATION_VERSION,
    GOVERNANCE_REPORT_VERSION,
)
from .identity import (
    GovernanceIntelligenceIdentity, GovernanceIdentityError, mint_intelligence, mint_approval,
    mint_violation, mint_escalation, mint_risk, validate_identity,
)
from .models import (
    GovernedKind, GOVERNED_KINDS, Severity, SEVERITIES, ViolationType, VIOLATION_TYPES,
    RiskDimension, RISK_DIMENSIONS, RiskLevel, risk_level_for, ApprovalRecord, ViolationRecord,
    EscalationRecord, GovernanceRiskRecord, GovernanceMetric, GovernanceVersion,
    GovernanceAuditRecord, GovernanceLineageRecord, GovernanceRegistryRecord,
    GovernanceIntelligenceRecord, GovernedObservation, GovernanceObservationView, observe_record,
)
from .approvals import build_approvals, approval_metrics, approval_bottlenecks
from .violations import detect_violations, violation_summary
from .escalations import build_escalations, escalation_summary
from .risk import build_risks, risk_summary, highest_risks
from .analytics import (
    governance_health, build_metrics, governance_trends, governance_bottlenecks,
)
from .monitoring import (
    executions_requiring_intervention, state_requiring_review, monitoring_summary,
)
from .governance import GovernanceIntelligenceGate, GovernanceIntelligenceError
from .registry import GovernanceRegistry
from .validation import GovernanceValidator
from .audit import make_governance_audit_log
from .service import GovernanceIntelligenceService

__all__ = [
    "GOVERNANCE_INTELLIGENCE_VERSION", "GOVERNANCE_DOMAIN_VERSION", "GOVERNANCE_IDENTITY_VERSION",
    "GOVERNANCE_OBSERVATION_VERSION", "GOVERNANCE_APPROVAL_VERSION", "GOVERNANCE_VIOLATION_VERSION",
    "GOVERNANCE_ESCALATION_VERSION", "GOVERNANCE_RISK_VERSION", "GOVERNANCE_ANALYTICS_VERSION",
    "GOVERNANCE_METRIC_VERSION", "GOVERNANCE_GOVERNANCE_VERSION", "GOVERNANCE_REGISTRY_VERSION",
    "GOVERNANCE_AUDIT_VERSION", "GOVERNANCE_LINEAGE_VERSION", "GOVERNANCE_VALIDATION_VERSION",
    "GOVERNANCE_REPORT_VERSION",
    "GovernanceIntelligenceIdentity", "GovernanceIdentityError", "mint_intelligence",
    "mint_approval", "mint_violation", "mint_escalation", "mint_risk", "validate_identity",
    "GovernedKind", "GOVERNED_KINDS", "Severity", "SEVERITIES", "ViolationType",
    "VIOLATION_TYPES", "RiskDimension", "RISK_DIMENSIONS", "RiskLevel", "risk_level_for",
    "ApprovalRecord", "ViolationRecord", "EscalationRecord", "GovernanceRiskRecord",
    "GovernanceMetric", "GovernanceVersion", "GovernanceAuditRecord", "GovernanceLineageRecord",
    "GovernanceRegistryRecord", "GovernanceIntelligenceRecord", "GovernedObservation",
    "GovernanceObservationView", "observe_record",
    "build_approvals", "approval_metrics", "approval_bottlenecks", "detect_violations",
    "violation_summary", "build_escalations", "escalation_summary", "build_risks",
    "risk_summary", "highest_risks", "governance_health", "build_metrics", "governance_trends",
    "governance_bottlenecks", "executions_requiring_intervention", "state_requiring_review",
    "monitoring_summary", "GovernanceIntelligenceGate", "GovernanceIntelligenceError",
    "GovernanceRegistry", "GovernanceValidator", "make_governance_audit_log",
    "GovernanceIntelligenceService",
]
