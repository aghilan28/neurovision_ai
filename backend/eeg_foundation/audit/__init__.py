"""``backend/eeg_foundation/audit`` — immutable EEG audit log (P1-G).

Reuses the platform's single tamper-evident :class:`ImmutableAuditLog` (no parallel
audit system) bound to :class:`EEGAuditRecord`.
"""

from __future__ import annotations

from .audit import make_eeg_audit_log, ImmutableAuditLog, AuditError

__all__ = ["make_eeg_audit_log", "ImmutableAuditLog", "AuditError"]
