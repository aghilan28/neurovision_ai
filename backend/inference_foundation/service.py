"""InferenceFoundationService — the governed orchestration hub for Productization P5.

Transforms a trained model (P4) + a feature asset (P3) into an **immutable validated
prediction asset**, without touching upstream assets. The flow is:

    load + verify model (deterministic reconstruction) -> assemble + validate input ->
    execute (deterministic) -> build prediction -> assess confidence -> assess
    calibration -> generate explanation -> validate -> mint identity -> record lineage
    (Patient -> ... -> Model -> Prediction) -> append immutable audit events -> bump
    version -> register

Every step is audited; nothing is registered outside this governed path. The service
shares the platform's single ``ml.lineage.LineageTracker`` (so a prediction's chain
reaches the patient) and the shared ``ImmutableAuditLog`` (no parallel systems). It
performs **no serving, no APIs, no user predictions** — only in-process inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from ml.lineage import LineageTracker
from ml.provenance import content_id, hash_obj

from .version import INFERENCE_FOUNDATION_VERSION, DETERMINISTIC_EPOCH, FINGERPRINT_DECIMALS
from .identity import mint_identity, validate_identity
from .models.domain import (
    InferenceIdentity, InferenceRecord, InferenceRegistryRecord, InferenceStatus,
    InferenceValidationRecord, PredictionVersion,
)
from .inference import ModelExecutionEngine, PredictionEngine
from .confidence import ConfidenceEngine
from .calibration import CalibrationEngine
from .explainability import ExplainabilityEngine
from .validation import InferenceContentValidator, InferenceIntegrityValidator
from .registry import InferenceRegistry
from .audit import make_inference_audit_log, ImmutableAuditLog
from .lineage import make_prediction_lineage
from .reports import (
    build_prediction_report, build_confidence_report, build_calibration_report,
    build_explainability_report, build_inference_report, build_audit_report, build_lineage_report,
    build_validation_report, build_registry_report,
)


class InferenceFoundationError(RuntimeError):
    """Raised on programmer misuse of the service (not for unusable inputs)."""


@dataclass(frozen=True)
class InferenceOutcome:
    """The result of attempting to generate a prediction asset."""

    accepted: bool
    reason: str
    asset: Optional[InferenceRecord] = None

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted, "reason": self.reason,
            "prediction_id": self.asset.prediction_id if self.asset else None,
            "asset": self.asset.to_dict() if self.asset else None,
        }


class InferenceFoundationService:
    """Stateful service: a shared lineage tracker, the inference registry, the engines,
    and per-prediction immutable audit logs + record context."""

    def __init__(self, *, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[InferenceRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or InferenceRegistry()
        self.execution_engine = ModelExecutionEngine()
        self.prediction_engine = PredictionEngine()
        self.confidence_engine = ConfidenceEngine()
        self.calibration_engine = CalibrationEngine()
        self.explainability_engine = ExplainabilityEngine()
        self.content_validator = InferenceContentValidator()
        self.integrity_validator = InferenceIntegrityValidator()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}
        self._context: dict[str, dict] = {}

    def audit_log_for(self, prediction_id: str) -> ImmutableAuditLog:
        return self._audit_logs[prediction_id]

    # --- the single use case --------------------------------------------------
    def predict(self, model_record, input_feature_record, *, train_feature_records: Sequence,
                val_fraction: float = 0.2, test_fraction: float = 0.2, dataset_key: str = "default",
                label_fn=None,
                owner: str = "inference-ops", created_at: str = DETERMINISTIC_EPOCH) -> InferenceOutcome:
        """Generate a validated prediction asset for ``input_feature_record`` using ``model_record``."""
        model_id = model_record.model_id
        feature_asset_id = input_feature_record.feature_asset_id
        case_id, patient_id = input_feature_record.case_id, input_feature_record.patient_id
        if not validate_identity(model_id, "model")[0]:
            raise InferenceFoundationError(f"invalid model_id {model_id!r}")
        if not (model_record.lineage_id and self.lineage.exists(model_record.lineage_id)):
            raise InferenceFoundationError("model lineage node not present in the shared tracker")
        if not (input_feature_record.lineage_id and self.lineage.exists(input_feature_record.lineage_id)):
            raise InferenceFoundationError("input feature lineage node not present in the shared tracker")

        # --- load + verify the model (deterministic reconstruction) -----------
        model, exec_meta, bundle = self.execution_engine.load_model(
            model_record, train_feature_records, val_fraction=val_fraction,
            test_fraction=test_fraction, dataset_key=dataset_key,
            label_fn=label_fn)
        n_classes = model_record.metadata.n_classes
        feature_names = bundle.record.feature_names

        # --- assemble + validate input, execute (deterministic) ----------------
        row = self.prediction_engine.assemble_input(input_feature_record, feature_names)
        self.execution_engine.validate_input(row, len(feature_names))
        probs = self.execution_engine.execute(model, row, n_classes=n_classes)
        input_fp = hash_obj({"row": [round(float(v), FINGERPRINT_DECIMALS) for v in row]})

        # --- prediction (+ determinism re-check) ------------------------------
        prediction = self.prediction_engine.build_prediction(
            probs, class_labels=model_record.metadata.class_labels, n_classes=n_classes)
        probs2 = self.execution_engine.execute(model, row, n_classes=n_classes)
        prediction2 = self.prediction_engine.build_prediction(
            probs2, class_labels=model_record.metadata.class_labels, n_classes=n_classes)
        determinism_ok = (prediction.signature() == prediction2.signature()
                          and np.array_equal(probs, probs2))
        det_detail = {"equal": determinism_ok, "prediction_signature": prediction.signature()}

        # --- confidence / calibration / explanation ---------------------------
        confidence = self.confidence_engine.assess(model, row, probs, n_classes=n_classes)
        calibration = self.calibration_engine.assess(
            model, bundle.X, bundle.y, prediction_confidence=confidence.confidence_score)
        explanation = self.explainability_engine.explain(
            model, row, probs, feature_names=feature_names, n_classes=n_classes,
            input_feature_record=input_feature_record)

        # --- content validation (5 checks) ------------------------------------
        checks = self.content_validator.content_checks(
            prediction=prediction, confidence=confidence, calibration=calibration,
            explanation=explanation, n_classes=n_classes, n_features=len(feature_names),
            determinism_ok=determinism_ok, determinism_detail=det_detail)
        content_ok = all(passed for _, passed, _ in checks)
        validation = InferenceValidationRecord(
            validation_id=content_id("infval", {
                "model_id": model_id, "feature_asset_id": feature_asset_id,
                "checks": [[n, bool(p)] for n, p, _ in checks]}),
            ok=content_ok, checks=tuple(checks))
        status = InferenceStatus.GENERATED if content_ok else InferenceStatus.QUARANTINED

        # --- identity (content-addressed) -------------------------------------
        prediction_key = hash_obj({
            "feature_asset_id": feature_asset_id, "input_fingerprint": input_fp,
            "prediction": prediction.signature()})
        identity_obj = mint_identity("prediction", {"model_id": model_id,
                                                   "prediction_key": prediction_key})
        prediction_id = identity_obj.id
        identity = InferenceIdentity(prediction_id=prediction_id, model_id=model_id,
                                     feature_asset_id=feature_asset_id,
                                     identity_version=identity_obj.identity_version)
        dependencies = (model_id, feature_asset_id)

        # --- metadata bundles --------------------------------------------------
        execution_metadata = {**exec_meta, "input_fingerprint": input_fp}
        model_metadata = {
            "model_id": model_id, "architecture": model_record.architecture.value,
            "training_run_id": model_record.training_run_id, "dataset_id": model_record.dataset_id,
            "n_classes": n_classes, "n_params": model_record.metadata.n_params,
            "train_accuracy": model_record.metadata.train_accuracy,
            "eval_accuracy": model_record.metadata.eval_accuracy}
        fm = input_feature_record.metadata
        feature_metadata = {
            "feature_asset_id": feature_asset_id, "processed_id": fm.processed_id,
            "eeg_asset_id": fm.eeg_asset_id, "n_channels": fm.n_channels,
            "sampling_frequency": fm.sampling_frequency, "n_features_model": len(feature_names)}

        # --- lineage + audit ---------------------------------------------------
        log = make_inference_audit_log()
        log.append("model_loaded", {
            "model_id": model_id, "verified": exec_meta["params_fingerprint_verified"],
            "version_verified": exec_meta["version_verified"]}, created_at=created_at)
        log.append("prediction_generated", {
            "prediction_id": prediction_id, "predicted_class": prediction.predicted_class,
            "prediction_signature": prediction.signature()}, created_at=created_at)
        log.append("confidence_assessed", {
            "confidence_level": confidence.confidence_level.value,
            "reliability": round(confidence.prediction_reliability, 6)}, created_at=created_at)
        log.append("calibration_assessed", {
            "calibration_quality": calibration.calibration_quality.value,
            "ece": round(calibration.expected_calibration_error, 6)}, created_at=created_at)
        log.append("explanation_generated", {
            "method": explanation.method.value,
            "explanation_signature": explanation.signature()}, created_at=created_at)
        log.append("inference_validated", {"ok": validation.ok,
                   "validation_signature": validation.signature()}, created_at=created_at)
        node = self.lineage.record(make_prediction_lineage(
            prediction_id, model_record.lineage_id, input_feature_record.lineage_id,
            model_id=model_id, feature_asset_id=feature_asset_id,
            prediction_fingerprint=prediction.signature(), created_at=created_at))
        log.append("prediction_lineage_recorded", {
            "lineage_id": node.lineage_id, "parents": list(node.parents)}, created_at=created_at)

        # --- version + assemble immutable asset -------------------------------
        state_sig = InferenceRecord.state_signature_of(
            identity=identity, model_id=model_id, feature_asset_id=feature_asset_id, case_id=case_id,
            patient_id=patient_id, prediction=prediction, confidence=confidence,
            calibration=calibration, explanation=explanation, execution_metadata=execution_metadata,
            validation=validation, status=status, dependencies=dependencies)
        version = PredictionVersion(version=PredictionVersion.compute(state_sig, None), previous=None,
                                    reason="generated", created_at=created_at)
        log.append("prediction_version_changed", {"version": version.version, "reason": "generated"},
                   created_at=created_at)
        reg_kind = "prediction_registered" if status == InferenceStatus.GENERATED else "prediction_quarantined"
        log.append(reg_kind, {"prediction_id": prediction_id, "status": status.value},
                   created_at=created_at)

        asset = InferenceRecord(
            identity=identity, model_id=model_id, feature_asset_id=feature_asset_id, case_id=case_id,
            patient_id=patient_id, prediction=prediction, confidence=confidence,
            calibration=calibration, explanation=explanation, execution_metadata=execution_metadata,
            model_metadata=model_metadata, feature_metadata=feature_metadata, validation=validation,
            status=status, version=version, owner=owner, created_at=created_at,
            lineage_id=node.lineage_id, audit_head=log.head, dependencies=dependencies)

        self._audit_logs[prediction_id] = log
        self._context[prediction_id] = {"asset": asset}
        self.registry.register(self._registry_record(asset))
        return InferenceOutcome(accepted=True, reason=status.value, asset=asset)

    # --- validation + reports -------------------------------------------------
    def integrity(self, asset: InferenceRecord):
        return self.integrity_validator.validate(
            asset=asset, registry=self.registry, audit_log=self._audit_logs[asset.prediction_id],
            lineage_tracker=self.lineage)

    def reports(self, asset: InferenceRecord) -> dict:
        log = self._audit_logs[asset.prediction_id]
        return {
            "prediction_report": build_prediction_report(asset),
            "confidence_report": build_confidence_report(asset),
            "calibration_report": build_calibration_report(asset),
            "explainability_report": build_explainability_report(asset),
            "inference_report": build_inference_report(asset),
            "registry_report": build_registry_report(self.registry),
            "audit_report": build_audit_report(asset, log),
            "lineage_report": build_lineage_report(asset, self.lineage),
            "validation_report": build_validation_report(asset, self.integrity(asset)),
        }

    # --- internals ------------------------------------------------------------
    def _registry_record(self, asset: InferenceRecord) -> InferenceRegistryRecord:
        return InferenceRegistryRecord(
            prediction_id=asset.prediction_id, model_id=asset.model_id,
            feature_asset_id=asset.feature_asset_id, case_id=asset.case_id, patient_id=asset.patient_id,
            predicted_class=asset.prediction.predicted_class,
            confidence_level=asset.confidence.confidence_level.value,
            calibration_quality=asset.calibration.calibration_quality.value, status=asset.status,
            version=asset.version.version, owner=asset.owner, creation_date=asset.created_at,
            audit_state=asset.audit_head or "", lineage_id=asset.lineage_id or "",
            dependencies=asset.dependencies)

    @property
    def version(self) -> str:
        return INFERENCE_FOUNDATION_VERSION
