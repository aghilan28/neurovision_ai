"""Append-only, hash-chained intelligence audit log.

The log is the only mutable object in the audit subsystem, and it is mutable in
exactly one way: appending. It never rewrites or deletes an entry. Ordering is a
logical counter (no wall-clock), so replaying the same sequence of actions
reproduces an identical log with identical hashes.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from backend.multi_case_intelligence.schemas.base import ArtifactRef
from backend.multi_case_intelligence.schemas.determinism import GENESIS_HASH
from backend.multi_case_intelligence.schemas.events import AuditAction, AuditEvent


class IntelligenceAuditLog:
    """An immutable-by-policy, hash-chained sequence of audit events."""

    def __init__(self) -> None:
        self._entries: list[AuditEvent] = []

    @property
    def head_hash(self) -> str:
        """Hash of the latest entry (or the genesis hash if empty)."""
        return self._entries[-1].entry_hash if self._entries else GENESIS_HASH

    def record(
        self,
        action: AuditAction,
        subject: ArtifactRef,
        summary: str,
        details: Mapping[str, object] | None = None,
    ) -> AuditEvent:
        """Append a new immutable, chained audit event and return it."""
        prev = self.head_hash
        seq = len(self._entries)
        draft = AuditEvent(
            sequence=seq,
            action=action,
            subject=subject,
            summary=summary,
            details=dict(details or {}),
            prev_hash=prev,
        )
        # Freeze the chain hash onto a finalized copy.
        from dataclasses import replace

        entry = replace(draft, entry_hash=draft.computed_hash())
        self._entries.append(entry)
        return entry

    # -- read-only access -------------------------------------------------- #
    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterable[AuditEvent]:
        return iter(tuple(self._entries))

    @property
    def entries(self) -> tuple[AuditEvent, ...]:
        return tuple(self._entries)

    def for_subject(self, ref: ArtifactRef) -> tuple[AuditEvent, ...]:
        """All events whose subject shares the ``(kind, id)`` of ``ref``."""
        return tuple(e for e in self._entries if e.subject.key == ref.key)

    def verify(self) -> bool:
        """Verify the whole chain: each entry's hash and prev-link are intact."""
        prev = GENESIS_HASH
        for i, entry in enumerate(self._entries):
            if entry.sequence != i:
                return False
            if entry.prev_hash != prev:
                return False
            if not entry.is_valid():
                return False
            prev = entry.entry_hash
        return True
