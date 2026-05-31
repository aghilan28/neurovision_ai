"""ProductionModelService — the governed orchestration hub for DRP-2.

Transforms feature assets (Productization P3) + the platform's reference architectures
into **production-candidate models with benchmark + readiness evidence**, without touching
upstream assets or any other subsystem. The flow per architecture is:

    build a patient-disjoint dataset from feature assets (reused) -> register dataset
    (shared registry) -> train (deterministic, reproducibility verified) -> track training
    experiment -> evaluate (reused base evaluator) + extended analyses -> benchmark
    (deterministic metrics + informational timings) -> mint model id -> register the model
    (shared model registry) -> score readiness -> validate -> version -> register the
    production candidate -> append immutable audit events -> record lineage
    (Dataset -> Feature -> Training Run -> Experiment -> Model -> Benchmark -> Readiness)

Every step is audited; nothing is registered outside this governed path. It shares the
platform's single ``ml.lineage.LineageTracker`` (so readiness traces to the patient) and
the shared ``ImmutableAuditLog`` (no parallel systems), reuses the model-foundation
dataset / evaluation building blocks + the shared ``DatasetRegistry`` + ``ModelRegistry``
(no parallel registries), and performs **no inference serving, no APIs, no deployment**
(forbidden in this phase).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional, Sequence

from ml.lineage import LineageTracker

from backend.model_foundation import (
    DatasetRegistry, ModelRegistry, SplitName, build_feature_dataset, evaluate as foundation_evaluate,
)
from backend.model_foundation import ModelRegistryRecord as FoundationModelRegistryRecord
from backend.model_foundation import ModelStatus as FoundationModelStatus

from .version import PRODUCTION_MODELS_VERSION, DEFAULT_SEED, DETERMINISTIC_EPOCH
from .identity import mint_identity
from .models.domain import (
    ModelStatus, ModelValidationRecord, ModelVersion, ProductionArchitecture,
    ProductionModelIdentity, ProductionModelRecord, ModelRegistryRecord,
)
from .architectures import PRODUCTION_ARCHITECTURES
from .training import TrainingConfig, train_production
from .benchmarking import benchmark_model
from .evaluation import build_model_evaluation, compare_models
from .readiness import ReadinessEngine
from .validation import ProductionModelContentValidator, ProductionModelIntegrityValidator
from .registry import ProductionModelRegistry
from .audit import make_production_audit_log, ImmutableAuditLog
from .lineage import (
    make_dataset_lineage, make_training_lineage, make_evaluation_lineage,
    make_training_experiment_lineage, make_production_model_lineage, make_benchmark_lineage,
    make_readiness_lineage,
)
from . import reports as _reports

from ml.provenance import content_id


class ProductionModelError(RuntimeError):
    """Raised on programmer misuse of the service (not for unusable inputs)."""


@dataclass(frozen=True)
class ProductionModelOutcome:
    """The result of developing a production-candidate model from feature assets."""

    accepted: bool
    reason: str
    architecture: ProductionArchitecture
    model: Optional[ProductionModelRecord] = None
    benchmark: object = None
    evaluation: object = None
    readiness: object = None
    experiment: object = None
    base_evaluation: object = None
    dataset_id: Optional[str] = None

    @property
    def model_id(self) -> Optional[str]:
        return self.model.model_id if self.model else None

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted, "reason": self.reason,
            "architecture": self.architecture.value,
            "model_id": self.model_id, "dataset_id": self.dataset_id,
            "model": self.model.to_dict() if self.model else None,
            "benchmark": self.benchmark.to_dict() if self.benchmark else None,
            "evaluation": self.evaluation.to_dict() if self.evaluation else None,
            "readiness": self.readiness.to_dict() if self.readiness else None,
        }


class ProductionModelService:
    """Stateful service: a shared lineage tracker, the shared dataset + model registries,
    the production registry, and per-model immutable audit logs + record context."""

    def __init__(self, *, lineage_tracker: Optional[LineageTracker] = None,
                 dataset_registry: Optional[DatasetRegistry] = None,
                 model_registry: Optional[ModelRegistry] = None,
                 production_registry: Optional[ProductionModelRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.dataset_registry = dataset_registry or DatasetRegistry()
        self.model_registry = model_registry or ModelRegistry()
        self.production_registry = production_registry or ProductionModelRegistry()
        self.content_validator = ProductionModelContentValidator()
        self.integrity_validator = ProductionModelIntegrityValidator()
        self.readiness_engine = ReadinessEngine()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}
        self._context: dict[str, dict] = {}

    def audit_log_for(self, model_id: str) -> ImmutableAuditLog:
        return self._audit_logs[model_id]

    # --- the single use case --------------------------------------------------
    def develop_model(self, feature_records: Sequence, *, architecture: ProductionArchitecture,
                      dataset_key: str = "default", seed: int = DEFAULT_SEED,
                      hyperparameters: Optional[dict] = None, labels: Optional[dict] = None,
                      n_classes: int = 2, val_fraction: float = 0.2, test_fraction: float = 0.2,
                      owner: str = "model-ops",
                      created_at: str = DETERMINISTIC_EPOCH) -> ProductionModelOutcome:
        """Develop, benchmark, evaluate, and score-readiness for one production model."""
        if not feature_records:
            raise ProductionModelError("no feature assets supplied")
        feature_lineage_ids = []
        for rec in feature_records:
            if not (rec.lineage_id and self.lineage.exists(rec.lineage_id)):
                raise ProductionModelError(
                    "feature lineage node not present in the shared tracker; develop with a shared "
                    "LineageTracker (Patient -> ... -> Feature -> Dataset -> ... -> Readiness)")
            feature_lineage_ids.append(rec.lineage_id)
        feature_lineage_ids = tuple(feature_lineage_ids)

        # --- build + register the patient-disjoint dataset (reuse) ------------
        bundle = build_feature_dataset(
            feature_records, name=f"feature_dataset[{dataset_key}]", dataset_key=dataset_key,
            labels=labels, n_classes=n_classes, val_fraction=val_fraction,
            test_fraction=test_fraction, seed=seed)
        ds_node = self.lineage.record(make_dataset_lineage(
            bundle.record.dataset_id, feature_lineage_ids, source=bundle.record.source.value,
            n_samples=bundle.record.n_samples, data_fingerprint=bundle.record.data_fingerprint,
            created_at=created_at))
        log = make_production_audit_log()
        log.append("dataset_registered", {
            "dataset_id": bundle.record.dataset_id, "source": bundle.record.source.value,
            "n_samples": bundle.record.n_samples, "n_features": bundle.record.n_features,
            "patient_disjoint": bundle.record.split.patient_disjoint}, created_at=created_at)
        dataset_record = replace(bundle.record, lineage_id=ds_node.lineage_id, audit_state=log.head)
        bundle = replace(bundle, record=dataset_record)
        if not self.dataset_registry.exists(dataset_record.dataset_id):
            self.dataset_registry.register(dataset_record)

        # --- train (deterministic; reproducibility verified) ------------------
        config = TrainingConfig(architecture=architecture, seed=seed, n_classes=n_classes,
                                val_fraction=val_fraction, test_fraction=test_fraction,
                                hyperparameters=hyperparameters or {})
        tr = train_production(config, bundle, created_at=created_at)
        tr_node = self.lineage.record(make_training_lineage(
            tr.training_run_id, ds_node.lineage_id, architecture=architecture.value,
            params_fingerprint=tr.params_fingerprint, created_at=created_at))
        exp_node = self.lineage.record(make_training_experiment_lineage(
            tr.record.experiment_id, tr_node.lineage_id, architecture=architecture.value,
            created_at=created_at))
        experiment = replace(tr.record, lineage_id=exp_node.lineage_id, audit_state=log.head)
        log.append("training_completed", {
            "experiment_id": experiment.experiment_id, "training_run_id": tr.training_run_id,
            "architecture": architecture.value, "seed": seed, "reproducible": tr.reproducible,
            "params_fingerprint": tr.params_fingerprint}, created_at=created_at)

        # --- base evaluation (reuse the model-foundation evaluator) -----------
        base_eval = foundation_evaluate(tr.model, bundle, training_run_id=tr.training_run_id,
                                        n_classes=n_classes, split=SplitName.TEST,
                                        created_at=created_at)
        ev_node = self.lineage.record(make_evaluation_lineage(
            base_eval.evaluation_id, tr_node.lineage_id, created_at=created_at))
        log.append("evaluation_completed", {
            "evaluation_id": base_eval.evaluation_id, "accuracy": base_eval.metrics.get("accuracy"),
            "f1_macro": base_eval.metrics.get("f1_macro")}, created_at=created_at)

        # --- mint the production model identity + lineage ---------------------
        identity_obj = mint_identity("production_model", {
            "training_run_id": tr.training_run_id, "model_key": tr.params_fingerprint})
        model_id = identity_obj.id
        m_node = self.lineage.record(make_production_model_lineage(
            model_id, exp_node.lineage_id, architecture=architecture.value,
            params_fingerprint=tr.params_fingerprint, created_at=created_at))
        log.append("model_created", {"model_id": model_id, "lineage_id": m_node.lineage_id},
                   created_at=created_at)

        # --- benchmark (deterministic metrics + informational timings) --------
        benchmark = benchmark_model(
            tr.model, bundle, model_id=model_id, architecture=architecture, n_classes=n_classes,
            training_time_ms=tr.training_time_ms, split="test", created_at=created_at)
        b_node = self.lineage.record(make_benchmark_lineage(
            benchmark.benchmark_id, m_node.lineage_id, ev_node.lineage_id,
            metrics_signature=benchmark.metrics_signature(), created_at=created_at))
        benchmark = replace(benchmark, lineage_id=b_node.lineage_id)
        log.append("benchmark_completed", {
            "benchmark_id": benchmark.benchmark_id,
            "accuracy": benchmark.deterministic_metrics.get("accuracy"),
            "roc_auc_macro": benchmark.deterministic_metrics.get("roc_auc_macro")},
            created_at=created_at)

        # --- extended evaluation analyses -------------------------------------
        evaluation = build_model_evaluation(
            tr.model, bundle, model_id=model_id, evaluation_id=base_eval.evaluation_id,
            n_classes=n_classes, created_at=created_at)
        evaluation = replace(evaluation, lineage_id=ev_node.lineage_id)
        log.append("model_evaluation_completed", {
            "model_evaluation_id": evaluation.model_evaluation_id}, created_at=created_at)

        # --- content validation -----------------------------------------------
        checks = self.content_validator.content_checks(
            architecture=architecture, experiment=experiment, benchmark=benchmark,
            evaluation=evaluation, n_classes=n_classes, reproducible=tr.reproducible,
            determinism_detail={"reproducible": tr.reproducible,
                                "params_fingerprint": tr.params_fingerprint})
        content_ok = all(passed for _, passed, _ in checks)
        validation = ModelValidationRecord(
            validation_id=content_id("prodval", {
                "model_id": model_id, "checks": [[n, bool(p)] for n, p, _ in checks]}),
            ok=content_ok, checks=tuple(checks))

        # --- readiness (benchmark chain proves traceability to the patient) ---
        traceable = self.lineage.verify_chain(b_node.lineage_id)
        readiness = self.readiness_engine.assess(
            model_id=model_id, training_present=True, evaluation_present=True,
            benchmark_present=True, registered=True, validation_ok=content_ok,
            traceable=traceable, audited=log.verify(), created_at=created_at)
        r_node = self.lineage.record(make_readiness_lineage(
            readiness.readiness_id, b_node.lineage_id,
            classification=readiness.classification.value, created_at=created_at))
        readiness = replace(readiness, lineage_id=r_node.lineage_id)
        log.append("readiness_scored", {
            "readiness_id": readiness.readiness_id, "classification": readiness.classification.value,
            "score": readiness.score}, created_at=created_at)

        # --- status + version --------------------------------------------------
        status = ModelStatus.CANDIDATE if content_ok else ModelStatus.QUARANTINED
        rep_case = feature_records[0].case_id
        patient_ids = tuple(sorted({r.patient_id for r in feature_records}))
        dependencies = (experiment.experiment_id, tr.training_run_id, bundle.record.dataset_id,
                        benchmark.benchmark_id)
        identity = ProductionModelIdentity(
            model_id=model_id, training_run_id=tr.training_run_id,
            training_experiment_id=experiment.experiment_id, architecture=architecture,
            identity_version=identity_obj.identity_version)
        state_sig = ProductionModelRecord.state_signature_of(
            identity=identity, architecture=architecture, dataset_id=bundle.record.dataset_id,
            training_experiment_id=experiment.experiment_id, base_evaluation_id=base_eval.evaluation_id,
            benchmark_id=benchmark.benchmark_id, model_evaluation_id=evaluation.model_evaluation_id,
            readiness_id=readiness.readiness_id, readiness_class=readiness.classification,
            case_id=rep_case, patient_ids=patient_ids, validation=validation,
            params_fingerprint=tr.params_fingerprint, status=status, dependencies=dependencies)
        version = ModelVersion(version=ModelVersion.compute(state_sig, None), previous=None,
                               reason="developed", created_at=created_at)
        log.append("model_version_changed", {"version": version.version, "reason": "developed"},
                   created_at=created_at)

        # --- register the base model in the SHARED model registry (no parallel)
        self.model_registry.register(FoundationModelRegistryRecord(
            model_id=model_id, architecture=architecture.value, dataset_id=bundle.record.dataset_id,
            training_run_id=tr.training_run_id, evaluation_id=base_eval.evaluation_id,
            experiment_id=experiment.experiment_id, case_id=rep_case, patient_ids=patient_ids,
            status=(FoundationModelStatus.TRAINED if content_ok else FoundationModelStatus.QUARANTINED),
            version=version.version, owner=owner, creation_date=created_at, audit_state=log.head,
            lineage_id=m_node.lineage_id, dependencies=dependencies))

        reg_kind = "model_registered" if status == ModelStatus.CANDIDATE else "model_quarantined"
        log.append(reg_kind, {"model_id": model_id, "status": status.value,
                              "readiness": readiness.classification.value}, created_at=created_at)

        model_record = ProductionModelRecord(
            identity=identity, architecture=architecture, dataset_id=bundle.record.dataset_id,
            training_experiment_id=experiment.experiment_id, base_evaluation_id=base_eval.evaluation_id,
            benchmark_id=benchmark.benchmark_id, model_evaluation_id=evaluation.model_evaluation_id,
            readiness_id=readiness.readiness_id, readiness_class=readiness.classification,
            case_id=rep_case, patient_ids=patient_ids, validation=validation,
            params_fingerprint=tr.params_fingerprint, status=status, version=version, owner=owner,
            created_at=created_at, lineage_id=m_node.lineage_id, audit_head=log.head,
            dependencies=dependencies)

        # --- register the production candidate (own registry; new artifacts) --
        self.production_registry.register_experiment(experiment)
        self.production_registry.register_benchmark(benchmark)
        self.production_registry.register_evaluation(evaluation)
        self.production_registry.register_readiness(readiness)
        self.production_registry.register_model(self._registry_record(model_record))

        self._audit_logs[model_id] = log
        self._context[model_id] = {
            "dataset_record": bundle.record, "experiment": experiment, "base_evaluation": base_eval,
            "benchmark": benchmark, "evaluation": evaluation, "readiness": readiness,
            "model": model_record}
        return ProductionModelOutcome(
            accepted=True, reason=status.value, architecture=architecture, model=model_record,
            benchmark=benchmark, evaluation=evaluation, readiness=readiness, experiment=experiment,
            base_evaluation=base_eval, dataset_id=bundle.record.dataset_id)

    # --- benchmark every architecture ----------------------------------------
    def develop_all(self, feature_records: Sequence, *,
                    architectures: Sequence[ProductionArchitecture] = PRODUCTION_ARCHITECTURES,
                    **kwargs) -> dict:
        """Develop + benchmark every requested architecture from one feature cohort."""
        return {arch.value: self.develop_model(feature_records, architecture=arch, **kwargs)
                for arch in architectures}

    # --- comparison + validation + reports ------------------------------------
    def compare(self, outcomes) -> dict:
        """Compare >=2 developed models -> ranking, best-per-metric, recommended model."""
        items = outcomes.values() if isinstance(outcomes, dict) else outcomes
        benchmarks = [o.benchmark for o in items if o.benchmark is not None]
        if len(benchmarks) < 2:
            raise ProductionModelError("comparison requires >= 2 benchmarked models")
        return compare_models(benchmarks)

    def integrity(self, model: ProductionModelRecord):
        ctx = self._context[model.model_id]
        return self.integrity_validator.validate(
            model=model, experiment=ctx["experiment"], benchmark=ctx["benchmark"],
            evaluation=ctx["evaluation"], readiness=ctx["readiness"],
            dataset_registry=self.dataset_registry, model_registry=self.model_registry,
            production_registry=self.production_registry, audit_log=self._audit_logs[model.model_id],
            lineage_tracker=self.lineage)

    def reports(self, model: ProductionModelRecord, *, comparison: Optional[dict] = None) -> dict:
        ctx = self._context[model.model_id]
        log = self._audit_logs[model.model_id]
        return {
            "training_report": _reports.build_training_report(model, ctx["experiment"]),
            "benchmark_report": _reports.build_benchmark_report(model, ctx["benchmark"]),
            "evaluation_report": _reports.build_evaluation_report(model, ctx["evaluation"]),
            "comparison_report": _reports.build_comparison_report(
                comparison if comparison is not None else {"n_models": 1,
                                                            "recommended_model": model.model_id}),
            "readiness_report": _reports.build_readiness_report(model, ctx["readiness"]),
            "registry_report": _reports.build_registry_report(
                self.production_registry, self.model_registry, self.dataset_registry),
            "audit_report": _reports.build_audit_report(model, log),
            "lineage_report": _reports.build_lineage_report(model, self.lineage, ctx["readiness"]),
            "model_summary_report": _reports.build_model_summary_report(
                model, ctx["benchmark"], ctx["readiness"], self.integrity(model)),
        }

    # --- internals ------------------------------------------------------------
    def _registry_record(self, model: ProductionModelRecord) -> ModelRegistryRecord:
        return ModelRegistryRecord(
            model_id=model.model_id, architecture=model.architecture.value,
            dataset_id=model.dataset_id, training_experiment_id=model.training_experiment_id,
            benchmark_id=model.benchmark_id, model_evaluation_id=model.model_evaluation_id,
            readiness_id=model.readiness_id, base_evaluation_id=model.base_evaluation_id,
            case_id=model.case_id, patient_ids=model.patient_ids, status=model.status,
            readiness_class=model.readiness_class, version=model.version.version, owner=model.owner,
            creation_date=model.created_at, audit_state=model.audit_head or "",
            lineage_id=model.lineage_id or "", dependencies=model.dependencies)

    @property
    def version(self) -> str:
        return PRODUCTION_MODELS_VERSION


__all__ = ["ProductionModelService", "ProductionModelOutcome", "ProductionModelError"]
