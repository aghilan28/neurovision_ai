"""``backend/clinical_knowledge/audit`` — immutable knowledge audit log (V2-P4).

Reuses the shared tamper-evident ``ImmutableAuditLog`` (NR-6), bound to
``KnowledgeAuditRecord``.
"""

from __future__ import annotations

from .audit import make_knowledge_audit_log, ImmutableAuditLog, AuditError

__all__ = ["make_knowledge_audit_log", "ImmutableAuditLog", "AuditError"]
