"""``backend/signal_processing/audit`` — immutable signal audit log (P2-I).

Reuses the platform's single tamper-evident :class:`ImmutableAuditLog` (no parallel
audit system) bound to :class:`SignalAuditRecord`.
"""

from __future__ import annotations

from .audit import make_signal_audit_log, ImmutableAuditLog, AuditError

__all__ = ["make_signal_audit_log", "ImmutableAuditLog", "AuditError"]
