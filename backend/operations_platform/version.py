"""Version identities for the Operations Platform subsystem (Track 4).

Track 4 turns the usable product (Track 3) into a **deployable product**: it qualifies
operations — health monitoring, operational monitoring, diagnostics, deployment
qualification, and operational readiness (NOT_READY / PARTIALLY_READY /
READY_FOR_DEPLOYMENT) — over the **real** application platform.

It REUSES the Track-3 ``application_platform`` (the product it observes), the shared
``ml.lineage`` tracker, the shared ``ImmutableAuditLog``, ``ml.validation`` and
``ml.provenance``. It qualifies operations; it alters no business logic — it retrains no
models and modifies no datasets, Track 1/2/3 workflows, prediction logic, or security.
"""

from __future__ import annotations

OPERATIONS_PLATFORM_VERSION: str = "operations-platform@1.0.0"

OPS_DOMAIN_VERSION: str = "ops-domain@1.0.0"
OPS_IDENTITY_VERSION: str = "ops-identity@1.0.0"
OPS_HEALTH_VERSION: str = "ops-health@1.0.0"
OPS_MONITORING_VERSION: str = "ops-monitoring@1.0.0"
OPS_DIAGNOSTICS_VERSION: str = "ops-diagnostics@1.0.0"
OPS_QUALIFICATION_VERSION: str = "ops-qualification@1.0.0"
OPS_READINESS_VERSION: str = "ops-readiness@1.0.0"
OPS_REGISTRY_VERSION: str = "ops-registry@1.0.0"
OPS_AUDIT_VERSION: str = "ops-audit@1.0.0"
OPS_LINEAGE_VERSION: str = "ops-lineage@1.0.0"
OPS_REPORT_VERSION: str = "ops-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
FINGERPRINT_DECIMALS: int = 9
