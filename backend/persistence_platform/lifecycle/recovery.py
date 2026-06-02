"""Recovery engine (DRP4-I) — the persistence lifecycle's recover step.

Reconstructs platform state from durable storage on a **cold restart** (a fresh process /
service pointed at the same storage root reads a persisted manifest and rebuilds everything):

- registry snapshots (dicts),
- audit logs (replayed into the shared ``ImmutableAuditLog`` — reproduces the head),
- the shared lineage graph (rebuilt ``LineageTracker`` — ``verify_chain`` holds),
- execution-history streams (ordered lists).

Every component is checksum-verified on read (storage integrity); the rebuilt audit chains
and lineage chain are re-verified (recovery integrity).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ml.lineage import LineageTracker
from ml.provenance import hash_obj

from ..models.domain import RecoveryStatus, StorageRecord
from ..storage import StorageEngine
from ..registry_storage import RegistryStore
from ..audit_storage import AuditStore
from ..lineage_storage import LineageStore
from ..execution_storage import ExecutionStore


def storage_record_from_dict(d: dict) -> StorageRecord:
    return StorageRecord(
        storage_id=d["storage_id"], namespace=d["namespace"], key=d["key"], checksum=d["checksum"],
        fingerprint=d["fingerprint"], size_bytes=d["size_bytes"], uri=d["uri"],
        created_at=d.get("created_at", "1970-01-01T00:00:00Z"))


@dataclass
class RecoveryResult:
    recovery_id: str
    status: RecoveryStatus
    registries: dict = field(default_factory=dict)
    audit_logs: dict = field(default_factory=dict)
    lineage_tracker: Optional[LineageTracker] = None
    execution_histories: dict = field(default_factory=dict)
    anchor_lineage_id: Optional[str] = None
    anchor_verified: bool = False
    checks: tuple = ()
    lineage_id: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status == RecoveryStatus.RECOVERED

    def to_dict(self) -> dict:
        return {
            "recovery_id": self.recovery_id, "status": self.status.value,
            "registries": sorted(self.registries), "audit_logs": sorted(self.audit_logs),
            "n_lineage_nodes": len(self.lineage_tracker.all()) if self.lineage_tracker else 0,
            "execution_histories": {k: len(v) for k, v in sorted(self.execution_histories.items())},
            "anchor_lineage_id": self.anchor_lineage_id, "anchor_verified": self.anchor_verified,
            "checks": [{"name": n, "passed": bool(p), "detail": d} for n, p, d in self.checks],
            "lineage_id": self.lineage_id,
        }


class RecoveryEngine:
    """Reconstructs + verifies platform state from a persisted manifest."""

    def __init__(self, engine: StorageEngine):
        self.engine = engine
        self.registry_store = RegistryStore(engine)
        self.audit_store = AuditStore(engine)
        self.lineage_store = LineageStore(engine)
        self.execution_store = ExecutionStore(engine)

    def recover(self, manifest: dict) -> RecoveryResult:
        index = manifest["storage_index"]
        anchor = manifest.get("anchor_lineage_id")
        checks: list[tuple] = []
        status = RecoveryStatus.RECOVERED

        # --- storage integrity (checksum-verify every stored object on read) --
        registries, audit_logs, histories = {}, {}, {}
        lineage_tracker = None
        try:
            for d in index.get("registries", []):
                sr = storage_record_from_dict(d)
                registries[sr.key] = self.registry_store.recover(sr)
            checks.append(("registry_recovery", True, f"{len(registries)} registries"))
        except Exception as exc:
            status = RecoveryStatus.PARTIAL
            checks.append(("registry_recovery", False, f"error: {exc}"))

        try:
            for d in index.get("audit", []):
                sr = storage_record_from_dict(d)
                audit_logs[sr.key] = self.audit_store.recover(sr)
            checks.append(("audit_recovery", all(lg.verify() for lg in audit_logs.values()),
                           f"{len(audit_logs)} logs"))
        except Exception as exc:
            status = RecoveryStatus.PARTIAL
            checks.append(("audit_recovery", False, f"error: {exc}"))

        try:
            sr = storage_record_from_dict(index["lineage"])
            lineage_tracker = self.lineage_store.recover(sr)
            checks.append(("lineage_recovery", True, f"{len(lineage_tracker.all())} nodes"))
        except Exception as exc:
            status = RecoveryStatus.PARTIAL
            checks.append(("lineage_recovery", False, f"error: {exc}"))

        try:
            for d in index.get("execution", []):
                sr = storage_record_from_dict(d)
                histories[sr.key] = self.execution_store.recover(sr)
            checks.append(("execution_recovery", True, f"{len(histories)} streams"))
        except Exception as exc:
            status = RecoveryStatus.PARTIAL
            checks.append(("execution_recovery", False, f"error: {exc}"))

        # --- recovery integrity (the anchor chain verifies after rebuild) -----
        anchor_verified = bool(lineage_tracker and anchor and lineage_tracker.verify_chain(anchor))
        checks.append(("anchor_chain_verified", anchor_verified or anchor is None,
                       f"anchor={anchor}"))

        if not all(p for _, p, _ in checks):
            status = RecoveryStatus.PARTIAL if registries or lineage_tracker else RecoveryStatus.FAILED

        recovery_id = "recovery+" + hash_obj({
            "anchor": anchor, "registries": sorted(registries), "logs": sorted(audit_logs),
            "n_nodes": len(lineage_tracker.all()) if lineage_tracker else 0,
            "histories": {k: len(v) for k, v in histories.items()}, "status": status.value})

        return RecoveryResult(
            recovery_id=recovery_id, status=status, registries=registries, audit_logs=audit_logs,
            lineage_tracker=lineage_tracker, execution_histories=histories, anchor_lineage_id=anchor,
            anchor_verified=anchor_verified, checks=tuple(checks))


__all__ = ["RecoveryEngine", "RecoveryResult", "storage_record_from_dict"]
