"""``backend/operations_platform`` — Operational Readiness & Deployment Qualification (Track 4).

Turns the usable product (Track 3) into a **deployable product**: it qualifies operations —
health monitoring, operational monitoring, diagnostics, deployment qualification, and
operational readiness (NOT_READY / PARTIALLY_READY / READY_FOR_DEPLOYMENT) — over the **real**
``application_platform`` it observes.

It REUSES the Track-3 ``ApplicationPlatformService`` (read-only), the shared ``ml.lineage``
tracker, the shared ``ImmutableAuditLog``, ``ml.validation`` and ``ml.provenance``. It
qualifies operations; it alters no business logic — it retrains no models and modifies no
datasets, Track 1/2/3 workflows, prediction logic, or security. Boundary: imports ``ml`` +
sibling ``backend`` only; never ``frontend``.
"""

from __future__ import annotations

from .version import (
    OPERATIONS_PLATFORM_VERSION, OPS_AUDIT_VERSION, OPS_DIAGNOSTICS_VERSION, OPS_DOMAIN_VERSION,
    OPS_HEALTH_VERSION, OPS_IDENTITY_VERSION, OPS_LINEAGE_VERSION, OPS_MONITORING_VERSION,
    OPS_QUALIFICATION_VERSION, OPS_READINESS_VERSION, OPS_REGISTRY_VERSION, OPS_REPORT_VERSION,
    DETERMINISTIC_EPOCH, FINGERPRINT_DECIMALS,
)
from .models import (
    ComponentHealthRecord, DeploymentReadinessClass, DeploymentReadinessRecord, DiagnosticDomain,
    DiagnosticFinding, DiagnosticRecord, EntityKind, HealthCheckRecord, HealthComponent,
    HealthState, MetricName, MetricsSnapshotRecord, OperationsAuditRecord,
    OperationsRegistryRecord, QualificationFinding, QualificationRecord, QualificationStatus,
    QualificationTarget, ReadinessDimension, RootCause, Severity,
)
from .identity import mint
from .health import HealthEngine
from .monitoring import MonitoringEngine
from .diagnostics import DiagnosticEngine
from .qualification import QualificationEngine
from .readiness import DeploymentReadinessEngine
from .registry import OperationsRegistry, RegistryError
from .audit import AuditError, ImmutableAuditLog, make_operations_audit_log
from .schemas import ENTITY_CONTRACTS, validate_entity
from .service import OperationsPlatformError, OperationsPlatformService, QualificationOutcome

__all__ = [
    # versions
    "OPERATIONS_PLATFORM_VERSION", "OPS_DOMAIN_VERSION", "OPS_IDENTITY_VERSION", "OPS_HEALTH_VERSION",
    "OPS_MONITORING_VERSION", "OPS_DIAGNOSTICS_VERSION", "OPS_QUALIFICATION_VERSION",
    "OPS_READINESS_VERSION", "OPS_REGISTRY_VERSION", "OPS_AUDIT_VERSION", "OPS_LINEAGE_VERSION",
    "OPS_REPORT_VERSION", "DETERMINISTIC_EPOCH", "FINGERPRINT_DECIMALS",
    # domain
    "ComponentHealthRecord", "DeploymentReadinessClass", "DeploymentReadinessRecord",
    "DiagnosticDomain", "DiagnosticFinding", "DiagnosticRecord", "EntityKind", "HealthCheckRecord",
    "HealthComponent", "HealthState", "MetricName", "MetricsSnapshotRecord", "OperationsAuditRecord",
    "OperationsRegistryRecord", "QualificationFinding", "QualificationRecord", "QualificationStatus",
    "QualificationTarget", "ReadinessDimension", "RootCause", "Severity",
    # engines / infra
    "mint", "HealthEngine", "MonitoringEngine", "DiagnosticEngine", "QualificationEngine",
    "DeploymentReadinessEngine", "OperationsRegistry", "RegistryError", "AuditError",
    "ImmutableAuditLog", "make_operations_audit_log", "ENTITY_CONTRACTS", "validate_entity",
    "OperationsPlatformError", "OperationsPlatformService", "QualificationOutcome",
]
