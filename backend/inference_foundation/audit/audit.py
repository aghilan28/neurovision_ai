"""Inference audit log = the shared ImmutableAuditLog bound to ``InferenceAuditRecord``.

No parallel audit system: the Clinical Inference layer reuses the platform's single
hash-chained :class:`ImmutableAuditLog` (V2-P1), parameterised with
:class:`InferenceAuditRecord`. Every execution / prediction / confidence / calibration
/ explanation / validation / lineage / version / registration event is appended
immutably and is tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import InferenceAuditRecord


def make_inference_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained inference audit log."""
    return ImmutableAuditLog(record_cls=InferenceAuditRecord)


__all__ = ["make_inference_audit_log", "ImmutableAuditLog", "AuditError"]
