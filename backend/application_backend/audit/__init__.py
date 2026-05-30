"""``backend/application_backend/audit`` — immutable application audit log (P6-J).

Reuses the platform's single tamper-evident :class:`ImmutableAuditLog` (no parallel
audit system) bound to :class:`BackendAuditRecord`.
"""

from __future__ import annotations

from .audit import make_backend_audit_log, ImmutableAuditLog, AuditError

__all__ = ["make_backend_audit_log", "ImmutableAuditLog", "AuditError"]
