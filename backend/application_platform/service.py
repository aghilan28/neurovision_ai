"""``ApplicationPlatformService`` — the Real Product Application hub (Track 3).

Turns the model platform into a **usable product**. It REUSES ``application_backend``
(which already orchestrates the reused P1-P5 upload -> analysis -> prediction workflow over
a shared ``ml.lineage`` tracker + the shared ``ImmutableAuditLog``) and adds the product
layer: a bounded-segment EEG upload workflow, a prediction-request/result projection with an
evidence bundle, deterministic JSON/HTML/PDF reports, a product registry + audit + lineage,
and an application-readiness engine (NOT_READY / PARTIALLY_READY / READY_FOR_USERS).

It retrains no models and modifies no datasets, Track 1, Track 2, persistence, security, or
deployment. The five Track-2 architectures and the real recordings are reused as-is.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from ml.lineage import LineageTracker

from backend.application_backend import ApplicationBackendService
from backend.application_backend.api import ApiRequest
from backend.application_backend.models.domain import ApiOperation
from backend.model_foundation import ModelArchitecture

from . import reports as _reports
from .audit import make_application_audit_log
from .identity import mint
from .lineage import (
    make_model_ref_lineage, make_prediction_request_lineage, make_prediction_result_lineage,
    make_report_lineage, make_upload_lineage,
)
from .models.domain import (
    AnalysisRecord, ApplicationRegistryRecord, EntityKind, ReportRecord, UploadRecord,
    UploadStatus, WorkflowRecord, WorkflowStatus,
)
from .predictions import build_prediction_request, build_prediction_result
from .readiness import ApplicationReadinessEngine
from .registry import ApplicationRegistry
from .uploads import prepare_bounded_segment, validate_eeg_bytes
from .validation import ApplicationIntegrityValidator
from .workflows import ANALYSIS_STAGES, run_backend_analysis
from .version import (
    APPLICATION_PLATFORM_VERSION, DEFAULT_ANALYSIS_SECONDS, DETERMINISTIC_EPOCH,
)

# Track-3 UploadFormat <- detected
from .models.domain import UploadFormat

_ARCH_BY_VALUE = {a.value: a for a in ModelArchitecture}


class ApplicationPlatformError(RuntimeError):
    """Raised on hub misuse."""


@dataclass
class AnalysisOutcome:
    accepted: bool
    upload: UploadRecord
    workflow: Optional[WorkflowRecord] = None
    analysis: Optional[AnalysisRecord] = None
    prediction_request: object = None
    prediction_result: object = None
    report_record: Optional[ReportRecord] = None
    readiness: object = None
    validation: object = None
    reason: str = ""

    def to_dict(self) -> dict:
        return {"accepted": self.accepted, "upload": self.upload.to_dict(),
                "workflow": self.workflow.to_dict() if self.workflow else None,
                "analysis": self.analysis.to_dict() if self.analysis else None,
                "prediction_request": (self.prediction_request.to_dict()
                                       if self.prediction_request else None),
                "prediction_result": (self.prediction_result.to_dict()
                                      if self.prediction_result else None),
                "report": self.report_record.to_dict() if self.report_record else None,
                "readiness": self.readiness.to_dict() if self.readiness else None,
                "validation": self.validation.to_dict() if self.validation else None,
                "reason": self.reason}


class ApplicationPlatformService:
    """The governed product application hub (wraps application_backend; reuses everything)."""

    def __init__(self, *, workspace_dir: Optional[str] = None,
                 lineage_tracker: Optional[LineageTracker] = None,
                 analysis_seconds: float = DEFAULT_ANALYSIS_SECONDS) -> None:
        self.lineage = lineage_tracker or LineageTracker()
        self.backend = ApplicationBackendService(workspace_dir=workspace_dir,
                                                 lineage_tracker=self.lineage)
        self.registry = ApplicationRegistry()
        self.readiness_engine = ApplicationReadinessEngine()
        self.validator = ApplicationIntegrityValidator()
        self.analysis_seconds = float(analysis_seconds)
        self.audit = make_application_audit_log()
        self._model_info: dict = {}
        self._uploads: dict[str, UploadRecord] = {}
        self._analyses: dict[str, AnalysisOutcome] = {}
        self._reports: dict[str, dict] = {}

    @property
    def version(self) -> str:
        return APPLICATION_PLATFORM_VERSION

    # =========================================================================
    # Model preparation (reuse application_backend.prepare_model on real EEG)
    # =========================================================================
    def prepare_model(self, cohort_files, *, architecture=ModelArchitecture.EEGNET,
                      dataset_key: str = "cohort", seed: int = 7,
                      created_at: str = DETERMINISTIC_EPOCH):
        ctx = self.backend.prepare_model(cohort_files, architecture=architecture,
                                         dataset_key=dataset_key, seed=seed, created_at=created_at)
        self._model_info = {"model_id": ctx.model_record.model_id,
                            "architecture": architecture.value,
                            "readiness": getattr(ctx.model_record, "status", "candidate")
                            if isinstance(getattr(ctx.model_record, "status", None), str)
                            else getattr(getattr(ctx.model_record, "status", None), "value",
                                         "candidate")}
        self.audit.append("model_prepared", {"model_id": self._model_info["model_id"],
                                             "architecture": architecture.value},
                          created_at=created_at)
        return ctx

    def use_track2_model(self, candidate, *, train_feature_context) -> None:
        """Adopt a Track-2 CandidateModelRecord's identity for product reporting.

        The actual inference still runs through the reused application_backend model context;
        this records the Track-2 model's id/architecture/readiness for the evidence bundle.
        """
        self._model_info = {"model_id": candidate.model_id,
                            "architecture": candidate.architecture.value,
                            "readiness": candidate.readiness_class.value}

    # =========================================================================
    # T3 user lifecycle (thin pass-through to the reused backend API)
    # =========================================================================
    def register(self, *, username: str, password: str, roles=None,
                 created_at: str = DETERMINISTIC_EPOCH):
        return self.backend.api.handle(ApiRequest(ApiOperation.REGISTER_USER, {
            "username": username, "password": password, "roles": roles or ["clinician"]}),
            created_at=created_at)

    def login(self, *, username: str, password: str, created_at: str = DETERMINISTIC_EPOCH) -> str:
        resp = self.backend.api.handle(ApiRequest(ApiOperation.LOGIN, {
            "username": username, "password": password}), created_at=created_at)
        if not resp.ok:
            raise ApplicationPlatformError(f"login failed: {resp.body}")
        return resp.body["token"]

    # =========================================================================
    # T3-D/E/F/G: the full product workflow
    # =========================================================================
    def upload_and_analyze(self, *, token: str, filename: str, content: bytes,
                           patient_key: Optional[str] = None, case_key: Optional[str] = None,
                           created_at: str = DETERMINISTIC_EPOCH) -> AnalysisOutcome:
        """The end-to-end user workflow: upload -> validate -> analyze -> predict -> report."""
        if not self._model_info:
            raise ApplicationPlatformError("no model prepared; call prepare_model() first")

        # --- T3-D: validate the real EEG bytes + prepare a bounded segment ---
        v = validate_eeg_bytes(content, filename)
        content_fp = mint("app_upload", {"filename": os.path.basename(filename),
                                         "sha": __import__("ml.provenance", fromlist=["hash_obj"])
                                         .hash_obj({"len": len(content)})})
        upload_id = mint("app_upload", {"filename": os.path.basename(filename),
                                        "fmt": v.fmt.value if v.fmt else "unknown",
                                        "sfreq": v.sampling_frequency, "nch": v.n_channels,
                                        "dur": round(v.duration_seconds, 3)})
        up_node = self.lineage.record(make_upload_lineage(
            upload_id, content_fingerprint=content_fp, created_at=created_at))
        self.audit.append("upload_received", {"upload_id": upload_id, "filename": filename,
                                             "valid": v.ok, "n_channels": v.n_channels},
                          created_at=created_at)

        upload = UploadRecord(
            upload_id=upload_id, user_id="(session)", filename=os.path.basename(filename),
            fmt=v.fmt or UploadFormat.EDF, content_fingerprint=content_fp,
            size_bytes=len(content), analysis_seconds=self.analysis_seconds,
            sampling_frequency=v.sampling_frequency, n_channels=v.n_channels,
            duration_seconds=v.duration_seconds,
            status=UploadStatus.VALIDATED if v.ok else UploadStatus.REJECTED,
            findings=tuple(f"{n}:{'ok' if p else 'fail'}" for n, p, _d in v.findings),
            created_at=created_at, lineage_id=up_node.lineage_id, audit_head=self.audit.head)
        self._uploads[upload_id] = upload
        self._register(EntityKind.UPLOAD, upload_id, content_fp, up_node.lineage_id, created_at)

        if not v.ok:
            return AnalysisOutcome(accepted=False, upload=upload, reason="upload_validation_failed")

        # bounded analysis segment (real, cropped) fed to the reused backend
        seg_path, _seg_fp, _seg_sz = prepare_bounded_segment(
            content, filename, analysis_seconds=self.analysis_seconds)
        try:
            ba = run_backend_analysis(self.backend, token=token, segment_path=seg_path,
                                      filename=filename, patient_key=patient_key,
                                      case_key=case_key, created_at=created_at)
        finally:
            if os.path.exists(seg_path):
                os.remove(seg_path)

        # --- model ref lineage (the model used) ---
        model_node = self.lineage.record(make_model_ref_lineage(
            self._model_info["model_id"], architecture=self._model_info["architecture"],
            created_at=created_at))

        # --- T3-F: prediction request + result (traceable) ---
        preq = build_prediction_request(
            upload_id=upload_id, user_id="(session)", model_id=self._model_info["model_id"],
            architecture=self._model_info["architecture"], created_at=created_at)
        preq_node = self.lineage.record(make_prediction_request_lineage(
            preq.prediction_request_id, up_node.lineage_id, model_node.lineage_id,
            created_at=created_at))
        from dataclasses import replace
        preq = replace(preq, lineage_id=preq_node.lineage_id)

        pres = build_prediction_result(prediction_request_id=preq.prediction_request_id,
                                       analysis=ba, model_info=self._model_info,
                                       created_at=created_at)
        pres_node = self.lineage.record(make_prediction_result_lineage(
            pres.prediction_result_id, preq_node.lineage_id, created_at=created_at))
        pres = replace(pres, lineage_id=pres_node.lineage_id)

        self.audit.append("prediction_generated", {
            "prediction_result_id": pres.prediction_result_id,
            "predicted_label": pres.predicted_label, "model_id": pres.model_id},
            created_at=created_at)

        # --- analysis + workflow records ---
        analysis_id = mint("app_analysis", {"upload_id": upload_id,
                                            "prediction_result_id": pres.prediction_result_id})
        workflow_id = mint("app_workflow", {"upload_id": upload_id, "analysis_id": analysis_id})
        analysis = AnalysisRecord(
            analysis_id=analysis_id, upload_id=upload_id, user_id="(session)",
            workflow_id=workflow_id, backend_analysis_id=ba.backend_analysis_id,
            prediction_request_id=preq.prediction_request_id,
            prediction_result_id=pres.prediction_result_id, status=WorkflowStatus.COMPLETED,
            created_at=created_at, lineage_id=pres_node.lineage_id)

        # --- T3-G: reports (build + export JSON/HTML/PDF) + report lineage ---
        report_payloads = self._build_reports(upload, analysis, preq, pres, created_at)
        report_fp = _reports.content_fingerprint(report_payloads["analysis_report"])
        report_id = mint("app_report", {"analysis_id": analysis_id, "fp": report_fp})
        report_node = self.lineage.record(make_report_lineage(
            report_id, pres_node.lineage_id, created_at=created_at))
        report_record = ReportRecord(
            report_id=report_id, analysis_id=analysis_id, report_type="analysis",
            available_formats=("json", "html", "pdf"), content_fingerprint=report_fp,
            created_at=created_at, lineage_id=report_node.lineage_id)
        self.audit.append("report_generated", {"report_id": report_id, "analysis_id": analysis_id,
                                              "formats": ["json", "html", "pdf"]},
                          created_at=created_at)

        workflow = WorkflowRecord(
            workflow_id=workflow_id, upload_id=upload_id, user_id="(session)",
            analysis_id=analysis_id, stages=tuple(s.value for s in ANALYSIS_STAGES),
            status=WorkflowStatus.COMPLETED, created_at=created_at,
            lineage_id=report_node.lineage_id, audit_head=self.audit.head)

        # --- register product entities (no orphans) ---
        self._register(EntityKind.PREDICTION_REQUEST, preq.prediction_request_id,
                       preq.prediction_request_id, preq_node.lineage_id, created_at,
                       deps=(upload_id,))
        self._register(EntityKind.PREDICTION_RESULT, pres.prediction_result_id, pres.signature(),
                       pres_node.lineage_id, created_at, deps=(preq.prediction_request_id,))
        self._register(EntityKind.ANALYSIS, analysis_id, analysis_id, pres_node.lineage_id,
                       created_at, deps=(upload_id, pres.prediction_result_id))
        self._register(EntityKind.WORKFLOW, workflow_id, workflow.signature(),
                       report_node.lineage_id, created_at, deps=(analysis_id,))
        self._register(EntityKind.REPORT, report_id, report_fp, report_node.lineage_id, created_at,
                       deps=(analysis_id,))

        # --- T3-I: application readiness + validation ---
        traceable = self.lineage.verify_chain(report_node.lineage_id)
        validation = self.validator.validate(
            upload=upload, analysis=analysis, prediction_result=pres, report_record=report_record,
            workflow=workflow, registry=self.registry, audit_log=self.audit,
            lineage_tracker=self.lineage)
        readiness = self.readiness_engine.assess(
            subject=workflow_id, upload_ok=upload.status == UploadStatus.VALIDATED,
            prediction_ok=bool(pres.predicted_label), workflow_ok=True, report_ok=True,
            registered=True, audited=self.audit.verify(), traceable=traceable,
            created_at=created_at)
        readiness = replace(readiness, lineage_id=report_node.lineage_id)
        self._register(EntityKind.READINESS, readiness.readiness_id, readiness.readiness_id,
                       report_node.lineage_id, created_at, deps=(workflow_id,))
        self.audit.append("readiness_scored", {"readiness_id": readiness.readiness_id,
                                             "classification": readiness.classification.value,
                                             "score": readiness.score}, created_at=created_at)

        outcome = AnalysisOutcome(
            accepted=True, upload=upload, workflow=workflow, analysis=analysis,
            prediction_request=preq, prediction_result=pres, report_record=report_record,
            readiness=readiness, validation=validation)
        self._analyses[analysis_id] = outcome
        self._reports[analysis_id] = report_payloads
        return outcome

    # =========================================================================
    # report access / export
    # =========================================================================
    def report_payloads(self, analysis_id: str) -> dict:
        if analysis_id not in self._reports:
            raise KeyError(f"no reports for analysis {analysis_id!r}")
        return self._reports[analysis_id]

    def export_report(self, analysis_id: str, report_type: str, fmt: str):
        payloads = self.report_payloads(analysis_id)
        key = f"{report_type}_report"
        if key not in payloads:
            raise KeyError(f"unknown report {report_type!r}; have {sorted(payloads)}")
        return _reports.export(payloads[key], fmt)

    # =========================================================================
    # internals
    # =========================================================================
    def _build_reports(self, upload, analysis, preq, pres, created_at) -> dict:
        wf_lineage = pres.lineage_id
        return {
            "analysis_report": _reports.build_analysis_report(upload, analysis, pres),
            "prediction_report": _reports.build_prediction_report(preq, pres),
            "metadata_report": _reports.build_metadata_report(upload),
            "model_report": _reports.build_model_report(pres),
            "evidence_report": _reports.build_evidence_report(pres),
            "audit_report": _reports.build_audit_report(self.audit, subject=analysis.analysis_id),
            "lineage_report": _reports.build_lineage_report(self.lineage, wf_lineage),
        }

    def _register(self, kind, entity_id, version, lineage_id, created_at, *, deps=()) -> None:
        self.registry.register(ApplicationRegistryRecord(
            entity_kind=kind, entity_id=entity_id, status="active", version=str(version),
            owner="application-ops", creation_date=created_at, audit_state=self.audit.head,
            lineage_id=lineage_id, dependencies=tuple(deps)))

    def get_analysis(self, analysis_id: str) -> AnalysisOutcome:
        if analysis_id not in self._analyses:
            raise KeyError(f"analysis {analysis_id!r} not found")
        return self._analyses[analysis_id]

    def reports_for(self, analysis_id: str) -> dict:
        """The product report set + the readiness report for a completed analysis."""
        outcome = self.get_analysis(analysis_id)
        payloads = dict(self.report_payloads(analysis_id))
        payloads["readiness_report"] = _reports.build_readiness_report(outcome.readiness)
        return payloads


__all__ = ["ApplicationPlatformService", "AnalysisOutcome", "ApplicationPlatformError"]
