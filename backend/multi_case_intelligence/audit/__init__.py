"""Intelligence audit system.

An append-only, hash-chained, deterministic audit log. Entries are immutable
:class:`AuditEvent` records ordered by a *logical* sequence number. Any tampering
with an earlier entry invalidates every subsequent entry's hash.
"""

from backend.multi_case_intelligence.audit.log import IntelligenceAuditLog

__all__ = ["IntelligenceAuditLog"]
