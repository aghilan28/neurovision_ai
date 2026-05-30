"""``operations.cli`` — the operational command line (P8).

A repository-native operations entrypoint usable directly and as a container command /
healthcheck. Subcommands print machine-readable JSON and exit non-zero on failure:

    live | ready | health | config | metrics | validate | report | backup | restore

``live`` is intentionally dependency-light (no backend import) so it works as a slim
container's healthcheck; heavier subcommands import the platform lazily.
"""

from __future__ import annotations

import argparse
import json
from typing import Optional


def _emit(payload: dict, ok: bool) -> int:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str))
    return 0 if ok else 1


def _cmd_live(_args) -> int:
    from .health import HealthChecker
    s = HealthChecker().liveness()
    return _emit({"command": "live", **s.to_dict()}, s.healthy)


def _cmd_ready(args) -> int:
    from .health import HealthChecker
    s = HealthChecker().readiness(environment=args.environment)
    return _emit({"command": "ready", **s.to_dict()}, s.healthy)


def _cmd_health(args) -> int:
    from .health import HealthChecker, build_health_report
    result = HealthChecker().check_all(environment=args.environment)
    return _emit({"command": "health", **build_health_report(result)}, result["healthy"])


def _cmd_config(args) -> int:
    from .config import ConfigLoader, ConfigValidator, build_config_report
    cfg = ConfigLoader().load(args.environment)
    report = build_config_report(cfg, ConfigValidator().validate(cfg))
    return _emit({"command": "config", **report}, report["ok"])


def _cmd_metrics(_args) -> int:
    from .monitoring import MetricsRegistry, build_monitoring_report
    return _emit({"command": "metrics", **build_monitoring_report(MetricsRegistry())}, True)


def _cmd_validate(args) -> int:
    from .validation import OperationsValidator
    result = OperationsValidator().validate(environment=args.environment)
    return _emit({"command": "validate", **result}, result["ok"])


def _cmd_backup(args) -> int:
    from .config import ConfigLoader
    from .backups import BackupManager, build_backup_report
    from backend.application_backend import ApplicationBackendService, DeterministicEntropy
    svc = ApplicationBackendService(entropy=DeterministicEntropy("cli-backup"))
    cfg = ConfigLoader().load(args.environment)
    manifest = BackupManager().backup(args.dest, registry=svc.registry, config=cfg)
    return _emit({"command": "backup", **build_backup_report(manifest)}, True)


def _cmd_restore(args) -> int:
    from .recovery import RestoreManager, build_recovery_report
    result = RestoreManager().restore(args.dest)
    return _emit({"command": "restore", **build_recovery_report(result)}, result.ok)


def _cmd_report(args) -> int:
    from .config import ConfigLoader, ConfigValidator, build_config_report
    from .deployment import build_deployment_report
    from .health import HealthChecker
    from .monitoring import MetricsRegistry, build_monitoring_report
    from .logging import StructuredLogger, build_logging_report
    from .backups import BackupManager, build_backup_report
    from .recovery import RestoreManager, build_recovery_report
    from .ci import build_ci_report
    from .validation import OperationsValidator
    from .reports import build_operations_reports
    import tempfile
    import os

    tmp = tempfile.mkdtemp(prefix="nv_ops_report_")
    cfg = ConfigLoader().load(args.environment)
    config_report = build_config_report(cfg, ConfigValidator().validate(cfg))
    deployment = build_deployment_report()
    health = HealthChecker(workspace_dir=os.path.join(tmp, "h")).check_all(environment=args.environment)
    logger = StructuredLogger(min_level="debug")
    logger.request(request_id="r", operation="login", status="ok")
    logging_report = build_logging_report(logger)
    monitoring = build_monitoring_report(MetricsRegistry())
    from backend.application_backend import ApplicationBackendService, DeterministicEntropy
    svc = ApplicationBackendService(workspace_dir=os.path.join(tmp, "be"),
                                    entropy=DeterministicEntropy("cli-report"))
    dest = os.path.join(tmp, "backup")
    manifest = BackupManager().backup(dest, registry=svc.registry, config=cfg)
    backup_report = build_backup_report(manifest)
    recovery = build_recovery_report(RestoreManager().restore(dest))
    ci = build_ci_report([])
    validation = OperationsValidator(workspace_dir=os.path.join(tmp, "v")).validate(
        environment=args.environment)
    reports = build_operations_reports(
        deployment=deployment, health=health, monitoring=monitoring,
        logging_report=logging_report, backup=backup_report, recovery=recovery, ci=ci,
        validation=validation, config=config_report)
    ready = reports["operations_readiness_report"]["deployment_ready"]
    return _emit({"command": "report", **reports["operations_readiness_report"]}, ready)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="operations.cli", description="NeuroVision operations CLI")
    sub = p.add_subparsers(dest="command", required=True)
    for name, fn, needs_env, needs_dest in [
        ("live", _cmd_live, False, False), ("ready", _cmd_ready, True, False),
        ("health", _cmd_health, True, False), ("config", _cmd_config, True, False),
        ("metrics", _cmd_metrics, False, False), ("validate", _cmd_validate, True, False),
        ("report", _cmd_report, True, False), ("backup", _cmd_backup, True, True),
        ("restore", _cmd_restore, False, True),
    ]:
        sp = sub.add_parser(name)
        if needs_env:
            sp.add_argument("--environment", default="testing")
        if needs_dest:
            sp.add_argument("--dest", required=True)
        sp.set_defaults(_fn=fn)
    return p


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    return args._fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
