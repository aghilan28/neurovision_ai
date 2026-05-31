"""Security report builders (DRP5-L; reproducible, version-tagged).

Each report is a plain JSON-able dict, deterministic for a given record/registry state (no
wall-clock, no randomness, no secret material). Mirrors the platform report style.
"""

from __future__ import annotations

from typing import Any, Optional

from ..version import SECURITY_REPORT_VERSION, SECURITY_PLATFORM_VERSION


def _header(report_type: str, record: Any) -> dict:
    return {
        "report_type": report_type, "security_report_version": SECURITY_REPORT_VERSION,
        "security_platform_version": SECURITY_PLATFORM_VERSION, "access_id": record.access_id,
        "user_id": record.user_id, "session_id": record.session_id,
        "authentication_id": record.authentication_id, "authorization_id": record.authorization_id,
        "decision": record.decision.value, "access_version": record.version.version,
    }


def build_authentication_report(record: Any, authentication: Any, session: Any) -> dict:
    return {**_header("authentication", record), "authentication": authentication.to_dict(),
            "session": session.to_dict()}


def build_authorization_report(record: Any, authorization: Any) -> dict:
    return {**_header("authorization", record), "authorization": authorization.to_dict()}


def build_access_control_report(record: Any) -> dict:
    return {**_header("access_control", record), "resource_type": record.resource_type.value,
            "resource_id": record.resource_id, "action": record.action.value,
            "matched_policies": list(record.matched_policies), "reason": record.reason}


def build_policy_report(policy_engine: Any) -> dict:
    return {
        "report_type": "policy", "security_report_version": SECURITY_REPORT_VERSION,
        "security_platform_version": SECURITY_PLATFORM_VERSION, "policies": policy_engine.to_dict(),
    }


def build_validation_report(record: Any, integrity_report: Optional[Any] = None) -> dict:
    out = {**_header("validation", record), "content_validation": record.validation.to_dict()}
    if integrity_report is not None:
        out["integrity_validation"] = integrity_report.to_dict()
        out["ok"] = bool(record.validation.ok and integrity_report.ok)
    else:
        out["ok"] = bool(record.validation.ok)
    return out


def build_readiness_report(record: Any, readiness: Any) -> dict:
    return {**_header("readiness", record), "readiness": readiness.to_dict()}


def build_audit_report(record: Any, audit_log: Any) -> dict:
    return {
        **_header("audit", record), "audit_head": audit_log.head,
        "chain_verified": audit_log.verify(), "n_events": len(audit_log),
        "events": [e.to_dict() for e in audit_log.events()],
    }


def build_lineage_report(record: Any, lineage_tracker: Any) -> dict:
    chain = lineage_tracker.chain(record.lineage_id) if record.lineage_id else []
    return {
        **_header("lineage", record), "lineage_id": record.lineage_id,
        "chain_verified": lineage_tracker.verify_chain(record.lineage_id) if record.lineage_id else False,
        "chain_length": len(chain), "chain_kinds": [r.kind for r in chain],
        "chain": [r.to_dict() for r in chain],
    }


def build_security_summary_report(record: Any, readiness: Any,
                                  integrity_report: Optional[Any] = None) -> dict:
    out = {
        **_header("summary", record), "readiness_class": record.readiness_class.value,
        "readiness_score": readiness.score, "permitted": record.permitted,
        "resource_type": record.resource_type.value, "action": record.action.value,
        "content_validation_ok": record.validation.ok, "record": record.to_dict(),
    }
    if integrity_report is not None:
        out["integrity_validation"] = integrity_report.to_dict()
        out["ok"] = bool(record.validation.ok and integrity_report.ok)
    else:
        out["ok"] = bool(record.validation.ok)
    return out


__all__ = [
    "build_authentication_report", "build_authorization_report", "build_access_control_report",
    "build_policy_report", "build_validation_report", "build_readiness_report", "build_audit_report",
    "build_lineage_report", "build_security_summary_report",
]
