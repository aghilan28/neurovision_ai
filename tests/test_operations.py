"""Tests for Productization P8 — Operations Foundation Platform.

Exercises the real operational subsystems over the real P1-P7 systems (no replacement
systems): configuration, containers/deployment definitions, health checks, monitoring,
logging, backup + recovery, CI validation, operations validation, boundary conditions,
and failure conditions.
"""

from __future__ import annotations

import ast
import os
import pathlib


import operations as ops
from operations.config import ConfigLoader, ConfigValidator, SecretsProvider, REDACTED
from operations.deployment import (
    validate_dockerfile, validate_compose, validate_all, BACKEND_DOCKERFILE, FRONTEND_DOCKERFILE,
)
from operations.health import HealthChecker
from operations.logging import StructuredLogger, BufferSink
from operations.monitoring import MetricsRegistry, build_monitoring_report
from operations.backups import BackupManager
from operations.recovery import RestoreManager
from operations.ci import CiPipeline, ReleaseValidator
from operations.validation import OperationsValidator
from operations.reports import build_operations_reports

from backend.application_backend import ApplicationBackendService, DeterministicEntropy

REPO = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ["valid.edf", "valid_edf_plus.edf", "valid.bdf", "valid_bdf_plus.bdf",
            "valid_raw.fif", "valid.set"]


def _cohort(eeg_fixtures):
    return [(f"P-{i}", f"C-{i}", eeg_fixtures[n]) for i, n in enumerate(FIXTURES)]


# =============================================================================
# P8-D — Configuration
# =============================================================================
def test_config_testing_loads_and_validates():
    cfg = ConfigLoader().load("testing")
    assert cfg.environment == "testing"
    assert all(c.passed for c in ConfigValidator().validate(cfg))


def test_production_rejects_placeholder_secrets():
    # production requires real secrets; the template uses an injection placeholder
    env = {"NV_ENV": "production", "NV_AUTH_SECRET_KEY": "__INJECT_AT_DEPLOY__",
           "NV_ADMIN_BOOTSTRAP_PASSWORD": ""}
    cfg = ConfigLoader(env=env).load("production")
    checks = ConfigValidator().validate(cfg)
    assert not all(c.passed for c in checks)
    # with real injected secrets it passes
    env2 = {"NV_ENV": "production", "NV_AUTH_SECRET_KEY": "a-real-strong-secret-value",
            "NV_ADMIN_BOOTSTRAP_PASSWORD": "another-strong-secret"}
    cfg2 = ConfigLoader(env=env2).load("production")
    assert all(c.passed for c in ConfigValidator().validate(cfg2))


def test_secrets_are_redacted_in_reports():
    env = {"NV_ENV": "production", "NV_AUTH_SECRET_KEY": "super-secret",
           "NV_ADMIN_BOOTSTRAP_PASSWORD": "super-secret-2"}
    cfg = ConfigLoader(env=env).load("production")
    serialized = str(cfg.to_dict(redact=True))
    assert "super-secret" not in serialized and REDACTED in serialized


def test_secrets_provider_reads_env_and_file(tmp_path):
    sfile = tmp_path / "secrets.env"
    sfile.write_text("NV_AUTH_SECRET_KEY=from-file\n", encoding="utf-8")
    provider = SecretsProvider(env={"NV_SECRETS_FILE": str(sfile)}, secrets_file=str(sfile))
    assert provider.get("NV_AUTH_SECRET_KEY") == "from-file"


# =============================================================================
# P8-B — Environments
# =============================================================================
def test_environments_defined_with_templates_and_no_real_secrets():
    envs = ops.all_environments()
    assert {e.name for e in envs} == {"development", "testing", "staging", "production"}
    for e in envs:
        assert os.path.exists(e.template_file)
        text = open(e.template_file, encoding="utf-8").read()
        # secret lines must be empty/placeholder, never a real value
        for line in text.splitlines():
            if line.startswith("NV_AUTH_SECRET_KEY=") or line.startswith("NV_ADMIN_BOOTSTRAP_PASSWORD="):
                val = line.split("=", 1)[1]
                assert val in ("", "__INJECT_AT_DEPLOY__")


