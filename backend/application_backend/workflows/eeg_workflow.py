"""EegWorkflowService — the application EEG workflow (P6-E).

Orchestrates the **existing** P1-P5 services into the single application use case:

    Upload -> Validate -> Process -> Generate Features ->
    Generate Prediction -> Generate Confidence -> Generate Explanation

It **duplicates no business logic** — each stage delegates to the real service
(``CaseService``, ``EEGFoundationService``, ``SignalProcessingService``,
``FeatureEngineeringService``, ``InferenceFoundationService``). The prediction stage
(P5) produces the prediction, confidence, calibration, and explanation together, so the
last three "stages" are recorded as completed sub-steps of that one governed call.

The workflow records a ``workflow`` **join** lineage node (parenting the upload node and
the prediction node) so a single ``verify_chain`` proves
User -> Upload -> EEG -> Processed -> Feature -> Model -> Prediction, and an immutable
per-workflow audit log captures every stage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ml.lineage import LineageTracker
from ml.provenance import hash_obj

from ..version import DETERMINISTIC_EPOCH
from ..identity import mint_identity
from ..models.domain import (
    AnalysisRecord, AnalysisStatus, BackendRegistryRecord, BackendVersion, EntityKind, UploadRecord,
    WorkflowRecord, WorkflowStage, WorkflowStatus,
)
from ..audit import make_backend_audit_log, ImmutableAuditLog
from ..lineage import make_workflow_lineage
from ..registry import BackendRegistry


class WorkflowError(RuntimeError):
    """Raised on workflow misuse (missing model context, unknown upload)."""


@dataclass(frozen=True)
class ModelContext:
    """A prepared, registered model + the cohort it was trained on (for deterministic
    reconstruction by P5) + the dataset key. Produced once; reused per analysis."""

    model_record: object
    train_feature_records: tuple
    dataset_key: str

    @property
    def model_id(self) -> str:
        return self.model_record.model_id


@dataclass(frozen=True)
class WorkflowOutcome:
    """The result of one workflow run."""

    accepted: bool
    reason: str
    workflow: Optional[WorkflowRecord] = None
    analysis: Optional[AnalysisRecord] = None
    inference_asset: object = None

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted, "reason": self.reason,
            "workflow": self.workflow.to_dict() if self.workflow else None,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "prediction_id": self.inference_asset.prediction_id if self.inference_asset else None,
        }


class EegWorkflowService:
    """Stateful orchestrator over the reused P1-P5 services."""

    def __init__(self, *, lineage_tracker: LineageTracker, case_service, eeg_service,
                 signal_service, feature_service, inference_service,
                 registry: Optional[BackendRegistry] = None):
        self.lineage = lineage_tracker
        self.case_service = case_service
        self.eeg_service = eeg_service
        self.signal_service = signal_service
        self.feature_service = feature_service
        self.inference_service = inference_service
        self.registry = registry or BackendRegistry()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}
        self._inference_assets: dict[str, object] = {}

    def audit_log_for(self, workflow_id: str) -> ImmutableAuditLog:
        return self._audit_logs[workflow_id]

    def inference_asset_for(self, prediction_id: str):
        return self._inference_assets[prediction_id]

    # --- the single use case --------------------------------------------------
    def run(self, *, upload_record: UploadRecord, model_context: ModelContext, patient_key: str,
            case_key: str, owner: str = "application-ops",
            created_at: str = DETERMINISTIC_EPOCH) -> WorkflowOutcome:
        """Run the full EEG application workflow from an uploaded file to an analysis."""
        if model_context is None or model_context.model_record is None:
            raise WorkflowError("no model context; prepare/register a model before analysis")
        if not (upload_record.lineage_id and self.lineage.exists(upload_record.lineage_id)):
            raise WorkflowError("upload lineage node not present in the shared tracker")

        stages: list[WorkflowStage] = [WorkflowStage.UPLOAD]

        # --- create the clinical case (reuse CaseService) ---------------------
        case = self.case_service.create_case(patient_key=patient_key, case_key=case_key,
                                             owner=owner, created_at=created_at)

        # --- VALIDATE + ingest the real EEG file (reuse EEGFoundationService) --
        ingestion = self.eeg_service.ingest_eeg(
            upload_record.stored_reference, case_id=case.case_id, patient_id=case.patient_id,
            case_lineage_id=case.lineage_id, owner=owner, created_at=created_at)
        if not ingestion.accepted or ingestion.asset is None:
            return WorkflowOutcome(accepted=False, reason=f"eeg_rejected:{ingestion.reason}")
        eeg_asset = ingestion.asset
        stages.append(WorkflowStage.VALIDATE)

        # --- PROCESS (reuse SignalProcessingService) --------------------------
        processing = self.signal_service.process(eeg_asset, owner=owner, created_at=created_at)
        if not processing.accepted or processing.asset is None:
            return WorkflowOutcome(accepted=False, reason=f"processing_failed:{processing.reason}")
        processed = processing.asset
        stages.append(WorkflowStage.PROCESS)

        # --- FEATURES (reuse FeatureEngineeringService) -----------------------
        feature = self.feature_service.generate_features(processed, owner=owner, created_at=created_at)
        if not feature.accepted or feature.asset is None:
            return WorkflowOutcome(accepted=False, reason=f"features_failed:{feature.reason}")
        feature_asset = feature.asset
        stages.append(WorkflowStage.FEATURES)

        # --- PREDICT + CONFIDENCE + EXPLANATION (reuse InferenceFoundationService)
        inference = self.inference_service.predict(
            model_context.model_record, feature_asset,
            train_feature_records=list(model_context.train_feature_records),
            dataset_key=model_context.dataset_key, owner=owner, created_at=created_at)
        if not inference.accepted or inference.asset is None:
            return WorkflowOutcome(accepted=False, reason=f"prediction_failed:{inference.reason}")
        asset = inference.asset
        stages += [WorkflowStage.PREDICT, WorkflowStage.CONFIDENCE, WorkflowStage.EXPLANATION]

        # --- workflow join node + audit + records -----------------------------
        workflow_key = hash_obj({
            "prediction_id": asset.prediction_id, "eeg_asset_id": eeg_asset.asset_id,
            "feature_asset_id": feature_asset.feature_asset_id, "model_id": model_context.model_id})
        workflow_id = mint_identity("workflow", {"upload_id": upload_record.upload_id,
                                                 "workflow_key": workflow_key}).id

        node = self.lineage.record(make_workflow_lineage(
            workflow_id, upload_record.lineage_id, asset.lineage_id,
            upload_id=upload_record.upload_id, prediction_id=asset.prediction_id,
            created_at=created_at))

        log = make_backend_audit_log()
        self._audit_logs[workflow_id] = log
        log.append("workflow_started", {"workflow_id": workflow_id,
                                        "upload_id": upload_record.upload_id,
                                        "user_id": upload_record.user_id}, created_at=created_at)
        log.append("eeg_validated", {"eeg_asset_id": eeg_asset.asset_id,
                                     "status": eeg_asset.status.value}, created_at=created_at)
        log.append("eeg_processed", {"processed_id": processed.processed_id}, created_at=created_at)
        log.append("features_generated", {"feature_asset_id": feature_asset.feature_asset_id},
                   created_at=created_at)
        log.append("prediction_generated", {"prediction_id": asset.prediction_id,
                                            "predicted_class": asset.prediction.predicted_class},
                   created_at=created_at)
        log.append("confidence_generated",
                   {"confidence_level": asset.confidence.confidence_level.value}, created_at=created_at)
        log.append("explanation_generated", {"method": asset.explanation.method.value},
                   created_at=created_at)
        log.append("workflow_lineage_recorded", {"lineage_id": node.lineage_id,
                                                 "parents": list(node.parents)}, created_at=created_at)

        dependencies = (upload_record.upload_id, eeg_asset.asset_id, processed.processed_id,
                        feature_asset.feature_asset_id, model_context.model_id, asset.prediction_id)
        state_sig = WorkflowRecord.state_signature_of(
            workflow_id=workflow_id, upload_id=upload_record.upload_id, user_id=upload_record.user_id,
            case_id=case.case_id, patient_id=case.patient_id, eeg_asset_id=eeg_asset.asset_id,
            processed_id=processed.processed_id, feature_asset_id=feature_asset.feature_asset_id,
            model_id=model_context.model_id, prediction_id=asset.prediction_id,
            stages=tuple(stages), status=WorkflowStatus.COMPLETED, dependencies=dependencies)
        version = BackendVersion(version=BackendVersion.compute(state_sig, None), previous=None,
                                 reason="completed", created_at=created_at)
        log.append("workflow_version_changed", {"version": version.version, "reason": "completed"},
                   created_at=created_at)
        log.append("workflow_completed", {"workflow_id": workflow_id,
                                          "status": WorkflowStatus.COMPLETED.value},
                   created_at=created_at)

        workflow = WorkflowRecord(
            workflow_id=workflow_id, upload_id=upload_record.upload_id, user_id=upload_record.user_id,
            case_id=case.case_id, patient_id=case.patient_id, eeg_asset_id=eeg_asset.asset_id,
            processed_id=processed.processed_id, feature_asset_id=feature_asset.feature_asset_id,
            model_id=model_context.model_id, prediction_id=asset.prediction_id, stages=tuple(stages),
            status=WorkflowStatus.COMPLETED, version=version, owner=owner, created_at=created_at,
            lineage_id=node.lineage_id, audit_head=log.head, dependencies=dependencies)

        # --- analysis summary -------------------------------------------------
        analysis_id = mint_identity("analysis", {"workflow_id": workflow_id,
                                                 "analysis_key": asset.prediction_id}).id
        analysis = AnalysisRecord(
            analysis_id=analysis_id, workflow_id=workflow_id, user_id=upload_record.user_id,
            prediction_id=asset.prediction_id, case_id=case.case_id, patient_id=case.patient_id,
            predicted_class=asset.prediction.predicted_class,
            predicted_label=asset.prediction.predicted_label,
            confidence_level=asset.confidence.confidence_level.value,
            calibration_quality=asset.calibration.calibration_quality.value,
            status=AnalysisStatus.GENERATED, created_at=created_at, lineage_id=node.lineage_id)

        self._inference_assets[asset.prediction_id] = asset
        self._register(workflow, analysis)
        return WorkflowOutcome(accepted=True, reason="completed", workflow=workflow,
                               analysis=analysis, inference_asset=asset)

    # --- internals ------------------------------------------------------------
    def _register(self, workflow: WorkflowRecord, analysis: AnalysisRecord) -> None:
        self.registry.register(BackendRegistryRecord(
            entity_kind=EntityKind.WORKFLOW, entity_id=workflow.workflow_id,
            status=workflow.status.value, version=workflow.version.version, owner=workflow.owner,
            creation_date=workflow.created_at, audit_state=workflow.audit_head or "",
            lineage_id=workflow.lineage_id or "", user_id=workflow.user_id,
            dependencies=workflow.dependencies))
        self.registry.register(BackendRegistryRecord(
            entity_kind=EntityKind.ANALYSIS, entity_id=analysis.analysis_id,
            status=analysis.status.value, version=workflow.version.version, owner=workflow.owner,
            creation_date=analysis.created_at, audit_state=workflow.audit_head or "",
            lineage_id=analysis.lineage_id or "", user_id=analysis.user_id,
            dependencies=(workflow.workflow_id, analysis.prediction_id)))


__all__ = ["EegWorkflowService", "ModelContext", "WorkflowOutcome", "WorkflowError"]
