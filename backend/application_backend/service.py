"""ApplicationBackendService — the Application Backend Platform composition hub (P6).

Wires the reused P1-P5 services + the clinical ``CaseService`` over a single shared
``ml.lineage.LineageTracker`` and the shared ``ImmutableAuditLog``, and adds the P6
application subsystems (auth, users, EEG workflow, API, storage, registry, validation,
reports). It exposes the high-level domain operations the API layer dispatches to, plus
``prepare_model`` (train + register a model from a cohort of real EEG files) so the
final deliverable runs end to end:

    register/login -> upload EEG -> start analysis -> prediction + confidence +
    explanation -> retrieve results

No frontend, deployment, monitoring, or cloud infrastructure (all out of scope). The
hub orchestrates existing services and never duplicates their business logic.
"""

from __future__ import annotations

import os
import tempfile
from typing import Optional, Sequence

from ml.lineage import LineageTracker

# Reused P1-P5 + clinical services (intra-backend; never frontend).
from backend.clinical_cases import CaseService
from backend.eeg_foundation import EEGFoundationService, LocalEEGStore
from backend.signal_processing import SignalProcessingService, ProcessedSignalStore
from backend.feature_engineering import FeatureEngineeringService
from backend.model_foundation import ModelFoundationService, ModelArchitecture
from backend.inference_foundation import InferenceFoundationService

from .version import APPLICATION_BACKEND_VERSION, DETERMINISTIC_EPOCH
from .identity import mint_identity
from .models.domain import (
    BackendRegistryRecord, EntityKind, UploadRecord, UploadStatus, UserRole,
)
from .audit import make_backend_audit_log, ImmutableAuditLog
from .lineage import make_upload_lineage
from .registry import BackendRegistry
from .storage import UploadByteStore, make_upload_store, make_workflow_store, make_analysis_store
from .users import UserService
from .auth import AuthService, SecureEntropy
from .workflows import EegWorkflowService, ModelContext
from .validation import ApplicationIntegrityValidator
from .reports import (
    build_user_report, build_workflow_report, build_analysis_report,
    build_api_report, build_registry_report, build_audit_report, build_lineage_report,
    build_validation_report,
)
from .api import ApplicationAPI


class ApplicationBackendError(RuntimeError):
    """Raised on hub misuse (e.g. starting an analysis with no prepared model)."""


