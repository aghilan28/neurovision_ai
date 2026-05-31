"""SecurityPlatformService — the governed orchestration hub for DRP-5.

Turns the persistent platform into a **secure platform**: it authenticates users, authorizes
requests against versioned policies, controls access to protected resources under least
privilege, audits every security event, traces the security lineage, and scores security
readiness — without changing any business logic.

    register user + credential + policies ->
    authenticate (verify credential, issue session) -> authorize (RBAC, default-deny) ->
    control access (least privilege) -> validate -> score readiness -> version ->
    record lineage (User -> Credential -> Authentication -> Authorization -> Access Decision ->
    Resource Access) -> append immutable audit events

Reuses the platform's PBKDF2 + entropy primitives, the shared ``ml.lineage`` tracker, and the
shared ``ImmutableAuditLog`` (no parallel systems). It performs **no** model / training /
inference / serving / persistence / deployment / monitoring changes (forbidden in this phase).
No plaintext credential storage; secrets never enter a content hash, report, or the audit/
lineage trail.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from ml.lineage import LineageTracker
from ml.provenance import content_id

from .version import SECURITY_PLATFORM_VERSION, DEFAULT_SESSION_TTL_STEPS, DETERMINISTIC_EPOCH
from .identity import mint_identity
from .models.domain import (
    AccessControlRecord, Action, AuthOutcome, ResourceType, Role,
    SecurityIdentity, SecurityUserRecord, SecurityValidationRecord, SecurityVersion, UserStatus,
)
from .credentials import CredentialManager
from .authentication import AuthenticationEngine
from .authorization import AuthorizationEngine
from .access_control import AccessControlEngine
from .policies import PolicyEngine
from .registry import SecurityRegistry
from .readiness import SecurityReadinessEngine
from .validation import SecurityContentValidator, SecurityIntegrityValidator
from .audit import make_security_audit_log, ImmutableAuditLog
from .lineage import (
    make_user_lineage, make_credential_lineage, make_authentication_lineage,
    make_authorization_lineage, make_access_decision_lineage, make_resource_access_lineage,
)
from . import reports as _reports


class SecurityPlatformError(RuntimeError):
    """Raised on programmer misuse of the service (not for denied/invalid access)."""


@dataclass(frozen=True)
class SecurityOutcome:
    """The result of an end-to-end secured access attempt."""

    accepted: bool                      # the access flow completed and produced a decision
    reason: str
    record: Optional[AccessControlRecord] = None
    readiness: object = None
    authentication: object = None

    @property
    def permitted(self) -> bool:
        return bool(self.record and self.record.permitted)

    @property
    def access_id(self) -> Optional[str]:
        return self.record.access_id if self.record else None

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted, "reason": self.reason, "permitted": self.permitted,
            "access_id": self.access_id,
            "record": self.record.to_dict() if self.record else None,
            "readiness": self.readiness.to_dict() if self.readiness else None,
            "authentication": self.authentication.to_dict() if self.authentication else None,
        }


class SecurityPlatformService:
    """Stateful service: users + credentials + policies + a shared lineage tracker, the
    security engines, the registry, and per-access immutable audit logs + context."""

    def __init__(self, *, lineage_tracker: Optional[LineageTracker] = None,
                 credential_manager: Optional[CredentialManager] = None,
                 install_default_policies: bool = True):
        self.lineage = lineage_tracker or LineageTracker()
        self.credentials = credential_manager or CredentialManager()
        self.authn = AuthenticationEngine(credential_manager=self.credentials)
        self.authz = AuthorizationEngine()
        self.access_control = AccessControlEngine()
        self.policies = PolicyEngine()
        self.registry = SecurityRegistry()
        self.registry.attach_policy_engine(self.policies)
        self.readiness_engine = SecurityReadinessEngine()
        self.content_validator = SecurityContentValidator()
        self.integrity_validator = SecurityIntegrityValidator()
        self.setup_log = make_security_audit_log()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}
        self._context: dict[str, dict] = {}
        self._users_by_name: dict[str, SecurityUserRecord] = {}
        self._active_credential: dict[str, object] = {}
        if install_default_policies:
            for p in self.policies.install_default_policies():
                self.setup_log.append("policy_registered", {"policy_id": p.policy_id, "name": p.name})

    def audit_log_for(self, access_id: str) -> ImmutableAuditLog:
        return self._audit_logs[access_id]

    # --- setup ----------------------------------------------------------------
    def register_user(self, username: str, role: Role, *,
                      created_at: str = DETERMINISTIC_EPOCH) -> SecurityUserRecord:
        if username in self._users_by_name:
            raise SecurityPlatformError(f"user {username!r} already registered")
        user_id = mint_identity("security_user", {"username": username}).id
        node = self.lineage.record(make_user_lineage(user_id, username=username, created_at=created_at))
        self.setup_log.append("user_registered", {"user_id": user_id, "role": role.value},
                              created_at=created_at)
        user = SecurityUserRecord(user_id=user_id, username=username, role=role,
                                  status=UserStatus.ACTIVE, created_at=created_at,
                                  lineage_id=node.lineage_id, audit_state=self.setup_log.head)
        self._users_by_name[username] = user
        self.registry.register_user(user)
        return user

    def set_credential(self, username: str, password: str, *,
                       created_at: str = DETERMINISTIC_EPOCH):
        user = self._require_user(username)
        credential = self.credentials.register(user.user_id, password, created_at=created_at)
        node = self.lineage.record(make_credential_lineage(
            credential.credential_id, user.lineage_id, created_at=created_at))
        credential = replace(credential, lineage_id=node.lineage_id)
        self.setup_log.append("credential_registered",
                              {"credential_id": credential.credential_id, "user_id": user.user_id},
                              created_at=created_at)
        self._active_credential[user.user_id] = credential
        self.registry.register_credential(credential)
        return credential

    def rotate_credential(self, username: str, new_password: str, *,
                          created_at: str = DETERMINISTIC_EPOCH):
        user = self._require_user(username)
        old = self._active_credential[user.user_id]
        rotated_old, new_active = self.credentials.rotate(old, new_password, created_at=created_at)
        node = self.lineage.record(make_credential_lineage(
            new_active.credential_id, user.lineage_id, created_at=created_at))
        new_active = replace(new_active, lineage_id=node.lineage_id)
        self.registry.register_credential(rotated_old)
        self.registry.register_credential(new_active)
        self._active_credential[user.user_id] = new_active
        self.setup_log.append("credential_rotated",
                              {"old": rotated_old.credential_id, "new": new_active.credential_id},
                              created_at=created_at)
        return new_active

    # --- the single use case: end-to-end secured access ----------------------
    def secure_access(self, username: str, password: str, *, resource_type: ResourceType,
                      resource_id: str, action: Action, resource_lineage_id: Optional[str] = None,
                      issued_step: int = 0, at_step: int = 0,
                      ttl_steps: int = DEFAULT_SESSION_TTL_STEPS, owner: str = "security-ops",
                      created_at: str = DETERMINISTIC_EPOCH) -> SecurityOutcome:
        """Authenticate -> authorize -> control access, end to end."""
        user = self._require_user(username)
        credential = self._active_credential.get(user.user_id)
        if credential is None:
            raise SecurityPlatformError(f"user {username!r} has no credential set")

        log = make_security_audit_log()

        # --- authentication ---------------------------------------------------
        auth, session = self.authn.authenticate(
            user.user_id, credential, password, issued_step=issued_step, ttl_steps=ttl_steps,
            created_at=created_at)
        auth_node = self.lineage.record(make_authentication_lineage(
            auth.authentication_id, credential.lineage_id, outcome=auth.outcome.value,
            created_at=created_at))
        auth = replace(auth, lineage_id=auth_node.lineage_id)
        log.append("authentication", {"authentication_id": auth.authentication_id,
                                      "outcome": auth.outcome.value}, created_at=created_at)
        self.registry.register_authentication(auth)
        if auth.outcome == AuthOutcome.FAILURE or session is None:
            # graceful: invalid credentials -> the access never proceeds (no access record)
            self._audit_logs.setdefault("_failed", log)
            return SecurityOutcome(accepted=False, reason="authentication_failed", authentication=auth)
        session = replace(session, lineage_id=auth_node.lineage_id)
        self.registry.register_session(session)

        # --- session validity (deterministic logical window) ------------------
        session_valid, session_reason = self.authn.validate_session(session, at_step=at_step)
        effective = self.authn.effective_status(session, at_step=at_step)
        if effective != session.status:
            session = replace(session, status=effective)
            self.registry.register_session(session)

        # --- authorization (RBAC, default-deny) -------------------------------
        authorization = self.authz.authorize(
            authentication_id=auth.authentication_id, user_id=user.user_id, role=user.role,
            resource_type=resource_type, resource_id=resource_id, action=action,
            policy_engine=self.policies, created_at=created_at)
        authz_node = self.lineage.record(make_authorization_lineage(
            authorization.authorization_id, auth_node.lineage_id,
            decision=authorization.decision.value, created_at=created_at))
        authorization = replace(authorization, lineage_id=authz_node.lineage_id)
        log.append("authorization", {"authorization_id": authorization.authorization_id,
                                     "decision": authorization.decision.value}, created_at=created_at)
        self.registry.register_authorization(authorization)

        # --- access control (least privilege) ---------------------------------
        outcome = self.access_control.control(
            session_valid=session_valid, session_reason=session_reason, authorization=authorization)
        decision = outcome.decision
        decision_node = self.lineage.record(make_access_decision_lineage(
            authz_node.lineage_id, decision=decision.value, resource_id=resource_id,
            created_at=created_at))
        log.append("access_decision", {"decision": decision.value, "reason": outcome.reason},
                   created_at=created_at)

        access_id = mint_identity("access_control", {
            "authorization_id": authorization.authorization_id, "resource_id": resource_id}).id
        access_node = self.lineage.record(make_resource_access_lineage(
            access_id, decision_node.lineage_id, resource_type=resource_type.value,
            resource_id=resource_id, resource_lineage_id=resource_lineage_id, created_at=created_at))
        log.append("resource_access", {"access_id": access_id, "resource_type": resource_type.value,
                                       "resource_id": resource_id}, created_at=created_at)

        # --- content validation -----------------------------------------------
        checks = tuple(self.content_validator.content_checks(
            credential=credential, session=session, authentication=auth, authorization=authorization,
            policy_engine=self.policies))
        content_ok = all(p for _, p, _ in checks)
        validation = SecurityValidationRecord(
            validation_id=content_id("secval", {
                "access_id": access_id, "checks": [[n, bool(p)] for n, p, _ in checks]}),
            ok=content_ok, checks=checks)

        # --- readiness ---------------------------------------------------------
        traceable = self.lineage.verify_chain(access_node.lineage_id)
        pol_ok, _ = self.policies.validate()
        readiness = self.readiness_engine.assess(
            target_id=access_id, authentication_ok=True, authorization_ok=True, policy_ok=pol_ok,
            registered=True, audited=log.verify(), traceable=traceable, validation_ok=content_ok,
            created_at=created_at)
        log.append("readiness_scored", {"readiness_id": readiness.readiness_id,
                                        "classification": readiness.classification.value},
                   created_at=created_at)
        self.registry.register_readiness(readiness)

        # --- version + aggregate ----------------------------------------------
        identity = SecurityIdentity(
            access_id=access_id, user_id=user.user_id, session_id=session.session_id,
            authentication_id=auth.authentication_id, authorization_id=authorization.authorization_id,
            identity_version=mint_identity("access_control", {
                "authorization_id": authorization.authorization_id,
                "resource_id": resource_id}).identity_version)
        dependencies = (user.user_id, credential.credential_id, session.session_id,
                        auth.authentication_id, authorization.authorization_id)
        state_sig = AccessControlRecord.state_signature_of(
            identity=identity, user_id=user.user_id, role=user.role,
            credential_id=credential.credential_id, session_id=session.session_id,
            authentication_id=auth.authentication_id, authorization_id=authorization.authorization_id,
            resource_type=resource_type, resource_id=resource_id, action=action, decision=decision,
            matched_policies=authorization.matched_policies, reason=outcome.reason,
            validation=validation, readiness_id=readiness.readiness_id,
            readiness_class=readiness.classification, dependencies=dependencies)
        version = SecurityVersion(version=SecurityVersion.compute(state_sig, None), previous=None,
                                  reason="access_decided", created_at=created_at)
        log.append("security_version_changed", {"version": version.version}, created_at=created_at)
        log.append("access_registered", {"access_id": access_id, "decision": decision.value},
                   created_at=created_at)

        record = AccessControlRecord(
            identity=identity, user_id=user.user_id, role=user.role,
            credential_id=credential.credential_id, session_id=session.session_id,
            authentication_id=auth.authentication_id, authorization_id=authorization.authorization_id,
            resource_type=resource_type, resource_id=resource_id, action=action, decision=decision,
            matched_policies=authorization.matched_policies, reason=outcome.reason,
            validation=validation, readiness_id=readiness.readiness_id,
            readiness_class=readiness.classification, version=version, owner=owner,
            created_at=created_at, lineage_id=access_node.lineage_id, audit_head=log.head,
            dependencies=dependencies)

        self.registry.register_access(self._registry_record(record))
        self._audit_logs[access_id] = log
        self._context[access_id] = {"record": record, "credential": credential, "session": session,
                                     "authentication": auth, "authorization": authorization,
                                     "readiness": readiness}
        return SecurityOutcome(accepted=True, reason=decision.value, record=record,
                               readiness=readiness, authentication=auth)

    # --- validation + reports -------------------------------------------------
    def integrity(self, record: AccessControlRecord):
        ctx = self._context[record.access_id]
        return self.integrity_validator.validate(
            record=record, credential=ctx["credential"], session=ctx["session"],
            authentication=ctx["authentication"], authorization=ctx["authorization"],
            policy_engine=self.policies, registry=self.registry,
            audit_log=self._audit_logs[record.access_id], lineage_tracker=self.lineage)

    def reports(self, record: AccessControlRecord) -> dict:
        ctx = self._context[record.access_id]
        log = self._audit_logs[record.access_id]
        integrity = self.integrity(record)
        return {
            "authentication_report": _reports.build_authentication_report(
                record, ctx["authentication"], ctx["session"]),
            "authorization_report": _reports.build_authorization_report(record, ctx["authorization"]),
            "access_control_report": _reports.build_access_control_report(record),
            "policy_report": _reports.build_policy_report(self.policies),
            "validation_report": _reports.build_validation_report(record, integrity),
            "readiness_report": _reports.build_readiness_report(record, ctx["readiness"]),
            "audit_report": _reports.build_audit_report(record, log),
            "lineage_report": _reports.build_lineage_report(record, self.lineage),
            "security_summary_report": _reports.build_security_summary_report(
                record, ctx["readiness"], integrity),
        }

    # --- internals ------------------------------------------------------------
    def _require_user(self, username: str) -> SecurityUserRecord:
        if username not in self._users_by_name:
            raise SecurityPlatformError(f"unknown user {username!r}")
        return self._users_by_name[username]

    def _registry_record(self, record: AccessControlRecord):
        from .models.domain import SecurityRegistryRecord
        return SecurityRegistryRecord(
            access_id=record.access_id, user_id=record.user_id, session_id=record.session_id,
            authentication_id=record.authentication_id, authorization_id=record.authorization_id,
            resource_type=record.resource_type.value, resource_id=record.resource_id,
            action=record.action.value, decision=record.decision.value,
            readiness_id=record.readiness_id, version=record.version.version, owner=record.owner,
            creation_date=record.created_at, audit_state=record.audit_head or "",
            lineage_id=record.lineage_id or "", dependencies=record.dependencies)

    @property
    def version(self) -> str:
        return SECURITY_PLATFORM_VERSION


__all__ = ["SecurityPlatformService", "SecurityOutcome", "SecurityPlatformError"]
