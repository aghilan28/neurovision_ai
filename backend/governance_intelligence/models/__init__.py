"""Governance-intelligence domain entities (V4-P7)."""

from __future__ import annotations

from .domain import (
    GovernedKind, GOVERNED_KINDS, Severity, SEVERITY_RANK, SEVERITIES,
    ViolationType, VIOLATION_TYPES, RiskDimension, RISK_DIMENSIONS, RiskLevel, risk_level_for,
    ApprovalRecord, ViolationRecord, EscalationRecord, GovernanceRiskRecord, GovernanceMetric,
    GovernanceVersion, GovernanceAuditRecord, GovernanceLineageRecord, GovernanceRegistryRecord,
    GovernanceIntelligenceRecord,
)
from .observation import GovernedObservation, GovernanceObservationView, observe_record

__all__ = [
    "GovernedKind", "GOVERNED_KINDS", "Severity", "SEVERITY_RANK", "SEVERITIES",
    "ViolationType", "VIOLATION_TYPES", "RiskDimension", "RISK_DIMENSIONS", "RiskLevel",
    "risk_level_for", "ApprovalRecord", "ViolationRecord", "EscalationRecord",
    "GovernanceRiskRecord", "GovernanceMetric", "GovernanceVersion", "GovernanceAuditRecord",
    "GovernanceLineageRecord", "GovernanceRegistryRecord", "GovernanceIntelligenceRecord",
    "GovernedObservation", "GovernanceObservationView", "observe_record",
]
