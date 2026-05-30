"""ModelFoundationService — the governed orchestration hub for Productization P4.

Transforms feature assets (from Productization P3) into a **validated trained model**,
without touching upstream assets. The flow is:

    build a patient-disjoint dataset from feature assets -> register dataset ->
    train (deterministic) -> evaluate (deterministic) -> track experiment -> validate
    -> mint identity -> record lineage (Patient -> ... -> Dataset -> Training Run ->
    Model) -> append immutable audit events -> bump version -> register model

Every step is audited; nothing is registered outside this governed path. The service
shares the platform's single ``ml.lineage.LineageTracker`` (so a model's chain reaches
the patient) and the shared ``ImmutableAuditLog`` (no parallel systems). It reads only
the feature assets' lineage nodes + their assembled feature vectors; it performs **no
inference serving, no predictions for users, no APIs** (forbidden in this phase).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Optional, Sequence

from ml.lineage import LineageTracker
from ml.provenance import content_id

from .version import MODEL_FOUNDATION_VERSION, DEFAULT_SEED, DETERMINISTIC_EPOCH
from .identity import mint_identity
from .models.domain import (
    ExperimentStatus, ModelArchitecture, ModelIdentity, ModelMetadata,
    ModelRecord, ModelRegistryRecord, ModelStatus, ModelValidationRecord, ModelVersion, SplitName,
)
from .datasets import build_feature_dataset, ExternalDatasetConnector
from .training import train
from .evaluation import evaluate
from .experiments import build_experiment, ExperimentRegistry
from .validation import ModelContentValidator, ModelIntegrityValidator
from .registry import DatasetRegistry, ModelRegistry
from .audit import make_model_audit_log, ImmutableAuditLog
from .lineage import make_dataset_lineage, make_training_lineage, make_evaluation_lineage, make_model_lineage
from .reports import (
    build_dataset_report, build_training_report, build_evaluation_report, build_experiment_report,
    build_model_report, build_audit_report, build_lineage_report, build_validation_report,
    build_registry_report,
)


class ModelFoundationError(RuntimeError):
    """Raised on programmer misuse of the service (not for unusable inputs)."""


@dataclass(frozen=True)
class ModelOutcome:
    """The result of attempting to train + register a model from feature assets."""

    accepted: bool
    reason: str
    model: Optional[ModelRecord] = None
    dataset_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted, "reason": self.reason,
            "model_id": self.model.model_id if self.model else None,
            "dataset_id": self.dataset_id,
            "model": self.model.to_dict() if self.model else None,
        }


class ModelFoundationService:
    """Stateful service: a shared lineage tracker, the dataset/model/experiment
    registries, and per-model immutable audit logs + record context."""

    def __init__(self, *, lineage_tracker: Optional[LineageTracker] = None,
                 dataset_registry: Optional[DatasetRegistry] = None,
                 model_registry: Optional[ModelRegistry] = None,
                 experiment_registry: Optional[ExperimentRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.dataset_registry = dataset_registry or DatasetRegistry()
        self.model_registry = model_registry or ModelRegistry()
        self.experiment_registry = experiment_registry or ExperimentRegistry()
        self.content_validator = ModelContentValidator()
        self.integrity_validator = ModelIntegrityValidator()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}
        self._context: dict[str, dict] = {}

    def audit_log_for(self, model_id: str) -> ImmutableAuditLog:
        return self._audit_logs[model_id]

    # --- external dataset registration (framework; no download) ---------------
    def register_external_dataset(self, source, manifest_or_path, *, dataset_key: str):
        """Register an external dataset (TUH/CHB-MIT/Temple) from a local manifest."""
        connector = ExternalDatasetConnector(source)
        record = connector.build_record(manifest_or_path, dataset_key=dataset_key)
        self.dataset_registry.register(record)
        return record

    # --- the single use case --------------------------------------------------
    def train_model(self, feature_records: Sequence, *, architecture: ModelArchitecture,
                    name: str = "experiment", dataset_key: str = "default", seed: int = DEFAULT_SEED,
                    hyperparameters: Optional[dict] = None, labels: Optional[dict] = None,
                    label_fn: Optional[Callable] = None, n_classes: int = 2,
                    val_fraction: float = 0.2, test_fraction: float = 0.2, owner: str = "model-ops",
                    created_at: str = DETERMINISTIC_EPOCH) -> ModelOutcome:
        """Build a dataset from feature assets and train + evaluate + register a model."""
        if not feature_records:
            raise ModelFoundationError("no feature assets supplied")
        feature_lineage_ids = []
        for rec in feature_records:
            if not (rec.lineage_id and self.lineage.exists(rec.lineage_id)):
                raise ModelFoundationError(
                    "feature lineage node not present in the shared tracker; train with a shared "
                    "LineageTracker (Patient -> ... -> Feature -> Dataset -> Training Run -> Model)")
            feature_lineage_ids.append(rec.lineage_id)
        feature_lineage_ids = tuple(feature_lineage_ids)

        # --- build the trainable, patient-disjoint dataset --------------------
        # The dataset name is stable per dataset_key (independent of the experiment
        # name) so the content-addressed dataset is identical across experiments.
        bundle = build_feature_dataset(
            feature_records, name=f"feature_dataset[{dataset_key}]", dataset_key=dataset_key,
            labels=labels, label_fn=label_fn, n_classes=n_classes, val_fraction=val_fraction,
            test_fraction=test_fraction, seed=seed)

        # --- dataset lineage (parents the feature nodes) ----------------------
        ds_node = self.lineage.record(make_dataset_lineage(
            bundle.record.dataset_id, feature_lineage_ids, source=bundle.record.source.value,
            n_samples=bundle.record.n_samples, data_fingerprint=bundle.record.data_fingerprint,
            created_at=created_at))

        log = make_model_audit_log()
        log.append("dataset_registered", {
            "dataset_id": bundle.record.dataset_id, "source": bundle.record.source.value,
            "n_samples": bundle.record.n_samples, "n_features": bundle.record.n_features,
            "patient_disjoint": bundle.record.split.patient_disjoint}, created_at=created_at)
        dataset_record = replace(bundle.record, lineage_id=ds_node.lineage_id, audit_state=log.head)
        bundle = replace(bundle, record=dataset_record)
        self.dataset_registry.register(dataset_record)

        # --- train (deterministic) + determinism re-check ---------------------
        training_run, model = train(architecture, bundle, n_classes=n_classes, seed=seed,
                                    hyperparameters=hyperparameters, created_at=created_at)
        _, model2 = train(architecture, bundle, n_classes=n_classes, seed=seed,
                          hyperparameters=hyperparameters, created_at=created_at)
        determinism_ok = (training_run.params_fingerprint == model2.params_fingerprint())
        det_detail = {"equal": determinism_ok, "fingerprint": training_run.params_fingerprint}

        tr_node = self.lineage.record(make_training_lineage(
            training_run.training_run_id, ds_node.lineage_id, architecture=architecture.value,
            params_fingerprint=training_run.params_fingerprint, created_at=created_at))
        training_run = replace(training_run, lineage_id=tr_node.lineage_id, audit_state=log.head)
        log.append("training_completed", {
            "training_run_id": training_run.training_run_id, "architecture": architecture.value,
            "seed": seed, "train_accuracy": training_run.training_metrics.get("train_accuracy"),
            "params_fingerprint": training_run.params_fingerprint}, created_at=created_at)

        # --- evaluate (deterministic) -----------------------------------------
        evaluation = evaluate(model, bundle, training_run_id=training_run.training_run_id,
                              n_classes=n_classes, split=SplitName.TEST, created_at=created_at)
        ev_node = self.lineage.record(make_evaluation_lineage(
            evaluation.evaluation_id, tr_node.lineage_id, created_at=created_at))
        evaluation = replace(evaluation, lineage_id=ev_node.lineage_id)
        log.append("evaluation_completed", {
            "evaluation_id": evaluation.evaluation_id, "split": evaluation.split.value,
            "accuracy": evaluation.metrics.get("accuracy"),
            "f1_macro": evaluation.metrics.get("f1_macro")}, created_at=created_at)

        # --- metadata ----------------------------------------------------------
        split = bundle.record.split
        metadata = ModelMetadata(
            architecture=architecture, dataset_id=bundle.record.dataset_id,
            dataset_source=bundle.record.source.value, n_features=bundle.record.n_features,
            n_classes=n_classes, class_labels=bundle.record.class_labels, n_params=training_run.n_params,
            seed=seed, hyperparameters=model.hyperparameters,
            train_accuracy=float(training_run.training_metrics.get("train_accuracy", 0.0)),
            eval_accuracy=float(evaluation.metrics.get("accuracy", 0.0)),
            eval_f1=float(evaluation.metrics.get("f1_macro", 0.0)),
            n_train=len(split.train), n_val=len(split.val), n_test=len(split.test))

        # --- content validation (5 checks) ------------------------------------
        checks = self.content_validator.content_checks(
            dataset_record=bundle.record, bundle=bundle, training_run=training_run,
            evaluation=evaluation, model_metadata=metadata, n_classes=n_classes,
            determinism_ok=determinism_ok, determinism_detail=det_detail)
        content_ok = all(passed for _, passed, _ in checks)
        validation = ModelValidationRecord(
            validation_id=content_id("modelval", {
                "dataset_id": bundle.record.dataset_id, "training_run_id": training_run.training_run_id,
                "checks": [[n, bool(p)] for n, p, _ in checks]}),
            ok=content_ok, checks=tuple(checks))

        # --- experiment --------------------------------------------------------
        rep_case = feature_records[0].case_id
        patient_ids = tuple(sorted({r.patient_id for r in feature_records}))
        configuration = {"architecture": architecture.value, "seed": seed, "n_classes": n_classes,
                         "val_fraction": val_fraction, "test_fraction": test_fraction,
                         **{f"hp_{k}": v for k, v in model.hyperparameters.items()}}

        # --- model identity (content-addressed by trained params) -------------
        identity_obj = mint_identity("model", {
            "training_run_id": training_run.training_run_id,
            "model_key": training_run.params_fingerprint})
        model_id = identity_obj.id

        experiment = build_experiment(
            name=name, dataset_id=bundle.record.dataset_id, architecture=architecture,
            configuration=configuration, training_run=training_run, evaluation=evaluation,
            artifact_refs=(model_id,),
            status=ExperimentStatus.COMPLETED if content_ok else ExperimentStatus.QUARANTINED,
            created_at=created_at)
        log.append("experiment_tracked", {
            "experiment_id": experiment.experiment_id, "name": name}, created_at=created_at)
        experiment = replace(experiment, audit_state=log.head)
        self.experiment_registry.register(experiment)

        status = ModelStatus.TRAINED if content_ok else ModelStatus.QUARANTINED
        identity = ModelIdentity(model_id=model_id, training_run_id=training_run.training_run_id,
                                 architecture=architecture, identity_version=identity_obj.identity_version)
        dependencies = (training_run.training_run_id, bundle.record.dataset_id)

        # --- model lineage + version ------------------------------------------
        m_node = self.lineage.record(make_model_lineage(
            model_id, tr_node.lineage_id, architecture=architecture.value,
            params_fingerprint=training_run.params_fingerprint, created_at=created_at))
        log.append("model_lineage_recorded", {
            "lineage_id": m_node.lineage_id, "parents": list(m_node.parents)}, created_at=created_at)

        state_sig = ModelRecord.state_signature_of(
            identity=identity, architecture=architecture, dataset_id=bundle.record.dataset_id,
            training_run_id=training_run.training_run_id, evaluation_id=evaluation.evaluation_id,
            experiment_id=experiment.experiment_id, case_id=rep_case, patient_ids=patient_ids,
            metadata=metadata, validation=validation,
            params_fingerprint=training_run.params_fingerprint, status=status, dependencies=dependencies)
        version = ModelVersion(version=ModelVersion.compute(state_sig, None), previous=None,
                               reason="trained", created_at=created_at)
        log.append("model_version_changed", {"version": version.version, "reason": "trained"},
                   created_at=created_at)
        reg_kind = "model_registered" if status == ModelStatus.TRAINED else "model_quarantined"
        log.append(reg_kind, {"model_id": model_id, "status": status.value}, created_at=created_at)

        model_record = ModelRecord(
            identity=identity, architecture=architecture, dataset_id=bundle.record.dataset_id,
            training_run_id=training_run.training_run_id, evaluation_id=evaluation.evaluation_id,
            experiment_id=experiment.experiment_id, case_id=rep_case, patient_ids=patient_ids,
            metadata=metadata, validation=validation,
            params_fingerprint=training_run.params_fingerprint, status=status, version=version,
            owner=owner, created_at=created_at, lineage_id=m_node.lineage_id, audit_head=log.head,
            dependencies=dependencies)

        self._audit_logs[model_id] = log
        self._context[model_id] = {
            "dataset_record": bundle.record, "training_run": training_run,
            "evaluation": evaluation, "experiment": experiment, "model": model_record}
        self.model_registry.register(self._registry_record(model_record))
        return ModelOutcome(accepted=True, reason=status.value, model=model_record,
                            dataset_id=bundle.record.dataset_id)

    # --- validation + reports -------------------------------------------------
    def integrity(self, model: ModelRecord):
        ctx = self._context[model.model_id]
        return self.integrity_validator.validate(
            model=model, dataset_record=ctx["dataset_record"], training_run=ctx["training_run"],
            evaluation=ctx["evaluation"], dataset_registry=self.dataset_registry,
            model_registry=self.model_registry, audit_log=self._audit_logs[model.model_id],
            lineage_tracker=self.lineage)

    def reports(self, model: ModelRecord) -> dict:
        ctx = self._context[model.model_id]
        log = self._audit_logs[model.model_id]
        return {
            "dataset_report": build_dataset_report(model, ctx["dataset_record"]),
            "training_report": build_training_report(model, ctx["training_run"]),
            "evaluation_report": build_evaluation_report(model, ctx["evaluation"]),
            "experiment_report": build_experiment_report(model, ctx["experiment"]),
            "model_report": build_model_report(model),
            "registry_report": build_registry_report(self.model_registry, self.dataset_registry,
                                                      self.experiment_registry),
            "audit_report": build_audit_report(model, log),
            "lineage_report": build_lineage_report(model, self.lineage),
            "validation_report": build_validation_report(model, self.integrity(model)),
        }

    # --- internals ------------------------------------------------------------
    def _registry_record(self, model: ModelRecord) -> ModelRegistryRecord:
        return ModelRegistryRecord(
            model_id=model.model_id, architecture=model.architecture.value, dataset_id=model.dataset_id,
            training_run_id=model.training_run_id, evaluation_id=model.evaluation_id,
            experiment_id=model.experiment_id, case_id=model.case_id, patient_ids=model.patient_ids,
            status=model.status, version=model.version.version, owner=model.owner,
            creation_date=model.created_at, audit_state=model.audit_head or "",
            lineage_id=model.lineage_id or "", dependencies=model.dependencies)

    @property
    def version(self) -> str:
        return MODEL_FOUNDATION_VERSION
