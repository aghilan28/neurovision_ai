"""PersistencePlatformService — the governed orchestration hub for DRP-4.

Turns the in-memory platform into a **persistent platform**: it durably persists registries,
audit history, lineage history, and execution history; recovers them on a cold restart;
validates the recovery; and scores persistence readiness — without modifying any business
logic.

    persist registries + audit + lineage + execution -> write a recovery manifest ->
    recover (cold restart, checksum-verified) -> validate -> score readiness -> version ->
    record lineage (Serving -> Persistence Record -> Recovery Event) -> append audit events

Reuses the shared ``ml.lineage`` tracker + the shared ``ImmutableAuditLog`` (no parallel
systems): it serializes and faithfully reconstructs them. It performs **no** model / training
/ inference / serving / frontend / deployment / monitoring / security changes (forbidden in
this phase) — it only persists and recovers state.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from typing import Optional

from ml.lineage import LineageTracker
from ml.provenance import content_id, hash_obj

from .version import PERSISTENCE_PLATFORM_VERSION, DETERMINISTIC_EPOCH
from .identity import mint_identity
from .models.domain import (
    PersistenceIdentity, PersistenceRecord, PersistenceStatus, PersistenceValidationRecord,
    RepositoryKind, StorageVersion,
)
from .storage import StorageEngine
from .storage.engine import StorageError
from .repositories import Repository
from .registry_storage import RegistryStore
from .audit_storage import AuditStore
from .lineage_storage import LineageStore
from .execution_storage import ExecutionStore
from .lifecycle import RecoveryEngine, RecoveryResult
from .validation import PersistenceContentValidator, PersistenceIntegrityValidator
from .readiness import PersistenceReadinessEngine
from .audit import make_persistence_audit_log, ImmutableAuditLog
from .lineage import make_persistence_lineage, make_recovery_lineage
from . import reports as _reports


class PersistencePlatformError(RuntimeError):
    """Raised on programmer misuse of the service (not for unusable state)."""


@dataclass
class PlatformState:
    """The platform state to persist: registries + audit logs + the shared lineage tracker +
    execution-history streams + an anchor (a representative served-execution lineage node)."""

    lineage: LineageTracker
    registries: dict = field(default_factory=dict)        # name -> obj with .to_dict()
    audit_logs: dict = field(default_factory=dict)        # name -> ImmutableAuditLog
    execution_history: dict = field(default_factory=dict)  # kind -> list[dict]
    repositories: dict = field(default_factory=dict)      # RepositoryKind -> {id: dict}
    anchor_lineage_id: Optional[str] = None


@dataclass(frozen=True)
class PersistenceOutcome:
    accepted: bool
    reason: str
    record: Optional[PersistenceRecord] = None
    recovery: Optional[RecoveryResult] = None
    readiness: object = None
    manifest_storage_id: Optional[str] = None

    @property
    def persistence_id(self) -> Optional[str]:
        return self.record.persistence_id if self.record else None

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted, "reason": self.reason,
            "persistence_id": self.persistence_id,
            "record": self.record.to_dict() if self.record else None,
            "recovery": self.recovery.to_dict() if self.recovery else None,
            "readiness": self.readiness.to_dict() if self.readiness else None,
        }


class PersistencePlatformService:
    """Stateful service: a durable storage engine + the persistence stores + per-snapshot
    audit logs + recovery/validation/readiness engines."""

    def __init__(self, *, storage_root: Optional[str] = None,
                 lineage_tracker: Optional[LineageTracker] = None):
        self.storage_root = storage_root or tempfile.mkdtemp(prefix="nv_persistence_")
        os.makedirs(self.storage_root, exist_ok=True)
        self.engine = StorageEngine(self.storage_root)
        self.lineage = lineage_tracker or LineageTracker()
        self.registry_store = RegistryStore(self.engine)
        self.audit_store = AuditStore(self.engine)
        self.lineage_store = LineageStore(self.engine)
        self.execution_store = ExecutionStore(self.engine)
        self.content_validator = PersistenceContentValidator(self.engine)
        self.integrity_validator = PersistenceIntegrityValidator()
        self.readiness_engine = PersistenceReadinessEngine()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}
        self._context: dict[str, dict] = {}

    def audit_log_for(self, persistence_id: str) -> ImmutableAuditLog:
        return self._audit_logs[persistence_id]

    # --- persist --------------------------------------------------------------
    def persist(self, state: PlatformState, *, owner: str = "persistence-ops",
                created_at: str = DETERMINISTIC_EPOCH) -> PersistenceOutcome:
        if state.lineage is not self.lineage:
            raise PersistencePlatformError(
                "persist with the service's shared LineageTracker so the persistence node joins "
                "the one graph (no parallel lineage)")
        log = make_persistence_audit_log()
        storage_records = []

        # --- snapshot fingerprint over the SOURCE state (breaks id<->lineage cycle) ---
        source = {
            "registries": {n: r.to_dict() for n, r in sorted(state.registries.items())},
            "audit": {n: {"head": lg.head, "n": len(lg)} for n, lg in sorted(state.audit_logs.items())},
            "lineage_nodes": sorted(state.lineage.all()),
            "execution": {k: len(v) for k, v in sorted(state.execution_history.items())},
            "anchor": state.anchor_lineage_id,
        }
        snapshot_fingerprint = hash_obj(source)
        persistence_id = mint_identity("persistence_record",
                                       {"snapshot_fingerprint": snapshot_fingerprint}).id
        log.append("persist_started", {"persistence_id": persistence_id,
                                       "snapshot_fingerprint": snapshot_fingerprint},
                   created_at=created_at)

        # --- record the persistence lineage node in the shared tracker (parents anchor) ---
        p_node = self.lineage.record(make_persistence_lineage(
            persistence_id, state.anchor_lineage_id, snapshot_fingerprint=snapshot_fingerprint,
            created_at=created_at))

        # --- persist registries (DRP4-E) --------------------------------------
        registry_storage = []
        for name, reg in sorted(state.registries.items()):
            sr, rsr = self.registry_store.persist(name, reg.to_dict())
            storage_records.append(sr)
            registry_storage.append(rsr)
        log.append("registries_persisted", {"n": len(registry_storage)}, created_at=created_at)

        # --- persist audit logs (DRP4-F) --------------------------------------
        audit_storage = []
        for name, alog in sorted(state.audit_logs.items()):
            sr, asr = self.audit_store.persist(name, alog)
            storage_records.append(sr)
            audit_storage.append(asr)
        log.append("audit_persisted", {"n": len(audit_storage)}, created_at=created_at)

        # --- persist the shared lineage graph incl. the persistence node (DRP4-G) ---
        sr, lineage_storage = self.lineage_store.persist(self.lineage)
        storage_records.append(sr)
        log.append("lineage_persisted", {"n_nodes": lineage_storage.n_nodes,
                                         "n_edges": lineage_storage.n_edges}, created_at=created_at)

        # --- persist execution history (DRP4-H) -------------------------------
        execution_storage = []
        for kind, entries in sorted(state.execution_history.items()):
            sr, esr = self.execution_store.persist(kind, entries)
            storage_records.append(sr)
            execution_storage.append(esr)
        log.append("execution_persisted", {"n": len(execution_storage)}, created_at=created_at)

        # --- repositories (DRP4-D): artifact repos (caller) + auto lineage/audit repos ---
        repositories = self._persist_repositories(state)
        log.append("repositories_persisted", {"n": len(repositories)}, created_at=created_at)

        # --- write the cold-restart recovery manifest -------------------------
        manifest = {
            "persistence_id": persistence_id, "snapshot_fingerprint": snapshot_fingerprint,
            "persistence_lineage_id": p_node.lineage_id,
            "anchor_lineage_id": state.anchor_lineage_id,
            "storage_index": {
                "registries": [s.to_dict() for s in storage_records
                               if s.namespace == "registry"],
                "audit": [s.to_dict() for s in storage_records if s.namespace == "audit"],
                "lineage": next(s.to_dict() for s in storage_records if s.namespace == "lineage"),
                "execution": [s.to_dict() for s in storage_records if s.namespace == "execution"],
            },
        }
        manifest_sr = self.engine.put("snapshot", persistence_id, manifest, created_at=created_at)
        storage_records.append(manifest_sr)
        log.append("manifest_written", {"manifest_storage_id": manifest_sr.storage_id},
                   created_at=created_at)

        # --- content validation (DRP4-J) --------------------------------------
        checks = tuple(self.content_validator.content_checks(
            storage_records=storage_records, registry_storage=registry_storage,
            audit_storage=audit_storage, lineage_storage=lineage_storage,
            execution_storage=execution_storage))
        content_ok = all(p for _, p, _ in checks)
        validation = PersistenceValidationRecord(
            validation_id=content_id("persval", {
                "persistence_id": persistence_id, "checks": [[n, bool(p)] for n, p, _ in checks]}),
            ok=content_ok, checks=checks)

        # --- cold-restart recovery (prove durability from disk) (DRP4-I) ------
        recovery = self._recover_from_manifest(manifest, register_event=False)
        log.append("recovery_verified", {"recovery_id": recovery.recovery_id,
                                         "status": recovery.status.value}, created_at=created_at)

        # --- readiness (DRP4-K) -----------------------------------------------
        readiness = self.readiness_engine.assess(
            target_id=persistence_id, storage_ok=content_ok, registry_ok=len(registry_storage) > 0,
            recovery_ok=recovery.ok and recovery.anchor_verified, audit_ok=len(audit_storage) > 0,
            lineage_ok=lineage_storage.n_nodes > 0, validation_ok=content_ok, created_at=created_at)
        log.append("readiness_scored", {"readiness_id": readiness.readiness_id,
                                        "classification": readiness.classification.value},
                   created_at=created_at)

        # --- status + version --------------------------------------------------
        status = PersistenceStatus.PERSISTED if (content_ok and recovery.ok) else PersistenceStatus.FAILED
        identity = PersistenceIdentity(
            persistence_id=persistence_id, snapshot_fingerprint=snapshot_fingerprint,
            anchor_lineage_id=state.anchor_lineage_id, identity_version=mint_identity(
                "persistence_record", {"snapshot_fingerprint": snapshot_fingerprint}).identity_version)
        dependencies = (state.anchor_lineage_id,) if state.anchor_lineage_id else ()
        state_sig = PersistenceRecord.state_signature_of(
            identity=identity, registry_storage=tuple(registry_storage),
            audit_storage=tuple(audit_storage), lineage_storage=lineage_storage,
            execution_storage=tuple(execution_storage), repositories=tuple(repositories),
            validation=validation, readiness_id=readiness.readiness_id,
            readiness_class=readiness.classification, status=status, dependencies=dependencies)
        version = StorageVersion(version=StorageVersion.compute(state_sig, None), previous=None,
                                 reason="persisted", created_at=created_at)
        log.append("persistence_version_changed", {"version": version.version}, created_at=created_at)
        log.append("persist_completed", {"persistence_id": persistence_id, "status": status.value},
                   created_at=created_at)

        record = PersistenceRecord(
            identity=identity, registry_storage=tuple(registry_storage),
            audit_storage=tuple(audit_storage), lineage_storage=lineage_storage,
            execution_storage=tuple(execution_storage), repositories=tuple(repositories),
            storage_root=self.storage_root, validation=validation, readiness_id=readiness.readiness_id,
            readiness_class=readiness.classification, status=status, version=version, owner=owner,
            created_at=created_at, lineage_id=p_node.lineage_id, audit_head=log.head,
            dependencies=dependencies)

        self._audit_logs[persistence_id] = log
        self._context[persistence_id] = {"record": record, "recovery": recovery,
                                          "readiness": readiness, "storage_records": storage_records,
                                          "manifest": manifest}
        return PersistenceOutcome(
            accepted=(status == PersistenceStatus.PERSISTED), reason=status.value, record=record,
            recovery=recovery, readiness=readiness, manifest_storage_id=manifest_sr.storage_id)

    # --- explicit cold-restart recovery --------------------------------------
    def recover(self, persistence_id: str, *, storage_root: Optional[str] = None,
                created_at: str = DETERMINISTIC_EPOCH) -> RecoveryResult:
        """Recover platform state from durable storage on a cold restart (fresh engine)."""
        engine = StorageEngine(storage_root or self.storage_root)
        if not engine.exists("snapshot", persistence_id):
            raise StorageError(f"no persisted snapshot {persistence_id!r}")
        manifest = engine.get("snapshot", persistence_id)
        return self._recover_from_manifest(manifest, engine=engine, register_event=True,
                                           created_at=created_at)

    def _recover_from_manifest(self, manifest: dict, *, engine: Optional[StorageEngine] = None,
                               register_event: bool = True,
                               created_at: str = DETERMINISTIC_EPOCH) -> RecoveryResult:
        engine = engine or StorageEngine(self.storage_root)
        result = RecoveryEngine(engine).recover(manifest)
        if register_event and result.lineage_tracker is not None:
            parent_lineage_id = manifest.get("persistence_lineage_id")
            if parent_lineage_id and result.lineage_tracker.exists(parent_lineage_id):
                r_node = make_recovery_lineage(
                    result.recovery_id, parent_lineage_id, status=result.status.value,
                    created_at=created_at)
                result.lineage_tracker.record(r_node)
                result.lineage_id = r_node.lineage_id
        return result

    # --- validation + reports -------------------------------------------------
    def integrity(self, record: PersistenceRecord):
        ctx = self._context[record.persistence_id]
        return self.integrity_validator.validate(
            record=record, recovery=ctx["recovery"], engine=self.engine, lineage_tracker=self.lineage,
            audit_log=self._audit_logs[record.persistence_id],
            storage_records=ctx["storage_records"])

    def reports(self, record: PersistenceRecord) -> dict:
        ctx = self._context[record.persistence_id]
        integrity = self.integrity(record)
        return {
            "storage_report": _reports.build_storage_report(record),
            "registry_report": _reports.build_registry_report(record),
            "audit_persistence_report": _reports.build_audit_persistence_report(record),
            "lineage_persistence_report": _reports.build_lineage_persistence_report(record),
            "recovery_report": _reports.build_recovery_report(record, ctx["recovery"]),
            "validation_report": _reports.build_validation_report(record, integrity),
            "readiness_report": _reports.build_readiness_report(record, ctx["readiness"]),
            "persistence_summary_report": _reports.build_persistence_summary_report(
                record, ctx["recovery"], ctx["readiness"], integrity),
        }

    # --- internals ------------------------------------------------------------
    def _persist_repositories(self, state: PlatformState) -> list:
        repositories = []
        # artifact repositories from caller-supplied data
        for kind in RepositoryKind:
            data = None
            if kind in (RepositoryKind.AUDIT, RepositoryKind.LINEAGE):
                continue
            data = state.repositories.get(kind) or state.repositories.get(kind.value)
            repo = Repository(self.engine, kind)
            if data:
                repositories.append(repo.save_all(data))
            else:
                repositories.append(repo.manifest())
        # auto-derived lineage repository (every node by id)
        lineage_repo = Repository(self.engine, RepositoryKind.LINEAGE)
        repositories.append(lineage_repo.save_all(
            {lid: node.to_dict() for lid, node in self.lineage.all().items()}))
        # auto-derived audit repository (every event by hash, across the input logs)
        audit_repo = Repository(self.engine, RepositoryKind.AUDIT)
        events = {}
        for _name, alog in sorted(state.audit_logs.items()):
            for e in alog.events():
                events[e.event_hash] = {"seq": e.seq, "kind": e.kind, "payload": e.payload,
                                        "prev_hash": e.prev_hash, "event_hash": e.event_hash,
                                        "created_at": e.created_at}
        repositories.append(audit_repo.save_all(events) if events else audit_repo.manifest())
        return repositories

    @property
    def version(self) -> str:
        return PERSISTENCE_PLATFORM_VERSION


__all__ = ["PersistencePlatformService", "PlatformState", "PersistenceOutcome",
           "PersistencePlatformError"]
