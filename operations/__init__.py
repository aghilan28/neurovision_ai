"""``operations`` — Operations Foundation Platform (Productization P8).

Transforms the usable product (P1-P7) into a **deployable** product: runtime
environments, containerization, configuration management, health/readiness, structured
logging, metrics, backup/recovery, a repository-native CI pipeline, operations validation,
and operational reporting. This is the top-level *operationalization* layer (like
``scripts/``): it **composes and observes** the existing systems and **modifies none** of
the AI / backend / frontend workflows.

Boundary note: ``operations`` is not one of the six governed domain packages, so it may
import ``backend``/``frontend`` (it does so lazily, inside functions, so importing
``operations`` stays light enough for the slim frontend container). It never imports
``tests``. Backend never imports operations (one-way, like scripts).

No new models / inference / frontend / backend features are added (NR-13).
"""

from __future__ import annotations

from .version import (
    OPERATIONS_VERSION, OPERATIONS_CONFIG_VERSION, OPERATIONS_ENVIRONMENT_VERSION,
    OPERATIONS_DEPLOYMENT_VERSION, OPERATIONS_HEALTH_VERSION, OPERATIONS_LOGGING_VERSION,
    OPERATIONS_MONITORING_VERSION, OPERATIONS_BACKUP_VERSION, OPERATIONS_RECOVERY_VERSION,
    OPERATIONS_CI_VERSION, OPERATIONS_VALIDATION_VERSION, OPERATIONS_REPORT_VERSION,
)
from .config import (
    AppConfig, ConfigLoader, ConfigValidator, SecretsProvider, build_config_report, ENVIRONMENTS,
)
from .environments import (
    EnvironmentSpec, get_environment, all_environments, build_environments_report,
)
from .deployment import validate_all as validate_deployment, build_deployment_report, build_plans
from .health import HealthChecker, HealthStatus, build_health_report
from .logging import StructuredLogger, BufferSink, StreamSink, build_logging_report
from .monitoring import MetricsRegistry, build_monitoring_report
from .backups import BackupManager, BackupManifest, build_backup_report
from .recovery import RestoreManager, RestoreResult, build_recovery_report
from .ci import CiPipeline, CiStep, ReleaseValidator, default_pipeline, build_ci_report
from .validation import OperationsValidator, build_validation_report
from .reports import build_operations_reports, build_operations_readiness_report

__all__ = [
    "OPERATIONS_VERSION", "OPERATIONS_CONFIG_VERSION", "OPERATIONS_ENVIRONMENT_VERSION",
    "OPERATIONS_DEPLOYMENT_VERSION", "OPERATIONS_HEALTH_VERSION", "OPERATIONS_LOGGING_VERSION",
    "OPERATIONS_MONITORING_VERSION", "OPERATIONS_BACKUP_VERSION", "OPERATIONS_RECOVERY_VERSION",
    "OPERATIONS_CI_VERSION", "OPERATIONS_VALIDATION_VERSION", "OPERATIONS_REPORT_VERSION",
    "AppConfig", "ConfigLoader", "ConfigValidator", "SecretsProvider", "build_config_report",
    "ENVIRONMENTS", "EnvironmentSpec", "get_environment", "all_environments",
    "build_environments_report", "validate_deployment", "build_deployment_report", "build_plans",
    "HealthChecker", "HealthStatus", "build_health_report", "StructuredLogger", "BufferSink",
    "StreamSink", "build_logging_report", "MetricsRegistry", "build_monitoring_report",
    "BackupManager", "BackupManifest", "build_backup_report", "RestoreManager", "RestoreResult",
    "build_recovery_report", "CiPipeline", "CiStep", "ReleaseValidator", "default_pipeline",
    "build_ci_report", "OperationsValidator", "build_validation_report",
    "build_operations_reports", "build_operations_readiness_report",
]
