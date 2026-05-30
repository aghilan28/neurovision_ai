"""Decision audit log.

Reuses the shared, tamper-evident, hash-chained log from the intelligence layer.
``DecisionAuditRecord`` is the decision-layer name for an audit event so callers
can refer to the directive's entity directly.
"""

from __future__ import annotations

from backend.multi_case_intelligence.audit.log import IntelligenceAuditLog
from backend.multi_case_intelligence.schemas.events import AuditAction, AuditEvent

# The directive's "DecisionAuditRecord" entity == a shared immutable AuditEvent.
DecisionAuditRecord = AuditEvent


class DecisionAuditLog(IntelligenceAuditLog):
    """Append-only, hash-chained audit log for decision-support events."""


__all__ = ["DecisionAuditLog", "DecisionAuditRecord", "AuditAction"]
