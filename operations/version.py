"""Version identities for the Operations Foundation Platform (Productization P8).

Operations is the top-level *operationalization* layer (like ``scripts/``): it composes
and observes the existing P1-P7 systems to make the product deployable, without modifying
any AI / backend / frontend workflow. Every operational artifact (config, health result,
metric, log record, backup manifest, report) records the versions that produced it so the
operational state is reproducible and auditable. Bump a version when behaviour changes.
"""

from __future__ import annotations

OPERATIONS_VERSION: str = "operations@1.0.0"

OPERATIONS_CONFIG_VERSION: str = "operations-config@1.0.0"
OPERATIONS_ENVIRONMENT_VERSION: str = "operations-environment@1.0.0"
OPERATIONS_DEPLOYMENT_VERSION: str = "operations-deployment@1.0.0"
OPERATIONS_HEALTH_VERSION: str = "operations-health@1.0.0"
OPERATIONS_LOGGING_VERSION: str = "operations-logging@1.0.0"
OPERATIONS_MONITORING_VERSION: str = "operations-monitoring@1.0.0"
OPERATIONS_BACKUP_VERSION: str = "operations-backup@1.0.0"
OPERATIONS_RECOVERY_VERSION: str = "operations-recovery@1.0.0"
OPERATIONS_CI_VERSION: str = "operations-ci@1.0.0"
OPERATIONS_VALIDATION_VERSION: str = "operations-validation@1.0.0"
OPERATIONS_REPORT_VERSION: str = "operations-report@1.0.0"

# Deterministic default timestamp — no wall-clock enters a reproducible artifact.
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
