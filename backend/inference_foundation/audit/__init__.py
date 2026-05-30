"""``backend/inference_foundation/audit`` — immutable inference audit log (P5-J).

Reuses the platform's single tamper-evident :class:`ImmutableAuditLog` (no parallel
audit system) bound to :class:`InferenceAuditRecord`.
"""

from __future__ import annotations

from .audit import make_inference_audit_log, ImmutableAuditLog, AuditError

__all__ = ["make_inference_audit_log", "ImmutableAuditLog", "AuditError"]