# =============================================================================
# P8-C — Containers / deployment definitions
# =============================================================================
def test_deployment_definitions_valid():
    result = validate_all()
    assert result["ok"], [c for c in result["checks"] if not c["passed"]]


def test_dockerfiles_pin_base_and_bake_no_secrets():
    for path, name in ((BACKEND_DOCKERFILE, "backend"), (FRONTEND_DOCKERFILE, "frontend")):
        checks = {c.name: c.passed for c in validate_dockerfile(path, name=name)}
        assert checks[f"{name}:base_pinned"]
        assert checks[f"{name}:no_baked_secrets"]
        assert checks[f"{name}:has_healthcheck"]
        assert checks[f"{name}:has_start_command"]


def test_compose_is_structurally_valid():
    checks = {c.name: c.passed for c in validate_compose()}
    assert checks["compose:backend_service"] and checks["compose:frontend_service"]
    assert checks["compose:no_inline_secrets"] and checks["compose:volumes"]


# =============================================================================
# P8-E — Health
# =============================================================================
def test_health_checks_pass(tmp_path):
    result = HealthChecker(workspace_dir=str(tmp_path)).check_all()
    assert result["healthy"]
    assert {"backend", "frontend", "model", "storage", "workflow", "liveness",
            "readiness", "system"} <= set(result["components"])


def test_liveness_and_readiness(tmp_path):
    checker = HealthChecker(workspace_dir=str(tmp_path))
    assert checker.liveness().healthy
    assert checker.readiness(environment="testing").healthy


# =============================================================================
# P8-F — Logging
# =============================================================================
def test_logging_is_structured_machine_readable_and_deterministic():
    def run():
        sink = BufferSink()
        log = StructuredLogger(sink=sink, min_level="debug")
        log.request(request_id="r1", operation="login", status="ok")
        log.workflow(workflow_id="w1", stage="predict", status="completed")
        log.prediction(prediction_id="p1", predicted_label="0", confidence_level="high")
        log.failure(error_type="ValueError", message="bad", where="x")
        return sink.records()
    a, b = run(), run()
    assert a == b                              # deterministic
    assert all("level" in r and "event" in r and "seq" in r for r in a)
    kinds = {r.get("kind") for r in a}
    assert {"request", "workflow", "prediction", "error"} <= kinds


# =============================================================================
# P8-G — Monitoring
# =============================================================================
def test_monitoring_generates_metrics_without_cloud():
    m = MetricsRegistry()
    m.record_request("login", "ok")
    m.record_request("upload_eeg", "created")
    m.record_workflow("generated", 7)
    m.record_prediction("high", "well_calibrated")
    m.record_error("AuthError")
    m.record_health("backend", True)
    report = build_monitoring_report(m)
    assert report["cloud_dependencies"] is False
    assert report["metrics"]["counters"]["app_requests_total"] == 2
    assert report["metrics"]["gauges"]["health.backend"] == 1.0


# =============================================================================
# P8-H — Backup & recovery
# =============================================================================
def test_backup_and_recovery_roundtrip(tmp_path):
    svc = ApplicationBackendService(workspace_dir=str(tmp_path / "be"),
                                    entropy=DeterministicEntropy("bk"))
    svc.do_register(username="ops.bk", password="password123", roles=["clinician"])
    cfg = ConfigLoader().load("testing")
    dest = str(tmp_path / "backup")
    manifest = BackupManager().backup(dest, registry=svc.registry, config=cfg)
    assert manifest.signature and len(manifest.components) == 2
    result = RestoreManager().restore(dest)
    assert result.ok
    assert {"checksums_match", "registry_reloaded", "no_orphans", "backup_secret_safe"} <= {
        c.name for c in result.checks if c.passed}


