"""``certification/evidence`` — the single evidence bundle (P10).

Collects all verifiable evidence from the real P1-P9 systems **once** so every audit,
scorecard, risk, gap, and the final decision rest on the same facts: the P9 validation
program, the P8 operations health/validation/deployment/config, the end-to-end journey,
and platform compliance. No assumptions — only collected evidence.
"""

from __future__ import annotations

import tempfile
from typing import Optional

from ..audits.end_to_end import EndToEndCertification
from ..compliance import collect_compliance
from ..util import fingerprint
from ..version import CERTIFICATION_EVIDENCE_VERSION


class EvidenceCollector:
    """Runs the platform once and assembles the evidence bundle."""

    def collect(self, fixtures: dict, *, validation_kwargs: Optional[dict] = None,
                workspace_dir: Optional[str] = None) -> dict:
        from validation import run_validation
        from operations.health import HealthChecker
        from operations.validation import OperationsValidator
        from operations.deployment import build_deployment_report
        from operations.config import ConfigLoader, ConfigValidator, build_config_report

        ws = workspace_dir or tempfile.mkdtemp(prefix="nv_p10_")
        vkwargs = {"benchmark_runs": 2, "reliability_repeats": 2, "reliability_stress": 3,
                   "cross_instance": False}
        vkwargs.update(validation_kwargs or {})

        validation_result = run_validation(dict(fixtures), workspace_dir=f"{ws}/val", **vkwargs)
        e2e_result = EndToEndCertification().run(dict(fixtures), workspace_dir=f"{ws}/e2e")

        operations_health = HealthChecker(workspace_dir=f"{ws}/health").check_all()
        operations_validation = OperationsValidator(workspace_dir=f"{ws}/opsval").validate()
        deployment = build_deployment_report()
        cfg = ConfigLoader().load("testing")
        config_report = build_config_report(cfg, ConfigValidator().validate(cfg))
        # production config WITHOUT injected secrets -> surfaces the security gap as evidence
        prod_cfg = ConfigLoader(env={"NV_ENV": "production"}).load("production")
        prod_secrets_present = all(
            c.passed for c in ConfigValidator().validate(prod_cfg)
            if c.name.startswith("secret_strength"))

        compliance = collect_compliance(validation_result=validation_result, e2e_result=e2e_result)

        bundle = {
            "evidence_version": CERTIFICATION_EVIDENCE_VERSION,
            "validation": validation_result,
            "e2e": e2e_result,
            "operations_health": operations_health,
            "operations_validation": operations_validation,
            "deployment": deployment,
            "config": config_report,
            "production_secrets_injected": prod_secrets_present,
            "compliance": compliance,
        }
        bundle["signature"] = fingerprint({
            "validation_complete": validation_result.get("validation_complete"),
            "e2e_ok": e2e_result.get("ok"),
            "ops_healthy": operations_health.get("healthy"),
            "ops_validation_ok": operations_validation.get("ok"),
            "deployment_ok": deployment.get("ok"),
            "compliance_ok": compliance.get("ok"),
        })
        return bundle


__all__ = ["EvidenceCollector"]
