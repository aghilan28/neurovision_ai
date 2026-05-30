"""``backend/clinical_cases/audit`` — immutable, tamper-evident audit log (V2-P1).

An append-only, hash-chained log: each event embeds the previous event's hash, so
any modification or reordering is detectable (``verify``). Every event is
immutable once appended. Reused by the review subsystem (V2-P2) via a record-class
parameter.
"""

from __future__ import annotations

from .audit import ImmutableAuditLog, AuditError, compute_event_hash

__all__ = ["ImmutableAuditLog", "AuditError", "compute_event_hash"]
