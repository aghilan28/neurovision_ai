"""Audit persistence (DRP4-F).

Persists hash-chained audit logs (events + chain head + metadata) to durable storage and
recovers them by **replaying** the events into the shared :class:`ImmutableAuditLog` — which
recomputes the chain deterministically, so a recovered log reproduces the same head and
re-verifies (immutable, append-only, traceable). No parallel audit system.
"""

from __future__ import annotations

from typing import Any

from backend.clinical_cases.audit import ImmutableAuditLog  # reuse the shared implementation

from ..models.domain import AuditStorageRecord, PersistenceAuditRecord, StorageNamespace, StorageRecord
from ..storage import StorageEngine
from ..version import DETERMINISTIC_EPOCH


class AuditPersistenceError(RuntimeError):
    """Raised when a recovered audit chain fails to reproduce the persisted head."""


class AuditStore:
    """Persists + recovers append-only audit logs."""

    def __init__(self, engine: StorageEngine):
        self.engine = engine

    def persist(self, name: str, audit_log: Any) -> tuple[StorageRecord, AuditStorageRecord]:
        snapshot = {
            "log_name": name, "head": audit_log.head, "n_events": len(audit_log),
            "events": [{"seq": e.seq, "kind": e.kind, "payload": e.payload,
                        "prev_hash": e.prev_hash, "event_hash": e.event_hash,
                        "created_at": e.created_at} for e in audit_log.events()],
        }
        sr = self.engine.put(StorageNamespace.AUDIT, name, snapshot)
        asr = AuditStorageRecord(log_name=name, n_events=len(audit_log), head=audit_log.head,
                                 fingerprint=sr.fingerprint, storage_id=sr.storage_id)
        return sr, asr

    def recover(self, storage_record: StorageRecord) -> ImmutableAuditLog:
        snapshot = self.engine.get(storage_record.namespace, storage_record.key,
                                   expected_checksum=storage_record.checksum)
        log = ImmutableAuditLog(record_cls=PersistenceAuditRecord)
        for ev in snapshot["events"]:
            log.append(ev["kind"], ev["payload"], created_at=ev.get("created_at", DETERMINISTIC_EPOCH))
        if log.head != snapshot["head"] or not log.verify():
            raise AuditPersistenceError(
                f"recovered audit log {snapshot['log_name']!r} did not reproduce the persisted head")
        return log


__all__ = ["AuditStore", "AuditPersistenceError"]
