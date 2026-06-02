"""``OperationsPlatformService`` — the Operational Qualification hub (Track 4).

Qualifies the **real** Track-3 ``ApplicationPlatformService`` for deployment by REUSING it
(observing it read-only) plus the shared ``ml.lineage`` tracker + the shared
``ImmutableAuditLog``. It runs: health check -> monitoring snapshot -> diagnostics ->
deployment qualification -> deployment readiness (NOT_READY / PARTIALLY_READY /
READY_FOR_DEPLOYMENT), recording an operational lineage chain and an immutable audit.

It qualifies operations; it alters no business logic — it retrains no models and modifies no
datasets, Track 1/2/3 workflows, prediction logic, or security.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ml.lineage import LineageTracker

from . import reports as _reports
from .audit import ImmutableAuditLog, make_operations_audit_log
from .diagnostics import DiagnosticEngine
from .health import HealthEngine
from .lineage import (
    make_diagnostic_lineage, make_health_lineage, make_metrics_lineage,
    make_qualification_lineage, make_readiness_lineage,
)
from .models.domain import (
    DeploymentReadinessClass, EntityKind, OperationsRegistryRecord,
)
from .monitoring import MonitoringEngine
from .qualification import QualificationEngine
from .readiness import DeploymentReadinessEngine
from .registry import OperationsRegistry
from .version import OPERATIONS_PLATFORM_VERSION, DETERMINISTIC_EPOCH


class OperationsPlatformError(RuntimeError):
    """Raised on hub misuse."""


@dataclass
class QualificationOutcome:
    health: object
    metrics: object
    diagnostic: object
    qualification: object
    readiness: object
    health_lineage_id: Optional[str] = None
    qualification_lineage_id: Optional[str] = None
    readiness_lineage_id: Optional[str] = None
    audit_head: Optional[str] = None

    @property
    def ready_for_deployment(self) -> bool:
        return self.readiness.classification == DeploymentReadinessClass.READY_FOR_DEPLOYMENT

    def to_dict(self) -> dict:
        return {"health": self.health.to_dict(), "metrics": self.metrics.to_dict(),
                "diagnostic": self.diagnostic.to_dict(),
                "qualification": self.qualification.to_dict(),
                "readiness": self.readiness.to_dict(),
                "health_lineage_id": self.health_lineage_id,
                "qualification_lineage_id": self.qualification_lineage_id,
                "readiness_lineage_id": self.readiness_lineage_id,
                "audit_head": self.audit_head,
                "ready_for_deployment": self.ready_for_deployment}


class OperationsPlatformService:
    """Observes + qualifies a Track-3 product for deployment (reuses everything)."""

    def __init__(self, product, *, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[OperationsRegistry] = None) -> None:
        self.product = product
        # share the product's lineage tracker so the operational chain attaches to the
        # product's workflow lineage (Dataset -> ... -> Workflow -> Health -> Qualification).
        self.lineage = lineage_tracker or getattr(product, "lineage", None) or LineageTracker()
        self.registry = registry or OperationsRegistry()
        self.health_engine = HealthEngine()
        self.monitoring_engine = MonitoringEngine()
        self.diagnostic_engine = DiagnosticEngine()
        self.qualification_engine = QualificationEngine()
        self.readiness_engine = DeploymentReadinessEngine()
        self.audit = make_operations_audit_log()
        self._outcome: Optional[QualificationOutcome] = None

    @property
    def version(self) -> str:
        return OPERATIONS_PLATFORM_VERSION

    def audit_log(self) -> ImmutableAuditLog:
        return self.audit

    def _product_workflow_nodes(self) -> list:
        """Lineage nodes of the product's completed workflows (the observed subjects)."""
        nodes = []
        for a in (getattr(self.product, "_analyses", {}) or {}).values():
            node = getattr(getattr(a, "report_record", None), "lineage_id", None) \
                or getattr(a, "lineage_id", None)
            if node and self.lineage.exists(node):
                nodes.append(node)
        return nodes

    # =========================================================================
    # T4-B..G: the full operational qualification
    # =========================================================================
    def qualify(self, *, created_at: str = DETERMINISTIC_EPOCH) -> QualificationOutcome:
        # --- T4-B health ---
        health = self.health_engine.check(self.product, created_at=created_at)
        wf_nodes = self._product_workflow_nodes()
        health_node = self.lineage.record(make_health_lineage(
            health.health_check_id, parents=wf_nodes, overall=health.overall.value,
            created_at=created_at))
        self.audit.append("health_checked", {"health_check_id": health.health_check_id,
                                             "overall": health.overall.value}, created_at=created_at)

        # --- T4-C monitoring ---
        metrics = self.monitoring_engine.snapshot(self.product, created_at=created_at)
        metrics_node = self.lineage.record(make_metrics_lineage(
            metrics.metrics_snapshot_id, parents=[health_node.lineage_id], created_at=created_at))
        self.audit.append("metrics_collected",
                          {"metrics_snapshot_id": metrics.metrics_snapshot_id,
                           "metrics": metrics.deterministic_metrics}, created_at=created_at)

        # --- T4-D diagnostics ---
        diagnostic = self.diagnostic_engine.diagnose(self.product, created_at=created_at)
        diag_node = self.lineage.record(make_diagnostic_lineage(
            diagnostic.diagnostic_id, parents=[health_node.lineage_id], created_at=created_at))
        self.audit.append("diagnostics_run", {"diagnostic_id": diagnostic.diagnostic_id,
                                             "ok": diagnostic.ok,
                                             "root_causes": list(diagnostic.root_causes)},
                          created_at=created_at)

        # --- T4-E deployment qualification ---
        qualification = self.qualification_engine.qualify(self.product, created_at=created_at)
        qual_node = self.lineage.record(make_qualification_lineage(
            qualification.qualification_id, health_node.lineage_id,
            status=qualification.status.value, created_at=created_at))
        self.audit.append("deployment_qualified",
                          {"qualification_id": qualification.qualification_id,
                           "status": qualification.status.value,
                           "available": f"{qualification.n_available}/{qualification.n_targets}"},
                          created_at=created_at)

        # --- T4-F deployment readiness ---
        traceable = self.lineage.verify_chain(qual_node.lineage_id)
        readiness = self.readiness_engine.assess(
            health=health, metrics=metrics, diagnostic=diagnostic, qualification=qualification,
            registered=True, audited=self.audit.verify(), traceable=traceable,
            created_at=created_at)
        read_node = self.lineage.record(make_readiness_lineage(
            readiness.readiness_id, qual_node.lineage_id,
            classification=readiness.classification.value, created_at=created_at))
        self.audit.append("readiness_scored", {"readiness_id": readiness.readiness_id,
                                             "classification": readiness.classification.value,
                                             "score": readiness.score}, created_at=created_at)

        # --- T4-G registry (no orphans) ---
        self._register(EntityKind.HEALTH_CHECK, health.health_check_id, health.signature(),
                       health_node.lineage_id, created_at)
        self._register(EntityKind.METRICS_SNAPSHOT, metrics.metrics_snapshot_id,
                       metrics.signature(), metrics_node.lineage_id, created_at,
                       deps=(health.health_check_id,))
        self._register(EntityKind.DIAGNOSTIC, diagnostic.diagnostic_id, diagnostic.signature(),
                       diag_node.lineage_id, created_at, deps=(health.health_check_id,))
        self._register(EntityKind.QUALIFICATION, qualification.qualification_id,
                       qualification.signature(), qual_node.lineage_id, created_at,
                       deps=(health.health_check_id,))
        self._register(EntityKind.READINESS, readiness.readiness_id, readiness.readiness_id,
                       read_node.lineage_id, created_at, deps=(qualification.qualification_id,))

        outcome = QualificationOutcome(
            health=health, metrics=metrics, diagnostic=diagnostic, qualification=qualification,
            readiness=readiness, health_lineage_id=health_node.lineage_id,
            qualification_lineage_id=qual_node.lineage_id,
            readiness_lineage_id=read_node.lineage_id, audit_head=self.audit.head)
        self._outcome = outcome
        return outcome

    # =========================================================================
    # T4-H reporting
    # =========================================================================
    def reports(self, outcome: Optional[QualificationOutcome] = None) -> dict:
        outcome = outcome or self._outcome
        if outcome is None:
            raise OperationsPlatformError("no qualification run yet; call qualify() first")
        return {
            "health_report": _reports.build_health_report(outcome.health),
            "monitoring_report": _reports.build_monitoring_report(outcome.metrics),
            "diagnostics_report": _reports.build_diagnostics_report(outcome.diagnostic),
            "qualification_report": _reports.build_qualification_report(outcome.qualification),
            "readiness_report": _reports.build_readiness_report(outcome.readiness),
            "audit_report": _reports.build_audit_report(self.audit, subject="operations"),
            "lineage_report": _reports.build_lineage_report(self.lineage,
                                                            outcome.readiness_lineage_id),
            "operational_summary_report": _reports.build_operational_summary_report(
                health=outcome.health, metrics=outcome.metrics, diagnostic=outcome.diagnostic,
                qualification=outcome.qualification, readiness=outcome.readiness),
        }

    # =========================================================================
    # internals
    # =========================================================================
    def _register(self, kind, entity_id, version, lineage_id, created_at, *, deps=()) -> None:
        self.registry.register(OperationsRegistryRecord(
            entity_kind=kind, entity_id=entity_id, status="active", version=str(version),
            owner="operations-ops", creation_date=created_at, audit_state=self.audit.head,
            lineage_id=lineage_id, dependencies=tuple(deps)))


__all__ = ["OperationsPlatformService", "QualificationOutcome", "OperationsPlatformError"]
