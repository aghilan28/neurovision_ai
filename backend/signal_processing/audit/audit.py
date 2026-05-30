"""Signal audit log = the shared ImmutableAuditLog bound to ``SignalAuditRecord``.

No parallel audit system: the Signal Processing layer reuses the platform's single
hash-chained :class:`ImmutableAuditLog` (V2-P1), parameterised with
:class:`SignalAuditRecord`. Every load / quality / detection / filtering / removal /
storage / lineage / version / registration event is appended immutably and is
tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import SignalAuditRecord


def make_signal_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained signal audit log."""
    return ImmutableAuditLog(record_cls=SignalAuditRecord)


__all__ = ["make_signal_audit_log", "ImmutableAuditLog", "AuditError"]
