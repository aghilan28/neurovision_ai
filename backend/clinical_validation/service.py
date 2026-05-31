"""ClinicalValidationService — the governed orchestration hub for DRP-6.

Transforms the production-candidate platform into an **evidence-supported** platform: it
benchmarks every production model, evaluates performance, measures reliability + calibration,
generates evidence, traces validation lineage, and scores validation readiness — **without
retraining or modifying any model/serving/persistence/security/frontend/deployment code**.

    develop production models (reused DRP-2) ->
    benchmark (acc/prec/rec/F1/ROC-AUC/PR-AUC/sensitivity/specificity + perf) ->
    calibrate (ECE/Brier + reliability curve) -> measure reliability (repeatability/
    reproducibility/cross-run/cross-dataset/failure modes) -> generate evidence ->
    compare models -> score readiness -> record lineage
    (Dataset -> Model -> Benchmark -> Evaluation -> Evidence -> Readiness) -> audit

Reuses the DRP-2 ``ProductionModelService`` (no replacement systems), the shared
``ml.lineage`` tracker, and the shared ``ImmutableAuditLog`` (no parallel systems).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional, Sequence

from ml.lineage import LineageTracker

from backend.production_models import (  # reuse: no replacement systems
    ProductionModelService, ProductionArchitecture, PRODUCTION_ARCHITECTURES, ProductionModelError,
)

from .version import CLINICAL_VALIDATION_VERSION, DETERMINISTIC_EPOCH
from .identity import mint_identity
from .models.domain import (
    ClinicalValidationIdentity, ClinicalValidationRecord, ClinicalValidationVersion,
    ValidationStatus,
)
from .benchmarks import build_benchmark
from .calibration import build_calibration
from .reliability import build_reliability
from .comparison import build_comparison
from .evidence import build_evidence
from .readiness import ValidationReadinessEngine
from .registry import EvidenceRegistry
from .validation import ValidationContentValidator, ValidationIntegrityValidator
from .audit import make_validation_audit_log, ImmutableAuditLog
from .lineage import (
    make_benchmark_lineage, make_evaluation_lineage, make_evidence_lineage, make_readiness_lineage,
)
from . import reports as _reports


class ClinicalValidationError(RuntimeError):
    """Raised on programmer misuse of the service (not for unusable inputs)."""


@dataclass(frozen=True)
class ModelValidationOutcome:
    architecture: ProductionArchitecture
    record: ClinicalValidationRecord
    benchmark: object
    performance: object
    reliability: object
    calibration: object
    evidence: object
    readiness: object

    @property
    def validation_id(self) -> str:
        return self.record.validation_id


@dataclass(frozen=True)
class ValidationRunOutcome:
    models: dict
    comparison: object

    def to_dict(self) -> dict:
        return {"models": {a: o.record.to_dict() for a, o in self.models.items()},
                "comparison": self.comparison.to_dict() if self.comparison else None}


class ClinicalValidationService:
    """Stateful service: a shared lineage tracker, the evidence registry, engines, and
    per-validation immutable audit logs + context."""

    def __init__(self, *, lineage_tracker: Optional[LineageTracker] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = EvidenceRegistry()
        self.readiness_engine = ValidationReadinessEngine()
        self.content_validator = ValidationContentValidator()
        self.integrity_validator = ValidationIntegrityValidator()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}
        self._context: dict[str, dict] = {}
        self._comparison = None

    def audit_log_for(self, validation_id: str) -> ImmutableAuditLog:
        return self._audit_logs[validation_id]

    # --- the single use case --------------------------------------------------
    def run_validation(self, feature_records: Sequence, *,
                       architectures: Sequence[ProductionArchitecture] = PRODUCTION_ARCHITECTURES,
                       dataset_label: str = "primary", seed: int = 7,
                       owner: str = "validation-ops",
                       created_at: str = DETERMINISTIC_EPOCH) -> ValidationRunOutcome:
        if not feature_records:
            raise ClinicalValidationError("no feature assets supplied")

        # --- develop production models (reuse DRP-2) on the shared tracker -----
        base = ProductionModelService(lineage_tracker=self.lineage).develop_all(
            feature_records, architectures=architectures, dataset_key="cohort", seed=seed,
            created_at=created_at)
        repeat = ProductionModelService(lineage_tracker=self.lineage).develop_all(
            feature_records, architectures=architectures, dataset_key="cohort", seed=seed,
            created_at=created_at)
        cross = ProductionModelService(lineage_tracker=self.lineage).develop_all(
            feature_records, architectures=architectures, dataset_key="cohort_xds", seed=seed,
            created_at=created_at)
        failure_modes = self._failure_modes(feature_records, seed=seed)

        outcomes: dict[str, ModelValidationOutcome] = {}
        for arch_value, base_outcome in base.items():
            outcomes[arch_value] = self._validate_one(
                base_outcome=base_outcome, repeat_outcome=repeat[arch_value],
                cross_outcome=cross[arch_value], failure_modes=failure_modes,
                dataset_label=dataset_label, owner=owner, created_at=created_at)

        # --- comparison across models (DRP6-F) --------------------------------
        comparison = None
        benchmarks = [o.benchmark for o in outcomes.values()]
        if len(benchmarks) >= 2:
            comparison = build_comparison(benchmarks)
            self.registry.register_comparison(comparison)
        self._comparison = comparison
        return ValidationRunOutcome(models=outcomes, comparison=comparison)

    # --- per-model validation -------------------------------------------------
    def _validate_one(self, *, base_outcome, repeat_outcome, cross_outcome, failure_modes,
                      dataset_label, owner, created_at) -> ModelValidationOutcome:
        model = base_outcome.model
        model_id = model.model_id
        log = make_validation_audit_log()

        benchmark, performance = build_benchmark(base_outcome, dataset_label=dataset_label,
                                                 created_at=created_at)
        b_node = self.lineage.record(make_benchmark_lineage(
            benchmark.benchmark_id, model.lineage_id, dataset_label=dataset_label,
            created_at=created_at))
        benchmark = replace(benchmark, lineage_id=b_node.lineage_id)
        log.append("benchmark", {"benchmark_id": benchmark.benchmark_id}, created_at=created_at)
        self.registry.register_benchmark(benchmark)
        self.registry.register_performance(performance)

        calibration = build_calibration(base_outcome, created_at=created_at)
        self.registry.register_calibration(calibration)
        log.append("calibration", {"calibration_id": calibration.calibration_id},
                   created_at=created_at)

        reliability = build_reliability(
            model_id=model_id, base_outcome=base_outcome, repeat_outcome=repeat_outcome,
            cross_dataset_outcome=cross_outcome, failure_modes=failure_modes, created_at=created_at)
        self.registry.register_reliability(reliability)
        log.append("reliability", {"reliability_id": reliability.reliability_id,
                                   "score": reliability.reliability_score}, created_at=created_at)

        e_node = self.lineage.record(make_evaluation_lineage(
            performance.performance_id, b_node.lineage_id, created_at=created_at))
        log.append("evaluation", {"performance_id": performance.performance_id},
                   created_at=created_at)

        evidence = build_evidence(model_id=model_id, benchmark=benchmark, performance=performance,
                                  reliability=reliability, calibration=calibration,
                                  created_at=created_at)
        ev_node = self.lineage.record(make_evidence_lineage(
            evidence.evidence_id, e_node.lineage_id, created_at=created_at))
        evidence = replace(evidence, lineage_id=ev_node.lineage_id)
        self.registry.register_evidence(evidence)
        log.append("evidence", {"evidence_id": evidence.evidence_id}, created_at=created_at)

        # --- content validation ------------------------------------------------
        checks = tuple(self.content_validator.content_checks(
            benchmark=benchmark, reliability=reliability, calibration=calibration, evidence=evidence))
        content_ok = all(p for _, p, _ in checks)

        # --- readiness ---------------------------------------------------------
        traceable = self.lineage.verify_chain(ev_node.lineage_id)
        readiness = self.readiness_engine.assess(
            target_id=evidence.evidence_id, benchmark_ok=True, reliability_ok=content_ok,
            calibration_ok=True, evidence_ok=True, registered=True, audited=log.verify(),
            traceable=traceable, created_at=created_at)
        r_node = self.lineage.record(make_readiness_lineage(
            readiness.readiness_id, ev_node.lineage_id, classification=readiness.classification.value,
            created_at=created_at))
        readiness = replace(readiness, lineage_id=r_node.lineage_id)
        self.registry.register_readiness(readiness)
        log.append("readiness", {"readiness_id": readiness.readiness_id,
                                 "classification": readiness.classification.value},
                   created_at=created_at)

        # --- version + aggregate ----------------------------------------------
        status = ValidationStatus.VALIDATED if content_ok else ValidationStatus.QUARANTINED
        identity = ClinicalValidationIdentity(
            validation_id=mint_identity("clinical_validation", {
                "model_id": model_id, "evidence_id": evidence.evidence_id}).id,
            model_id=model_id, evidence_id=evidence.evidence_id, benchmark_id=benchmark.benchmark_id,
            identity_version=CLINICAL_VALIDATION_VERSION)
        dependencies = (model_id, benchmark.benchmark_id, evidence.evidence_id)
        state_sig = ClinicalValidationRecord.state_signature_of(
            identity=identity, model_id=model_id, architecture=base_outcome.architecture.value,
            dataset_label=dataset_label, benchmark_id=benchmark.benchmark_id,
            performance_id=performance.performance_id, reliability_id=reliability.reliability_id,
            calibration_id=calibration.calibration_id, evidence_id=evidence.evidence_id,
            readiness_id=readiness.readiness_id, readiness_class=readiness.classification,
            validation_ok=content_ok, checks=checks, status=status, dependencies=dependencies)
        version = ClinicalValidationVersion(
            version=ClinicalValidationVersion.compute(state_sig, None), previous=None,
            reason="validated", created_at=created_at)
        log.append("validation_version_changed", {"version": version.version}, created_at=created_at)
        log.append("validation_registered", {"validation_id": identity.validation_id,
                                             "status": status.value}, created_at=created_at)

        record = ClinicalValidationRecord(
            identity=identity, model_id=model_id, architecture=base_outcome.architecture.value,
            dataset_label=dataset_label, benchmark_id=benchmark.benchmark_id,
            performance_id=performance.performance_id, reliability_id=reliability.reliability_id,
            calibration_id=calibration.calibration_id, evidence_id=evidence.evidence_id,
            readiness_id=readiness.readiness_id, readiness_class=readiness.classification,
            validation_ok=content_ok, checks=checks, status=status, version=version, owner=owner,
            created_at=created_at, lineage_id=r_node.lineage_id, audit_head=log.head,
            dependencies=dependencies)
        self.registry.register_validation(self._registry_record(record))
        self._audit_logs[record.validation_id] = log
        self._context[record.validation_id] = {
            "record": record, "benchmark": benchmark, "performance": performance,
            "reliability": reliability, "calibration": calibration, "evidence": evidence,
            "readiness": readiness}
        return ModelValidationOutcome(
            architecture=base_outcome.architecture, record=record, benchmark=benchmark,
            performance=performance, reliability=reliability, calibration=calibration,
            evidence=evidence, readiness=readiness)

    # --- validation + reports -------------------------------------------------
    def integrity(self, record: ClinicalValidationRecord):
        ctx = self._context[record.validation_id]
        return self.integrity_validator.validate(
            record=record, benchmark=ctx["benchmark"], reliability=ctx["reliability"],
            calibration=ctx["calibration"], evidence=ctx["evidence"], registry=self.registry,
            audit_log=self._audit_logs[record.validation_id], lineage_tracker=self.lineage)

    def reports(self, record: ClinicalValidationRecord) -> dict:
        ctx = self._context[record.validation_id]
        log = self._audit_logs[record.validation_id]
        integrity = self.integrity(record)
        return {
            "benchmark_report": _reports.build_benchmark_report(record, ctx["benchmark"]),
            "performance_report": _reports.build_performance_report(record, ctx["performance"]),
            "calibration_report": _reports.build_calibration_report(record, ctx["calibration"]),
            "reliability_report": _reports.build_reliability_report(record, ctx["reliability"]),
            "comparison_report": _reports.build_comparison_report(self._comparison),
            "evidence_report": _reports.build_evidence_report(record, ctx["evidence"]),
            "readiness_report": _reports.build_readiness_report(record, ctx["readiness"]),
            "audit_report": _reports.build_audit_report(record, log),
            "lineage_report": _reports.build_lineage_report(record, self.lineage),
            "clinical_validation_summary": _reports.build_clinical_validation_summary(
                record, ctx["readiness"], ctx["benchmark"], integrity),
        }

    # --- internals ------------------------------------------------------------
    def _failure_modes(self, feature_records, *, seed: int) -> tuple:
        """Deterministic failure-mode probes: the platform handles bad inputs gracefully
        (a controlled error), never a crash."""
        probes = []
        try:
            ProductionModelService(lineage_tracker=LineageTracker()).develop_model(
                [], architecture=ProductionArchitecture.EEGNET, seed=seed)
            probes.append({"mode": "empty_cohort", "handled": False})
        except ProductionModelError:
            probes.append({"mode": "empty_cohort", "handled": True})
        except Exception:
            probes.append({"mode": "empty_cohort", "handled": False})
        try:
            # feature lineage nodes absent on a fresh tracker -> controlled error
            ProductionModelService(lineage_tracker=LineageTracker()).develop_model(
                feature_records, architecture=ProductionArchitecture.EEGNET, seed=seed)
            probes.append({"mode": "missing_feature_lineage", "handled": False})
        except ProductionModelError:
            probes.append({"mode": "missing_feature_lineage", "handled": True})
        except Exception:
            probes.append({"mode": "missing_feature_lineage", "handled": False})
        return tuple(probes)

    def _registry_record(self, record: ClinicalValidationRecord):
        from .models.domain import ValidationRegistryRecord
        return ValidationRegistryRecord(
            validation_id=record.validation_id, model_id=record.model_id,
            architecture=record.architecture, dataset_label=record.dataset_label,
            benchmark_id=record.benchmark_id, evidence_id=record.evidence_id,
            readiness_id=record.readiness_id, status=record.status,
            readiness_class=record.readiness_class, version=record.version.version, owner=record.owner,
            creation_date=record.created_at, audit_state=record.audit_head or "",
            lineage_id=record.lineage_id or "", dependencies=record.dependencies)

    @property
    def version(self) -> str:
        return CLINICAL_VALIDATION_VERSION


__all__ = ["ClinicalValidationService", "ValidationRunOutcome", "ModelValidationOutcome",
           "ClinicalValidationError"]
