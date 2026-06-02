"""``backend/model_foundation/audit`` — immutable model audit log (P4-J).

Reuses the platform's single tamper-evident :class:`ImmutableAuditLog` (no parallel
audit system) bound to :class:`ModelAuditRecord`.
"""

from __future__ import annotations

from .audit import make_model_audit_log, ImmutableAuditLog, AuditError

__all__ = ["make_model_audit_log", "ImmutableAuditLog", "AuditError"]
