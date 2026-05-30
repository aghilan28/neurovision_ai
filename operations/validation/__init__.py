"""``operations/validation`` — operations integrity validation (P8-J).

Runs the eight mandated integrity checks across the operational subsystems by actually
exercising them (config load/validate, deployment definitions, health checks, metrics,
a backup + restore round-trip, and the CI pipeline definition). Returns a structured,
deterministic report. It never modifies any P1-P7 workflow.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Optional

from ..config import ConfigLoader, ConfigValidator
from ..deployment import validate_all as validate_deployment, build_plans
from ..health import HealthChecker
from ..monitoring import MetricsRegistry, build_monitoring_report
from ..backups import BackupManager
from ..recovery import RestoreManager
from ..ci import CiPipeline
from ..version import OPERATIONS_VALIDATION_VERSION


@dataclass(frozen=True)
class OpsCheck:
    name: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


class OperationsValidator:
    """The eight operations-integrity checks."""

    def __init__(self, *, workspace_dir: Optional[str] = None):
        self.workspace_dir = workspace_dir or tempfile.mkdtemp(prefix="nv_ops_val_")

    def validate(self, *, environment: str = "testing") -> dict:
        checks: list[OpsCheck] = []

        # 1. configuration integrity
        try:
            cfg = ConfigLoader().load(environment)
            cfg_checks = ConfigValidator().validate(cfg)
            checks.append(OpsCheck("configuration_integrity", all(c.passed for c in cfg_checks),
                                   f"env={environment} checks={len(cfg_checks)}"))
        except Exception as exc:
            checks.append(OpsCheck("configuration_integrity", False, f"error: {exc}"))

        # 2. deployment integrity (dockerfiles + compose structurally valid)
        try:
            dep = validate_deployment()
            checks.append(OpsCheck("deployment_integrity", dep["ok"],
                                   f"checks={len(dep['checks'])}"))
        except Exception as exc:
            checks.append(OpsCheck("deployment_integrity", False, f"error: {exc}"))

        # 3. container integrity (build plans well-formed; dockerfiles present)
        try:
            plans = build_plans(os.getcwd())
            ok = (len(plans) == 2 and any(p.slim for p in plans)
                  and all(os.path.exists(p.dockerfile) for p in plans))
            checks.append(OpsCheck("container_integrity", ok,
                                   f"plans={[p.name for p in plans]}"))
        except Exception as exc:
            checks.append(OpsCheck("container_integrity", False, f"error: {exc}"))

        # 4. health integrity
        try:
            health = HealthChecker(workspace_dir=os.path.join(self.workspace_dir, "health")
                                   ).check_all(environment=environment)
            checks.append(OpsCheck("health_integrity", health["healthy"],
                                   f"components={len(health['components'])}"))
        except Exception as exc:
            checks.append(OpsCheck("health_integrity", False, f"error: {exc}"))

        # 5. monitoring integrity
        try:
            m = MetricsRegistry()
            m.record_request("login", "ok")
            m.record_workflow("generated", 7)
            m.record_prediction("high", "well_calibrated")
            m.record_health("backend", True)
            report = build_monitoring_report(m)
            ok = (report["cloud_dependencies"] is False and report["n_counters"] >= 1
                  and report["n_gauges"] >= 1)
            checks.append(OpsCheck("monitoring_integrity", ok,
                                   f"counters={report['n_counters']} gauges={report['n_gauges']}"))
        except Exception as exc:
            checks.append(OpsCheck("monitoring_integrity", False, f"error: {exc}"))

        # 6 + 7. backup + recovery integrity (round-trip a real backend registry)
        try:
            from backend.application_backend import ApplicationBackendService, DeterministicEntropy
            svc = ApplicationBackendService(
                workspace_dir=os.path.join(self.workspace_dir, "be"),
                entropy=DeterministicEntropy("opsval"))
            svc.do_register(username="ops.val", password="password123", roles=["clinician"])
            cfg = ConfigLoader().load(environment)
            dest = os.path.join(self.workspace_dir, "backup")
            manifest = BackupManager().backup(
                dest, registry=svc.registry, config=cfg,
                artifact_roots={"raw": os.path.join(self.workspace_dir, "be", "raw")})
            backup_ok = bool(manifest.signature) and len(manifest.components) >= 2
            checks.append(OpsCheck("backup_integrity", backup_ok,
                                   f"components={len(manifest.components)}"))
            restore = RestoreManager().restore(dest)
            checks.append(OpsCheck("recovery_integrity", restore.ok,
                                   f"checks={[c.name for c in restore.checks if not c.passed]}"))
        except Exception as exc:
            checks.append(OpsCheck("backup_integrity", False, f"error: {exc}"))
            checks.append(OpsCheck("recovery_integrity", False, f"error: {exc}"))

        # 8. ci integrity (pipeline definition well-formed)
        try:
            pipeline = CiPipeline()
            steps = pipeline.steps
            ok = (len(steps) >= 3 and all(s.command for s in steps)
                  and {s.kind for s in steps} >= {"build", "lint", "test"})
            checks.append(OpsCheck("ci_integrity", ok, f"steps={[s.name for s in steps]}"))
        except Exception as exc:
            checks.append(OpsCheck("ci_integrity", False, f"error: {exc}"))

        return {
            "validation_version": OPERATIONS_VALIDATION_VERSION,
            "environment": environment,
            "ok": all(c.passed for c in checks),
            "checks": [c.to_dict() for c in checks],
        }


def build_validation_report(result: dict) -> dict:
    return {"report_type": "operations_validation", **result}


__all__ = ["OperationsValidator", "OpsCheck", "build_validation_report"]