class ApplicationBackendService:
    """The governed Application Backend hub."""

    def __init__(self, *, workspace_dir: Optional[str] = None,
                 lineage_tracker: Optional[LineageTracker] = None, entropy=None):
        self.workspace = os.path.abspath(workspace_dir or tempfile.mkdtemp(prefix="nv_appbackend_"))
        os.makedirs(self.workspace, exist_ok=True)
        self.lineage = lineage_tracker or LineageTracker()

        # --- reused platform services (shared tracker) ---
        self.eeg_store = LocalEEGStore(os.path.join(self.workspace, "raw"))
        self.processed_store = ProcessedSignalStore(os.path.join(self.workspace, "proc"))
        self.case_service = CaseService(lineage_tracker=self.lineage)
        self.eeg_service = EEGFoundationService(self.eeg_store, lineage_tracker=self.lineage)
        self.signal_service = SignalProcessingService(self.eeg_store, self.processed_store,
                                                       lineage_tracker=self.lineage)
        self.feature_service = FeatureEngineeringService(self.processed_store,
                                                         lineage_tracker=self.lineage)
        self.model_service = ModelFoundationService(lineage_tracker=self.lineage)
        self.inference_service = InferenceFoundationService(lineage_tracker=self.lineage)

        # --- application subsystems (shared registry) ---
        self.registry = BackendRegistry()
        self.users = UserService(lineage_tracker=self.lineage, registry=self.registry)
        self.auth = AuthService(users=self.users, lineage_tracker=self.lineage,
                                registry=self.registry, entropy=entropy or SecureEntropy())
        self.workflow_service = EegWorkflowService(
            lineage_tracker=self.lineage, case_service=self.case_service,
            eeg_service=self.eeg_service, signal_service=self.signal_service,
            feature_service=self.feature_service, inference_service=self.inference_service,
            registry=self.registry)
        self.integrity_validator = ApplicationIntegrityValidator()

        # --- application storage ---
        self.upload_bytes = UploadByteStore(os.path.join(self.workspace, "uploads"))
        self.uploads = make_upload_store()
        self.workflows = make_workflow_store()
        self.analyses = make_analysis_store()
        self._upload_audit: dict[str, ImmutableAuditLog] = {}
        self._model_context: Optional[ModelContext] = None

        # --- the API surface (constructed last; holds a back-reference) ---
        self.api = ApplicationAPI(self)

    @property
    def version(self) -> str:
        return APPLICATION_BACKEND_VERSION

    # =========================================================================
    # Model preparation (train + register a model from a cohort of real EEG files)
    # =========================================================================
    def prepare_model(self, cohort_files: Sequence[tuple], *,
                      architecture: ModelArchitecture = ModelArchitecture.EEGNET,
                      dataset_key: str = "cohort", seed: int = 7,
                      created_at: str = DETERMINISTIC_EPOCH) -> ModelContext:
        """Build a patient-disjoint cohort by running P1-P3 over real EEG files, then
        train + register a model (P4). ``cohort_files`` is a sequence of
        ``(patient_key, case_key, file_path)``.

        This reuses the exact P1-P5 pipeline; it trains no parallel models and creates
        no parallel EEG pipeline."""
        if len(cohort_files) < 2:
            raise ApplicationBackendError("a patient-disjoint cohort needs >= 2 recordings")
        feats = []
        for patient_key, case_key, file_path in cohort_files:
            case = self.case_service.create_case(patient_key=patient_key, case_key=case_key,
                                                 created_at=created_at)
            ingestion = self.eeg_service.ingest_eeg(
                file_path, case_id=case.case_id, patient_id=case.patient_id,
                case_lineage_id=case.lineage_id, created_at=created_at)
            if not ingestion.accepted:
                raise ApplicationBackendError(f"cohort EEG rejected: {ingestion.reason}")
            processed = self.signal_service.process(ingestion.asset, created_at=created_at).asset
            feats.append(self.feature_service.generate_features(processed, created_at=created_at).asset)
        model = self.model_service.train_model(
            feats, architecture=architecture, dataset_key=dataset_key, seed=seed,
            created_at=created_at).model
        self._model_context = ModelContext(model_record=model, train_feature_records=tuple(feats),
                                            dataset_key=dataset_key)
        return self._model_context

    def set_model_context(self, context: ModelContext) -> None:
        self._model_context = context

    @property
    def model_context(self) -> Optional[ModelContext]:
        return self._model_context

    # =========================================================================
    # Domain operations (called by the API layer)
    # =========================================================================
    def do_register(self, *, username: str, password: str, roles=None,
                    metadata: Optional[dict] = None, created_at: str = DETERMINISTIC_EPOCH):
        return self.auth.register(username=username, password=password, roles=roles,
                                  metadata=metadata, created_at=created_at)

    def do_upload(self, *, user, filename: str, content: bytes,
                  created_at: str = DETERMINISTIC_EPOCH) -> UploadRecord:
        """Receive a real EEG file's bytes: persist them, mint an upload, and record an
        upload lineage node parented on the user node (User -> Upload)."""
        if not isinstance(content, (bytes, bytearray)) or len(content) == 0:
            raise ValueError("upload content must be non-empty bytes")
        suffix = os.path.splitext(filename)[1] or ".bin"
        reference, fingerprint, size = self.upload_bytes.put_bytes(bytes(content), suffix=suffix)
        upload_id = mint_identity("upload", {"user_id": user.user_id,
                                            "upload_key": fingerprint}).id
        node = self.lineage.record(make_upload_lineage(
            upload_id, user.user_id, user.lineage_id, content_fingerprint=fingerprint,
            created_at=created_at))
        log = make_backend_audit_log()
        self._upload_audit[upload_id] = log
        log.append("upload_received", {"upload_id": upload_id, "user_id": user.user_id,
                                       "filename": filename, "content_fingerprint": fingerprint,
                                       "size_bytes": size, "lineage_id": node.lineage_id},
                   created_at=created_at)
        upload = UploadRecord(
            upload_id=upload_id, user_id=user.user_id, filename=filename,
            content_fingerprint=fingerprint, size_bytes=size, status=UploadStatus.RECEIVED,
            stored_reference=reference, created_at=created_at, lineage_id=node.lineage_id,
            audit_head=log.head)
        self.uploads.put(upload)
        self.registry.register(BackendRegistryRecord(
            entity_kind=EntityKind.UPLOAD, entity_id=upload_id, status=upload.status.value,
            version=fingerprint, owner=user.user_id, creation_date=created_at,
            audit_state=log.head, lineage_id=node.lineage_id, user_id=user.user_id,
            dependencies=(user.user_id,)))
        return upload

    def do_start_analysis(self, *, user, upload_id: str, patient_key: Optional[str] = None,
                          case_key: Optional[str] = None, created_at: str = DETERMINISTIC_EPOCH):
        """Run the EEG application workflow for an uploaded file using the active model."""
        if self._model_context is None:
            raise ApplicationBackendError("no model prepared; call prepare_model() first")
        upload = self.get_upload(upload_id)
        if upload.user_id != user.user_id and not user.has_role(UserRole.ADMIN):
            raise LookupError(f"upload {upload_id!r} not found")
        fp8 = upload.content_fingerprint[:8]
        patient_key = patient_key or f"upload-patient-{fp8}"
        case_key = case_key or f"upload-case-{fp8}"
        outcome = self.workflow_service.run(
            upload_record=upload, model_context=self._model_context, patient_key=patient_key,
            case_key=case_key, owner=user.user_id, created_at=created_at)
        if outcome.accepted:
            self.workflows.put(outcome.workflow)
            self.analyses.put(outcome.analysis)
        return outcome

    # --- retrieval ------------------------------------------------------------
    def get_upload(self, upload_id: str) -> UploadRecord:
        upload = self.uploads.find(upload_id)
        if upload is None:
            raise LookupError(f"upload {upload_id!r} not found")
        return upload

    def list_uploads_for_user(self, user_id: str) -> list[UploadRecord]:
        return [u for u in self.uploads.values() if u.user_id == user_id]

    def get_analysis(self, analysis_id: str):
        analysis = self.analyses.find(analysis_id)
        if analysis is None:
            raise LookupError(f"analysis {analysis_id!r} not found")
        return analysis

    def get_workflow(self, workflow_id: str):
        wf = self.workflows.find(workflow_id)
        if wf is None:
            raise LookupError(f"workflow {workflow_id!r} not found")
        return wf

    def list_analyses_for_user(self, user_id: str):
        return [a for a in self.analyses.values() if a.user_id == user_id]

    def _inference_asset_for_analysis(self, analysis_id: str):
        analysis = self.get_analysis(analysis_id)
        return self.workflow_service.inference_asset_for(analysis.prediction_id)

    def analysis_facet(self, analysis_id: str, facet: str) -> dict:
        """Return a single facet of an analysis result, reusing the P5 records."""
        asset = self._inference_asset_for_analysis(analysis_id)
        if facet == "prediction":
            return asset.prediction.to_dict()
        if facet == "confidence":
            return asset.confidence.to_dict()
        if facet == "explanation":
            return asset.explanation.to_dict()
        if facet == "calibration":
            return asset.calibration.to_dict()
        raise ValueError(f"unknown facet {facet!r}")

    def analysis_reports(self, analysis_id: str) -> dict:
        """Build the analysis report set (reusing the P5 inference report builders)."""
        analysis = self.get_analysis(analysis_id)
        asset = self.workflow_service.inference_asset_for(analysis.prediction_id)
        inference_reports = self.inference_service.reports(asset)
        workflow = self.get_workflow(analysis.workflow_id)
        wf_log = self.workflow_service.audit_log_for(workflow.workflow_id)
        return {
            "analysis_report": build_analysis_report(analysis, inference_reports),
            "workflow_report": build_workflow_report(workflow, wf_log),
            "prediction_report": inference_reports["prediction_report"],
            "confidence_report": inference_reports["confidence_report"],
            "calibration_report": inference_reports["calibration_report"],
            "explainability_report": inference_reports["explainability_report"],
            "inference_report": inference_reports["inference_report"],
            "lineage_report": build_lineage_report(self.lineage, workflow.lineage_id),
        }

    # =========================================================================
    # Validation + reports (application-level)
    # =========================================================================
    def integrity(self, workflow_id: str, *, session=None):
        """Run the eight application integrity checks over a finalized workflow."""
        workflow = self.get_workflow(workflow_id)
        user = self.users.get_user(workflow.user_id)
        wf_log = self.workflow_service.audit_log_for(workflow_id)
        session_log = (self.auth.audit_log_for(session.session_id)
                       if session is not None else None)
        return self.integrity_validator.validate(
            workflow=workflow, user=user, session=session, workflow_audit_log=wf_log,
            registry=self.registry, lineage_tracker=self.lineage, api_record=self.api.api_record,
            session_audit_log=session_log)

    def reports(self, workflow_id: str) -> dict:
        """A deterministic application report set anchored on one workflow."""
        workflow = self.get_workflow(workflow_id)
        user = self.users.get_user(workflow.user_id)
        analysis = next(a for a in self.analyses.values() if a.workflow_id == workflow_id)
        wf_log = self.workflow_service.audit_log_for(workflow_id)
        user_log = self.users.audit_log_for(user.user_id)
        inference_reports = self.inference_service.reports(
            self.workflow_service.inference_asset_for(workflow.prediction_id))
        return {
            "user_report": build_user_report(user, user_log),
            "workflow_report": build_workflow_report(workflow, wf_log),
            "analysis_report": build_analysis_report(analysis, inference_reports),
            "api_report": build_api_report(self.api.api_record),
            "registry_report": build_registry_report(self.registry),
            "audit_report": build_audit_report(wf_log, subject=workflow_id),
            "lineage_report": build_lineage_report(self.lineage, workflow.lineage_id),
            "validation_report": build_validation_report(self.integrity(workflow_id)),
        }


__all__ = ["ApplicationBackendService", "ApplicationBackendError", "ModelContext"]
