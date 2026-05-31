"""Operations Platform domain entities + closed vocabularies (Track 4, T4-A/B).

Pure, JSON-able, content-hashable records describing **operational qualification**: health
statuses, operational metrics, diagnostic findings, deployment-qualification findings, and
operational readiness — plus the registry/audit/lineage projections. No I/O and no
orchestration here — only the shapes and the closed vocabularies (NR-6).

Determinism (NR-9/NR-10): every ``signature()`` / content id is a function of the
deterministic fields only. Wall-clock latency / processing-time / resource measures are
carried as **informational** fields and excluded from every signature.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    FINGERPRINT_DECIMALS, OPS_DIAGNOSTICS_VERSION, OPS_HEALTH_VERSION,
    OPS_MONITORING_VERSION, OPS_QUALIFICATION_VERSION, OPS_READINESS_VERSION, OPS_REGISTRY_VERSION,
    DETERMINISTIC_EPOCH,
)


def _q(x: float) -> float:
    return round(float(x), FINGERPRINT_DECIMALS)


def _qmap(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        out[k] = _q(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
    return dict(sorted(out.items()))


# =============================================================================
# Closed vocabularies
# =============================================================================
class HealthState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"

    @property
    def rank(self) -> int:
        return {"HEALTHY": 2, "DEGRADED": 1, "UNHEALTHY": 0}[self.value]


class HealthComponent(str, Enum):
    SERVICE = "service"
    DATASET = "dataset"
    MODEL = "model"
    STORAGE = "storage"
    API = "api"
    WORKFLOW = "workflow"
    PREDICTION = "prediction"


class MetricName(str, Enum):
    REQUEST_VOLUME = "request_volume"
    PREDICTION_VOLUME = "prediction_volume"
    UPLOAD_VOLUME = "upload_volume"
    LATENCY = "latency"
    PROCESSING_TIME = "processing_time"
    FAILURES = "failures"
    VALIDATION_ERRORS = "validation_errors"
    RESOURCE_USAGE = "resource_usage"


class DiagnosticDomain(str, Enum):
    WORKFLOW = "workflow"
    PREDICTION = "prediction"
    UPLOAD = "upload"
    API = "api"
    FAILURE = "failure"


class RootCause(str, Enum):
    NONE = "none"
    MISSING_MODEL = "missing_model"
    MISSING_DATASET = "missing_dataset"
    INVALID_UPLOAD = "invalid_upload"
    CORRUPTED_STATE = "corrupted_state"
    API_ERROR = "api_error"
    WORKFLOW_INCOMPLETE = "workflow_incomplete"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def blocking(self) -> bool:
        return self in (Severity.ERROR, Severity.CRITICAL)


class QualificationTarget(str, Enum):
    DATASET = "dataset_availability"
    MODEL = "model_availability"
    API = "api_availability"
    WORKFLOW = "workflow_availability"
    REPORT = "report_availability"
    PERSISTENCE = "persistence_availability"
    SECURITY = "security_availability"


class QualificationStatus(str, Enum):
    QUALIFIED = "QUALIFIED"
    CONDITIONALLY_QUALIFIED = "CONDITIONALLY_QUALIFIED"
    NOT_QUALIFIED = "NOT_QUALIFIED"


class DeploymentReadinessClass(str, Enum):
    NOT_READY = "NOT_READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    READY_FOR_DEPLOYMENT = "READY_FOR_DEPLOYMENT"


class ReadinessDimension(str, Enum):
    OPERATIONAL = "operational_readiness"
    MONITORING = "monitoring_readiness"
    HEALTH = "health_readiness"
    QUALIFICATION = "qualification_readiness"
    REGISTRY = "registry_readiness"
    AUDIT = "audit_readiness"
    LINEAGE = "lineage_readiness"


class EntityKind(str, Enum):
    HEALTH_CHECK = "ops_health_check"
    METRICS_SNAPSHOT = "ops_metrics_snapshot"
    DIAGNOSTIC = "ops_diagnostic"
    QUALIFICATION = "ops_qualification"
    READINESS = "ops_readiness"


# =============================================================================
# T4-B — health
# =============================================================================
@dataclass(frozen=True)
class ComponentHealthRecord:
    component: HealthComponent
    state: HealthState
    detail: str = ""

    def to_dict(self) -> dict:
        return {"component": self.component.value, "state": self.state.value,
                "detail": self.detail}


@dataclass(frozen=True)
class HealthCheckRecord:
    health_check_id: str
    overall: HealthState
    components: tuple                         # (ComponentHealthRecord, ...)
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    health_version: str = OPS_HEALTH_VERSION

    @property
    def n_components(self) -> int:
        return len(self.components)

    def signature(self) -> str:
        return hash_obj({"overall": self.overall.value,
                         "components": [[c.component.value, c.state.value]
                                        for c in self.components]})

    def to_dict(self) -> dict:
        return {"health_check_id": self.health_check_id, "overall": self.overall.value,
                "n_components": self.n_components,
                "components": [c.to_dict() for c in self.components],
                "created_at": self.created_at, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state, "health_version": self.health_version,
                "signature": self.signature()}


# =============================================================================
# T4-C — monitoring
# =============================================================================
@dataclass(frozen=True)
class MetricsSnapshotRecord:
    metrics_snapshot_id: str
    deterministic_metrics: dict               # counts: request/prediction/upload/failures/...
    informational_metrics: dict               # latency / processing time / resource (not hashed)
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    monitoring_version: str = OPS_MONITORING_VERSION

    def signature(self) -> str:
        return hash_obj({"deterministic_metrics": _qmap(self.deterministic_metrics)})

    def to_dict(self) -> dict:
        return {"metrics_snapshot_id": self.metrics_snapshot_id,
                "deterministic_metrics": _qmap(self.deterministic_metrics),
                "informational_metrics": _qmap(self.informational_metrics),
                "created_at": self.created_at, "lineage_id": self.lineage_id,
                "monitoring_version": self.monitoring_version, "signature": self.signature()}


# =============================================================================
# T4-D — diagnostics
# =============================================================================
@dataclass(frozen=True)
class DiagnosticFinding:
    domain: DiagnosticDomain
    severity: Severity
    passed: bool
    root_cause: RootCause
    detail: str = ""

    def to_dict(self) -> dict:
        return {"domain": self.domain.value, "severity": self.severity.value,
                "passed": self.passed, "root_cause": self.root_cause.value, "detail": self.detail}


@dataclass(frozen=True)
class DiagnosticRecord:
    diagnostic_id: str
    ok: bool
    findings: tuple                           # (DiagnosticFinding, ...)
    root_causes: tuple
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    diagnostics_version: str = OPS_DIAGNOSTICS_VERSION

    @property
    def n_findings(self) -> int:
        return len(self.findings)

    def signature(self) -> str:
        return hash_obj({"ok": self.ok,
                         "findings": [[f.domain.value, f.severity.value, f.passed,
                                       f.root_cause.value] for f in self.findings]})

    def to_dict(self) -> dict:
        return {"diagnostic_id": self.diagnostic_id, "ok": self.ok, "n_findings": self.n_findings,
                "findings": [f.to_dict() for f in self.findings],
                "root_causes": list(self.root_causes), "created_at": self.created_at,
                "lineage_id": self.lineage_id, "diagnostics_version": self.diagnostics_version,
                "signature": self.signature()}


# =============================================================================
# T4-E — deployment qualification
# =============================================================================
@dataclass(frozen=True)
class QualificationFinding:
    target: QualificationTarget
    available: bool
    severity: Severity
    detail: str = ""

    def to_dict(self) -> dict:
        return {"target": self.target.value, "available": self.available,
                "severity": self.severity.value, "detail": self.detail}


@dataclass(frozen=True)
class QualificationRecord:
    qualification_id: str
    status: QualificationStatus
    findings: tuple                           # (QualificationFinding, ...)
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    qualification_version: str = OPS_QUALIFICATION_VERSION

    @property
    def n_available(self) -> int:
        return sum(1 for f in self.findings if f.available)

    @property
    def n_targets(self) -> int:
        return len(self.findings)

    def signature(self) -> str:
        return hash_obj({"status": self.status.value,
                         "findings": [[f.target.value, f.available] for f in self.findings]})

    def to_dict(self) -> dict:
        return {"qualification_id": self.qualification_id, "status": self.status.value,
                "n_available": self.n_available, "n_targets": self.n_targets,
                "findings": [f.to_dict() for f in self.findings], "created_at": self.created_at,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "qualification_version": self.qualification_version, "signature": self.signature()}


# =============================================================================
# T4-F — deployment readiness
# =============================================================================
@dataclass(frozen=True)
class DeploymentReadinessRecord:
    readiness_id: str
    score: float
    classification: DeploymentReadinessClass
    dimensions: dict
    findings: tuple
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    readiness_version: str = OPS_READINESS_VERSION

    def to_dict(self) -> dict:
        return {"readiness_id": self.readiness_id, "score": _q(self.score),
                "classification": self.classification.value,
                "dimensions": dict(sorted(self.dimensions.items())), "findings": list(self.findings),
                "created_at": self.created_at, "lineage_id": self.lineage_id,
                "readiness_version": self.readiness_version}


# =============================================================================
# Registry / audit / lineage projections
# =============================================================================
@dataclass
class OperationsRegistryRecord:
    entity_kind: EntityKind
    entity_id: str
    status: str
    version: str
    owner: str
    creation_date: str
    audit_state: str
    lineage_id: str
    dependencies: tuple = ()
    registry_version: str = OPS_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"entity_kind": self.entity_kind.value, "entity_id": self.entity_id,
                         "status": self.status, "version": self.version,
                         "lineage_id": self.lineage_id, "audit_state": self.audit_state})

    def to_dict(self) -> dict:
        return {"entity_kind": self.entity_kind.value, "entity_id": self.entity_id,
                "status": self.status, "version": self.version, "owner": self.owner,
                "creation_date": self.creation_date, "audit_state": self.audit_state,
                "lineage_id": self.lineage_id, "dependencies": list(self.dependencies),
                "registry_version": self.registry_version,
                "content_signature": self.content_signature()}


@dataclass(frozen=True)
class OperationsAuditRecord:
    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload,
                "prev_hash": self.prev_hash, "event_hash": self.event_hash,
                "created_at": self.created_at}


__all__ = [
    "HealthState", "HealthComponent", "MetricName", "DiagnosticDomain", "RootCause", "Severity",
    "QualificationTarget", "QualificationStatus", "DeploymentReadinessClass", "ReadinessDimension",
    "EntityKind", "ComponentHealthRecord", "HealthCheckRecord", "MetricsSnapshotRecord",
    "DiagnosticFinding", "DiagnosticRecord", "QualificationFinding", "QualificationRecord",
    "DeploymentReadinessRecord", "OperationsRegistryRecord", "OperationsAuditRecord",
]
