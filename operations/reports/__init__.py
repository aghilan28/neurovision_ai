"""``operations/reports`` — operations reporting (P8-K).

Aggregates the per-subsystem reports into the eight mandated operational reports
(deployment, health, monitoring, logging, recovery, CI, validation) plus the
**Operations Readiness Report** — a single deterministic verdict over every operational
dimension that decides whether the product is deployment-ready.
"""

from __future__ import annotations

from typing import Optional

from ..util import fingerprint
from ..version import OPERATIONS_REPORT_VERSION


def build_operations_readiness_report(*, deployment: dict, health: dict, monitoring: dict,
                                      logging_report: dict, backup: dict, recovery: dict,
                                      ci: dict, validation: dict,
                                      config: Optional[dict] = None) -> dict:
    dimensions = {
        "configuration": bool((config or {}).get("ok", True)),
        "deployment": bool(deployment.get("ok")),
        "containers": bool(deployment.get("ok")),
        "health": bool(health.get("healthy")),
        "logging": bool(logging_report.get("machine_readable")),
        "monitoring": monitoring.get("cloud_dependencies") is False,
        "backup": bool(backup.get("backup_id")),
        "recovery": bool(recovery.get("ok")),
        "ci": bool(ci.get("quality_gate_passed")),
        "operations_validation": bool(validation.get("ok")),
    }
    ready = all(dimensions.values())
    return {
        "report_type": "operations_readiness", "report_version": OPERATIONS_REPORT_VERSION,
        "deployment_ready": ready,
        "dimensions": dimensions,
        "failed_dimensions": sorted(k for k, v in dimensions.items() if not v),
        "signature": fingerprint(dimensions),
    }


def build_operations_reports(*, deployment: dict, health: dict, monitoring: dict,
                             logging_report: dict, backup: dict, recovery: dict,
                             ci: dict, validation: dict, config: Optional[dict] = None) -> dict:
    readiness = build_operations_readiness_report(
        deployment=deployment, health=health, monitoring=monitoring,
        logging_report=logging_report, backup=backup, recovery=recovery, ci=ci,
        validation=validation, config=config)
    return {
        "deployment_report": deployment,
        "health_report": health,
        "monitoring_report": monitoring,
        "logging_report": logging_report,
        "recovery_report": recovery,
        "ci_report": ci,
        "validation_report": validation,
        "operations_readiness_report": readiness,
    }


__all__ = ["build_operations_readiness_report", "build_operations_reports"]
