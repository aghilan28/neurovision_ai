"""Security *integrity* validation (DRP5-J, post-build).

Reuses ``ml.validation.ValidationReport`` to produce the mandated checks over a finalized,
registered access decision: credential / session / authorization / policy / registry / audit /
lineage / version integrity. The result shape matches the rest of the platform (NR-6).
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import SecurityVersion

# the lineage kinds that prove an access decision traces back to the user
_REQUIRED_CHAIN_KINDS = {
    "security_user", "credential", "authentication", "authorization", "access_decision",
    "resource_access",
}


class SecurityIntegrityValidator:
    """Runs the mandated security integrity checks."""

    def validate(self, *, record: Any, credential: Any, session: Any, authentication: Any,
                 authorization: Any, policy_engine: Any, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()

        # --- credential integrity (hashed; no plaintext) ---
        report.add("credential_integrity",
                   bool(credential.hash_hex) and credential.algorithm == "pbkdf2_hmac_sha256",
                   f"algorithm={credential.algorithm} iterations={credential.iterations}")

        # --- session integrity ---
        report.add("session_integrity",
                   bool(session.token_fingerprint) and session.credential_id == credential.credential_id,
                   f"status={session.status.value}")

        # --- authorization integrity (explicit permission; default-deny) ---
        permitted_ok = (record.decision.value != "permitted" or len(record.matched_policies) > 0)
        report.add("authorization_integrity",
                   authorization.authorization_id == record.authorization_id and permitted_ok,
                   f"decision={record.decision.value} policies={len(record.matched_policies)}")

        # --- policy integrity ---
        pol_ok, _problems = policy_engine.validate()
        report.add("policy_integrity", bool(pol_ok and len(policy_engine.list_policies()) > 0),
                   f"n_policies={len(policy_engine.list_policies())}")

        # --- registry integrity ---
        try:
            rec = registry.get_access(record.access_id)
            ok = (rec.version == record.version.version and rec.lineage_id == record.lineage_id
                  and registry.orphans() == [])
            report.add("registry_integrity", bool(ok),
                       f"registered={rec.version} orphans={len(registry.orphans())}")
        except Exception as exc:  # pragma: no cover - defensive
            report.add("registry_integrity", False, f"error: {exc}")

        # --- audit integrity ---
        try:
            ok = audit_log.verify() and record.audit_head == audit_log.head
            report.add("audit_integrity", bool(ok),
                       f"chain_verified={audit_log.verify()} head_match={record.audit_head == audit_log.head}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # --- lineage integrity (resource-access chain reaches the user root) ---
        try:
            chain_ok = bool(record.lineage_id) and lineage_tracker.verify_chain(record.lineage_id)
            kinds = ({r.kind for r in lineage_tracker.chain(record.lineage_id)}
                     if record.lineage_id else set())
            reaches = _REQUIRED_CHAIN_KINDS <= kinds
            ids_ok = (validate_identity(record.access_id, "access_control")[0]
                      and validate_identity(record.authorization_id, "authorization")[0]
                      and validate_identity(credential.credential_id, "credential")[0])
            report.add("lineage_integrity", bool(chain_ok and reaches and ids_ok),
                       f"chain_ok={chain_ok} reaches_user={reaches}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # --- version integrity ---
        try:
            expected = SecurityVersion.compute(record.state_signature(), record.version.previous)
            report.add("version_integrity", record.version.version == expected,
                       f"recorded={record.version.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report


__all__ = ["SecurityIntegrityValidator"]
