"""``backend/feature_engineering/audit`` — immutable feature audit log (P3-J).

Reuses the platform's single tamper-evident :class:`ImmutableAuditLog` (no parallel
audit system) bound to :class:`FeatureAuditRecord`.
"""

from __future__ import annotations

from .audit import make_feature_audit_log, ImmutableAuditLog, AuditError

__all__ = ["make_feature_audit_log", "ImmutableAuditLog", "AuditError"]
