"""``certification/deployment`` — deployment readiness audit (P10-C).

Determines build / deployment / configuration / recovery / monitoring / operational /
security readiness from the evidence bundle only (the P8 operations evidence + the
end-to-end recovery + the config/secrets evidence). No assumptions.
"""

from __future__ import annotations

from ..util import fingerprint
from ..version import CERTIFICATION_DEPLOYMENT_VERSION


def _e2e_check(bundle: dict, name: str) -> bool:
    for c in bundle["e2e"].get("checks", []):
        if c["name"] == name:
            return bool(c["passed"])
    return False


class DeploymentReadinessAudit:
    def run(self, bundle: dict) -> dict:
        deployment_ok = bool(bundle["deployment"].get("ok"))
        ops_health = bool(bundle["operations_health"].get("healthy"))
        ops_val = bool(bundle["operations_validation"].get("ok"))
        config_ok = bool(bundle["config"].get("ok"))
        e2e_ok = bool(bundle["e2e"].get("ok"))
        prod_secrets = bool(bundle.get("production_secrets_injected"))

        areas = [
            {"area": "build_readiness", "ready": deployment_ok,
             "detail": "container build definitions valid (frontend image build verified in P8)"},
            {"area": "deployment_readiness", "ready": deployment_ok and e2e_ok,
             "detail": "compose + images defined; end-to-end journey runs"},
            {"area": "configuration_readiness", "ready": config_ok,
             "detail": "config loads + validates; secrets injectable, never hardcoded"},
            {"area": "recovery_readiness", "ready": _e2e_check(bundle, "recovery_capability"),
             "detail": "backup + verified (tamper-detecting) restore"},
            {"area": "monitoring_readiness", "ready": _e2e_check(bundle, "operational_monitoring")
             and ops_health, "detail": "structured logging + metrics + health checks"},
            {"area": "operational_readiness", "ready": ops_val and ops_health,
             "detail": "operations validation (8 checks) + health all green"},
            {"area": "security_readiness", "ready": prod_secrets,
             "detail": "local PBKDF2 auth + injectable secrets; production secrets NOT injected "
                       "in-repo (must be provided at deploy) and no TLS/rate-limiting hardening"},
        ]
        ready = all(a["ready"] for a in areas)
        return {
            "deployment_version": CERTIFICATION_DEPLOYMENT_VERSION,
            "ready": ready, "areas": areas,
            "ready_areas": [a["area"] for a in areas if a["ready"]],
            "not_ready_areas": [a["area"] for a in areas if not a["ready"]],
            "signature": fingerprint([(a["area"], a["ready"]) for a in areas]),
        }


__all__ = ["DeploymentReadinessAudit"]
