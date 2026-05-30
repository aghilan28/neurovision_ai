"""The intelligence registry.

Coordinates three guarantees on every admitted artifact:

1. **Versioning.** A new logical id starts at version 1. Re-registering the same
   id with *different* content produces the next version; re-registering with
   *identical* content is idempotent (no new version).
2. **Auditability.** Every admission writes an immutable audit event
   (``CREATE``/``REGISTER`` for v1, ``VERSION`` for later revisions).
3. **Traceability.** Every admission records a lineage entry linking the artifact
   to its parents (and, transitively, its source roots).

Because version assignment depends only on prior registry state and artifact
content (never the clock), replaying the same admissions reproduces identical
versions and audit/lineage references.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from backend.multi_case_intelligence.audit.log import IntelligenceAuditLog
from backend.multi_case_intelligence.lineage.tracker import IntelligenceLineageTracker
from backend.multi_case_intelligence.schemas.base import (
    ArtifactKind,
    ArtifactRef,
    VersionedArtifact,
)
from backend.multi_case_intelligence.schemas.events import AuditAction


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    """An immutable registry record pinning one revision of an artifact."""

    ref: ArtifactRef
    artifact: VersionedArtifact
    version: int
    content_hash: str
    audit_sequence: int
    lineage_hash: str


class IntelligenceRegistry:
    """In-memory, version-aware registry for intelligence artifacts."""

    def __init__(
        self,
        audit_log: IntelligenceAuditLog | None = None,
        lineage: IntelligenceLineageTracker | None = None,
    ) -> None:
        self.audit = audit_log or IntelligenceAuditLog()
        self.lineage = lineage or IntelligenceLineageTracker()
        # (kind, id) -> ordered version history of entries.
        self._history: dict[tuple[str, str], list[RegistryEntry]] = {}

    def register(
        self,
        artifact: VersionedArtifact,
        *,
        parents: tuple[ArtifactRef, ...] = (),
        summary: str | None = None,
    ) -> RegistryEntry:
        """Admit (or re-admit) an artifact, returning its registry entry."""
        key = (artifact.KIND.value, artifact.id)
        content = artifact.compute_hash()
        history = self._history.get(key, [])

        if history and history[-1].content_hash == content:
            # Idempotent: identical content already registered at this id.
            return history[-1]

        version = len(history) + 1
        # Stamp the assigned version onto the stored artifact for honesty.
        versioned_artifact = replace(artifact, version=version)
        pinned_ref = ArtifactRef(
            kind=artifact.KIND, id=artifact.id, content_hash=content, version=version
        )

        lineage_record = self.lineage.register(pinned_ref, parents)
        action = AuditAction.CREATE if version == 1 else AuditAction.VERSION
        event = self.audit.record(
            action,
            pinned_ref,
            summary or f"register {artifact.KIND.value} v{version}",
            details={
                "version": version,
                "content_hash": content,
                "parents": [p.key for p in parents],
                "roots": [r.key for r in lineage_record.roots],
            },
        )
        # A second REGISTER event documents the registry admission explicitly.
        self.audit.record(
            AuditAction.REGISTER,
            pinned_ref,
            f"registered {artifact.KIND.value} {artifact.id} v{version}",
            details={"audit_link": event.sequence},
        )

        entry = RegistryEntry(
            ref=pinned_ref,
            artifact=versioned_artifact,
            version=version,
            content_hash=content,
            audit_sequence=event.sequence,
            lineage_hash=lineage_record.record_hash(),
        )
        self._history.setdefault(key, []).append(entry)
        return entry

    # -- read-only access -------------------------------------------------- #
    def latest(self, kind: ArtifactKind, artifact_id: str) -> RegistryEntry | None:
        history = self._history.get((kind.value, artifact_id))
        return history[-1] if history else None

    def get(self, ref: ArtifactRef) -> RegistryEntry | None:
        history = self._history.get(ref.key)
        if not history:
            return None
        if ref.version is not None:
            for entry in history:
                if entry.version == ref.version:
                    return entry
            return None
        return history[-1]

    def contains(self, ref: ArtifactRef) -> bool:
        return self.get(ref) is not None

    def history(self, kind: ArtifactKind, artifact_id: str) -> tuple[RegistryEntry, ...]:
        return tuple(self._history.get((kind.value, artifact_id), ()))

    def all_entries(self) -> tuple[RegistryEntry, ...]:
        """Every latest-version entry, in deterministic order."""
        latest = [h[-1] for h in self._history.values()]
        latest.sort(key=lambda e: (e.ref.kind.value, e.ref.id))
        return tuple(latest)

    def all_versions(self) -> tuple[RegistryEntry, ...]:
        out = [e for h in self._history.values() for e in h]
        out.sort(key=lambda e: (e.ref.kind.value, e.ref.id, e.version))
        return tuple(out)

    def __len__(self) -> int:
        return len(self._history)
