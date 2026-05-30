"""UserService — governed user management (P6-D).

Owns the user store, per-user immutable audit logs, and the user lineage nodes (on the
shared tracker), and keeps the application registry in sync. Every mutation is:
validated -> audited (immutable) -> lineage-tracked -> version-bumped -> registry-synced.

A user is the root of the user/upload lineage branch. User records carry **no secret
material** (credentials live in the auth credential store), so user records, versions,
and reports are deterministic and free of secrets.
"""

from __future__ import annotations

from typing import Optional

from ml.lineage import LineageTracker

from ..version import DETERMINISTIC_EPOCH
from ..identity import mint_identity
from ..models.domain import (
    BackendRegistryRecord, BackendVersion, EntityKind, UserIdentity, UserRecord, UserRole, UserStatus,
)
from ..audit import make_backend_audit_log, ImmutableAuditLog
from ..lineage import make_user_lineage
from ..registry import BackendRegistry


class UserManagementError(RuntimeError):
    """Raised on user-management misuse (duplicate username, unknown user, bad role)."""


_DEFAULT_ROLE = UserRole.VIEWER


class UserService:
    """Stateful service: the user store, per-user audit logs, shared lineage + registry."""

    def __init__(self, *, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[BackendRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or BackendRegistry()
        self._users_by_id: dict[str, UserRecord] = {}
        self._id_by_username: dict[str, str] = {}
        self._audit_logs: dict[str, ImmutableAuditLog] = {}

    # --- accessors ------------------------------------------------------------
    def audit_log_for(self, user_id: str) -> ImmutableAuditLog:
        return self._audit_logs[user_id]

    def exists(self, user_id: str) -> bool:
        return user_id in self._users_by_id

    def exists_username(self, username: str) -> bool:
        return username in self._id_by_username

    def get_user(self, user_id: str) -> UserRecord:
        if user_id not in self._users_by_id:
            raise UserManagementError(f"unknown user {user_id!r}")
        return self._users_by_id[user_id]

    def get_by_username(self, username: str) -> Optional[UserRecord]:
        uid = self._id_by_username.get(username)
        return self._users_by_id.get(uid) if uid else None

    def list_users(self) -> list[UserRecord]:
        return [self._users_by_id[uid] for uid in sorted(self._users_by_id)]

    # --- create ---------------------------------------------------------------
    def create_user(self, *, username: str, roles=(_DEFAULT_ROLE,),
                    metadata: Optional[dict] = None, owner: str = "application-ops",
                    created_at: str = DETERMINISTIC_EPOCH) -> UserRecord:
        if not isinstance(username, str) or username.strip() == "":
            raise UserManagementError("username must be a non-empty string")
        if self.exists_username(username):
            raise UserManagementError(f"username {username!r} already exists")
        role_tuple = self._coerce_roles(roles)

        identity_obj = mint_identity("user", {"username": username})
        user_id = identity_obj.id
        identity = UserIdentity(user_id=user_id, username=username,
                                identity_version=identity_obj.identity_version)

        node = self.lineage.record(make_user_lineage(user_id, username=username, created_at=created_at))
        log = make_backend_audit_log()
        self._audit_logs[user_id] = log
        log.append("user_created", {"user_id": user_id, "username": username,
                                    "roles": sorted(r.value for r in role_tuple),
                                    "lineage_id": node.lineage_id}, created_at=created_at)

        record = self._assemble(
            identity=identity, roles=role_tuple, status=UserStatus.ACTIVE,
            metadata=dict(metadata or {}), previous=None, reason="created", owner=owner,
            created_at=created_at, lineage_id=node.lineage_id, log=log)
        self._store(record)
        return record

    # --- update ---------------------------------------------------------------
    def update_user(self, user_id: str, *, roles=None, metadata: Optional[dict] = None,
                    owner: Optional[str] = None, created_at: str = DETERMINISTIC_EPOCH) -> UserRecord:
        current = self.get_user(user_id)
        if current.status == UserStatus.DEACTIVATED:
            raise UserManagementError(f"user {user_id!r} is deactivated and cannot be updated")
        new_roles = current.roles if roles is None else self._coerce_roles(roles)
        new_meta = current.metadata if metadata is None else dict(metadata)
        log = self._audit_logs[user_id]
        log.append("user_updated", {"user_id": user_id,
                                    "roles": sorted(r.value for r in new_roles),
                                    "metadata_keys": sorted(new_meta)}, created_at=created_at)
        record = self._assemble(
            identity=current.identity, roles=new_roles, status=current.status, metadata=new_meta,
            previous=current.version.version, reason="updated", owner=owner or current.owner,
            created_at=created_at, lineage_id=current.lineage_id, log=log)
        self._store(record, allow_update=True)
        return record

    def set_status(self, user_id: str, status: UserStatus, *,
                   created_at: str = DETERMINISTIC_EPOCH) -> UserRecord:
        current = self.get_user(user_id)
        log = self._audit_logs[user_id]
        log.append("user_status_changed", {"user_id": user_id, "from": current.status.value,
                                           "to": status.value}, created_at=created_at)
        record = self._assemble(
            identity=current.identity, roles=current.roles, status=status, metadata=current.metadata,
            previous=current.version.version, reason=f"status:{status.value}", owner=current.owner,
            created_at=created_at, lineage_id=current.lineage_id, log=log)
        self._store(record, allow_update=True)
        return record

    def deactivate_user(self, user_id: str, *, created_at: str = DETERMINISTIC_EPOCH) -> UserRecord:
        return self.set_status(user_id, UserStatus.DEACTIVATED, created_at=created_at)

    # --- internals ------------------------------------------------------------
    def _coerce_roles(self, roles) -> tuple[UserRole, ...]:
        out = []
        for r in roles:
            if isinstance(r, UserRole):
                out.append(r)
            else:
                try:
                    out.append(UserRole(r))
                except ValueError as exc:
                    raise UserManagementError(f"unknown role {r!r}") from exc
        if not out:
            raise UserManagementError("a user must have at least one role")
        # de-duplicate, stable order by role value
        return tuple(sorted(set(out), key=lambda x: x.value))

    def _assemble(self, *, identity, roles, status, metadata, previous, reason, owner,
                  created_at, lineage_id, log: ImmutableAuditLog) -> UserRecord:
        state_sig = UserRecord.state_signature_of(identity=identity, roles=roles, status=status,
                                                   metadata=metadata)
        version = BackendVersion(version=BackendVersion.compute(state_sig, previous),
                                 previous=previous, reason=reason, created_at=created_at)
        log.append("user_version_changed", {"version": version.version, "reason": reason},
                   created_at=created_at)
        return UserRecord(
            identity=identity, roles=roles, status=status, metadata=dict(metadata),
            version=version, owner=owner, created_at=created_at, lineage_id=lineage_id,
            audit_head=log.head)

    def _store(self, record: UserRecord, *, allow_update: bool = False) -> None:
        self._users_by_id[record.user_id] = record
        self._id_by_username[record.username] = record.user_id
        self.registry.register(BackendRegistryRecord(
            entity_kind=EntityKind.USER, entity_id=record.user_id, status=record.status.value,
            version=record.version.version, owner=record.owner, creation_date=record.created_at,
            audit_state=record.audit_head or "", lineage_id=record.lineage_id or "",
            user_id=record.user_id, dependencies=()))


__all__ = ["UserService", "UserManagementError"]