def test_recovery_detects_tampering(tmp_path):
    svc = ApplicationBackendService(workspace_dir=str(tmp_path / "be"),
                                    entropy=DeterministicEntropy("bk2"))
    svc.do_register(username="ops.bk2", password="password123", roles=["clinician"])
    dest = str(tmp_path / "backup")
    BackupManager().backup(dest, registry=svc.registry, config=ConfigLoader().load("testing"))
    # tamper with the backed-up registry
    with open(os.path.join(dest, "registry.json"), "a", encoding="utf-8") as fh:
        fh.write("TAMPER")
    result = RestoreManager().restore(dest)
    assert not result.ok
    assert any(c.name == "checksums_match" and not c.passed for c in result.checks)


# =============================================================================
# P8-I — CI
# =============================================================================
def test_ci_pipeline_definition_and_build_step():
    pipeline = CiPipeline()
    assert {s.kind for s in pipeline.steps} >= {"build", "lint", "test"}
    results = pipeline.run(only=["build_verification"])
    assert results and pipeline.quality_gate(results)


def test_release_validator():
    pipeline = CiPipeline()
    results = pipeline.run(only=["build_verification"])
    decision = ReleaseValidator().validate(results, ops_ok=True)
    assert decision["release_ready"] is True


# =============================================================================
# P8-J / P8-K — Operations validation + reports
# =============================================================================
def test_operations_validation_all_pass(tmp_path):
    result = OperationsValidator(workspace_dir=str(tmp_path)).validate()
    assert result["ok"], [c for c in result["checks"] if not c["passed"]]
    assert len(result["checks"]) == 8


def test_operations_reports_and_readiness(tmp_path):
    from operations.deployment import build_deployment_report
    from operations.config import build_config_report
    from operations.backups import build_backup_report
    from operations.recovery import build_recovery_report
    from operations.ci import build_ci_report

    cfg = ConfigLoader().load("testing")
    svc = ApplicationBackendService(workspace_dir=str(tmp_path / "be"),
                                    entropy=DeterministicEntropy("rep"))
    dest = str(tmp_path / "bk")
    manifest = BackupManager().backup(dest, registry=svc.registry, config=cfg)
    log = StructuredLogger(min_level="debug")
    log.request(request_id="r", operation="login", status="ok")
    reports = build_operations_reports(
        deployment=build_deployment_report(),
        health=HealthChecker(workspace_dir=str(tmp_path / "h")).check_all(),
        monitoring=build_monitoring_report(MetricsRegistry()),
        logging_report=ops.build_logging_report(log),
        backup=build_backup_report(manifest),
        recovery=build_recovery_report(RestoreManager().restore(dest)),
        ci=build_ci_report(CiPipeline().run(only=["build_verification"])),
        validation=OperationsValidator(workspace_dir=str(tmp_path / "v")).validate(),
        config=build_config_report(cfg, ConfigValidator().validate(cfg)))
    assert set(reports) == {"deployment_report", "health_report", "monitoring_report",
                            "logging_report", "recovery_report", "ci_report", "validation_report",
                            "operations_readiness_report"}
    assert reports["operations_readiness_report"]["deployment_ready"] is True


# =============================================================================
# Final deliverable — deployable pipeline smoke (real upload -> prediction)
# =============================================================================
def test_deployable_pipeline_smoke(eeg_fixtures, tmp_path):
    checker = HealthChecker(workspace_dir=str(tmp_path))
    status = checker.smoke_pipeline(_cohort(eeg_fixtures), eeg_fixtures["valid.edf"])
    assert status.healthy, status.detail


# =============================================================================
# Boundary — operations is one-way (no domain package imports operations)
# =============================================================================
def test_no_domain_package_imports_operations():
    for pkg in ("preprocessing", "datasets", "ml", "evaluation", "backend", "frontend"):
        for path in (REPO / pkg).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    assert all(a.name.split(".")[0] != "operations" for a in node.names), path
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    assert node.module.split(".")[0] != "operations", path
