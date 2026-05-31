"""``backend/real_model_training/audit`` — immutable training audit log (T2-I).

Reuses the platform's single tamper-evident :class:`ImmutableAuditLog` (no parallel audit
system), bound to :class:`TrainingAuditRecord`. Every window/train/evaluate/benchmark/
compare/score/register event is appended immutably and is tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import AuditError, ImmutableAuditLog

from ..models.domain import TrainingAuditRecord


def make_training_audit_log() -> ImmutableAuditLog:
    return ImmutableAuditLog(record_cls=TrainingAuditRecord)


__all__ = ["make_training_audit_log", "ImmutableAuditLog", "AuditError"]
