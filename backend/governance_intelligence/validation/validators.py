"""Governance-intelligence validation — the mandated integrity checks (V4-P7).

``GovernanceValidator`` verifies a registered governance-intelligence record's
integrity across the mandated dimensions: identity, approval, violation, escalation,
risk, registry, audit, lineage, and version. It reuses the shared
``ml.validation.ValidationReport``.
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import (
    validate_identity, validate_approval_identity, validate_violation_identity,
    validate_escalation_identity, validate_risk_identity,
)
from ..models.domain import (
    GovernanceIntelligenceRecord, GovernanceVersion, GOVERNED_KINDS, VIOLATION_TYPES,
    RISK_DIMENSIONS,
)


class GovernanceValidator:
    """Validates integrity of a registered governance-intelligence record."""

    def validate(self, *, record: GovernanceIntelligenceRecord, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        iid = record.intelligence_id

        # 1. identity integrity
        report.add("identity_integrity", validate_identity(iid)[0] and bool(record.scope),
                   f"intelligence_id={iid} scope={record.scope}")

        # 2. approval integrity — well-formed ids, known kinds, bounded latency
        appr_ok = all(validate_approval_identity(a.approval_id)[0]
                      and a.entity_kind in GOVERNED_KINDS and a.latency_steps >= 0
                      for a in record.approvals)
        report.add("approval_integrity", bool(appr_ok), f"{len(record.approvals)} approval(s)")

        # 3. violation integrity — well-formed ids + known types
        viol_ok = all(validate_violation_identity(v.violation_id)[0]
                      and v.violation_type in VIOLATION_TYPES for v in record.violations)
        report.add("violation_integrity", bool(viol_ok), f"{len(record.violations)} violation(s)")

        # 4. escalation integrity — well-formed ids + non-negative delay
        esc_ok = all(validate_escalation_identity(e.escalation_id)[0] and e.delay_steps >= 0
                     for e in record.escalations)
        report.add("escalation_integrity", bool(esc_ok), f"{len(record.escalations)} escalation(s)")

        # 5. risk integrity — well-formed ids, known dimensions, bounded scores, explainable
        risk_ok = all(validate_risk_identity(r.risk_id)[0] and r.dimension in RISK_DIMENSIONS
                      and 0.0 <= r.score <= 1.0 and r.factors and r.explanation
                      for r in record.risks)
        report.add("risk_integrity", bool(risk_ok), f"{len(record.risks)} risk(s)")

        # 6. registry integrity — registered at this version + lineage
        try:
            rec = registry.get(iid)
            ok = rec.version == record.version and rec.lineage_id == record.lineage_id
            report.add("registry_integrity", bool(ok),
                       f"registered version={rec.version} record version={record.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 7. audit integrity — chain verifies + the record's head is in the log
        try:
            heads = {e.event_hash for e in audit_log.events()}
            ok = audit_log.verify() and (record.audit_state in heads)
            report.add("audit_integrity", bool(ok), f"chain_verified={audit_log.verify()}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 8. lineage integrity — the record's lineage chain verifies
        try:
            chain_ok = bool(record.lineage_id) and lineage_tracker.verify_chain(record.lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 9. version integrity — recorded version == recomputed content-addressed version
        try:
            expected = GovernanceVersion.compute(record.state_signature(), record.version_previous())
            report.add("version_integrity", record.version == expected,
                       f"recorded={record.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report
