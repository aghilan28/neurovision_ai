"""Immutable, hash-chained audit log.

Generic over the record class so both the case and review subsystems share one
tamper-evident implementation. Each appended event carries:

  ``event_hash = hash(seq, kind, payload, prev_hash, created_at)``

and ``prev_hash`` links to the previous event. The chain head is the last
``event_hash``; ``verify()`` recomputes the whole chain to detect any tampering.
The log exposes no mutation API beyond ``append`` (events are permanent).
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import DETERMINISTIC_EPOCH
from ..models.domain import CaseAuditRecord

GENESIS = "0" * 16


class AuditError(RuntimeError):
    """Raised when the audit chain fails verification."""


def compute_event_hash(seq: int, kind: str, payload: Mapping[str, Any],
                       prev_hash: str, created_at: str) -> str:
    return hash_obj({"seq": seq, "kind": kind, "payload": dict(payload),
                     "prev_hash": prev_hash, "created_at": created_at})


class ImmutableAuditLog:
    """An append-only, hash-chained audit log.

    ``record_cls`` must accept ``(seq, kind, payload, prev_hash, event_hash,
    created_at)`` — both ``CaseAuditRecord`` and ``ReviewAuditRecord`` do.
    """

    def __init__(self, record_cls: Callable[..., Any] = CaseAuditRecord):
        self._record_cls = record_cls
        self._events: list = []

    @property
    def head(self) -> str:
        """The current chain head hash (``GENESIS`` for an empty log)."""
        return self._events[-1].event_hash if self._events else GENESIS

    def __len__(self) -> int:
        return len(self._events)

    def append(self, kind: str, payload: Mapping[str, Any],
               created_at: str = DETERMINISTIC_EPOCH):
        """Append an immutable event; returns the created record."""
        seq = len(self._events)
        prev = self.head
        event_hash = compute_event_hash(seq, kind, payload, prev, created_at)
        record = self._record_cls(seq=seq, kind=kind, payload=dict(payload),
                                  prev_hash=prev, event_hash=event_hash, created_at=created_at)
        self._events.append(record)
        return record

    def events(self) -> list:
        return list(self._events)

    def verify(self) -> bool:
        """Recompute the chain; return True iff every link and hash is intact."""
        prev = GENESIS
        for i, ev in enumerate(self._events):
            if ev.seq != i or ev.prev_hash != prev:
                return False
            expected = compute_event_hash(ev.seq, ev.kind, ev.payload, ev.prev_hash, ev.created_at)
            if expected != ev.event_hash:
                return False
            prev = ev.event_hash
        return True

    def raise_if_tampered(self) -> None:
        if not self.verify():
            raise AuditError("audit chain verification failed (tampering detected)")

    def to_dict(self) -> dict:
        return {"n_events": len(self._events), "head": self.head,
                "events": [e.to_dict() for e in self._events]}
