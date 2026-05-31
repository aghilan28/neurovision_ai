"""ServingPlatformService — the governed orchestration hub for DRP-3.

Turns the model platform into a **serving platform**: it receives prediction requests,
selects models, executes inference (by **reusing** the inference foundation — no duplicated
prediction logic), generates + delivers responses, tracks the execution lifecycle, scores
readiness, traces lineage, and audits every execution — without training models or touching
any other subsystem.

    receive request -> validate -> select model (resolve/version) -> execute inference
    (reused) -> generate response (prediction + confidence + calibration + explanation) ->
    deliver -> complete -> validate -> score readiness -> version -> register ->
    record lineage (Dataset -> Feature -> Model -> Inference -> Request -> Execution ->
    Response) -> append immutable audit events

Shares the platform's single ``ml.lineage.LineageTracker`` (so a served response traces to
the patient) and the shared ``ImmutableAuditLog`` (no parallel systems); reuses the shared
``ModelRegistry`` via the serving engine. Invalid requests / missing models are handled
gracefully (a structured error, never a crash). It performs **no training, no frontend, no
deployment, no operations, no security, no persistence changes** (forbidden in this phase).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from ml.lineage import LineageTracker

from .version import SERVING_PLATFORM_VERSION, SERVING_IDENTITY_VERSION, DETERMINISTIC_EPOCH
from .identity import mint_identity
from .models.domain import (
    LifecycleState, ServingExecutionRecord, ServingIdentity,
    ServingRequestRecord, ServingStatus, ServingValidationRecord, ServingVersion,
)
from .contracts import (
    PredictionRequestContract, build_error_contract, build_prediction_response_contract,
    CONTRACT_REGISTRY,
)
from .execution import ModelServingEngine
from .routing import RoutingError
from .services import PredictionService
from .lifecycle import LifecycleTracker
from .validation import ServingContentValidator, ServingIntegrityValidator
from .readiness import ServingReadinessEngine
from .registry import ServingRegistry
from .audit import make_serving_audit_log, ImmutableAuditLog
from .lineage import (
    make_serving_request_lineage, make_serving_execution_lineage, make_serving_response_lineage,
)
from . import reports as _reports

from ml.provenance import content_id, hash_obj


class ServingPlatformError(RuntimeError):
    """Raised on programmer misuse of the service (not for unusable requests)."""


@dataclass(frozen=True)
class ServingOutcome:
    """The result of serving a prediction request."""

    accepted: bool
    reason: str
    execution: Optional[ServingExecutionRecord] = None
    response_contract: Optional[dict] = None
    error: Optional[dict] = None
    readiness: object = None

    @property
    def execution_id(self) -> Optional[str]:
        return self.execution.execution_id if self.execution else None

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted, "reason": self.reason,
            "execution_id": self.execution_id,
            "execution": self.execution.to_dict() if self.execution else None,
            "response_contract": self.response_contract, "error": self.error,
            "readiness": self.readiness.to_dict() if self.readiness else None,
        }


class ServingPlatformService:
    """Stateful service: a shared lineage tracker, the serving engine (reused inference
    foundation), the serving registry, and per-execution immutable audit logs + context."""

    def __init__(self, *, lineage_tracker: Optional[LineageTracker] = None,
                 engine: Optional[ModelServingEngine] = None,
                 registry: Optional[ServingRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.engine = engine or ModelServingEngine(lineage_tracker=self.lineage)
        if self.engine.lineage is not self.lineage:  # pragma: no cover - defensive
            raise ServingPlatformError("serving engine must share the serving lineage tracker")
        self.registry = registry or ServingRegistry()
        self.registry.register_contracts(CONTRACT_REGISTRY)
        self.prediction_service = PredictionService()
        self.content_validator = ServingContentValidator()
        self.integrity_validator = ServingIntegrityValidator()
        self.readiness_engine = ServingReadinessEngine()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}
        self._context: dict[str, dict] = {}

    def audit_log_for(self, execution_id: str) -> ImmutableAuditLog:
        return self._audit_logs[execution_id]

    # --- model loading (delegates to the engine) ------------------------------
    def load_model(self, model_record, train_feature_records, *, dataset_key: str,
                   val_fraction: float = 0.2, test_fraction: float = 0.2):
        return self.engine.load_model(model_record, train_feature_records, dataset_key=dataset_key,
                                      val_fraction=val_fraction, test_fraction=test_fraction)

    # --- the single use case --------------------------------------------------
    def serve(self, request_contract: PredictionRequestContract, input_feature_record, *,
              owner: str = "serving-ops", created_at: str = DETERMINISTIC_EPOCH) -> ServingOutcome:
        """Serve one prediction request end to end."""
        # --- request structure -------------------------------------------------
        ok, problems = request_contract.validate()
        if not ok:
            return self._reject("REQUEST_INVALID", "; ".join(problems), request_contract,
                                findings=problems, created_at=created_at)
        if request_contract.feature_asset_id != input_feature_record.feature_asset_id:
            return self._reject("FEATURE_MISMATCH",
                                "feature_asset_id does not match the supplied input record",
                                request_contract, created_at=created_at)
        if not (input_feature_record.lineage_id and self.lineage.exists(input_feature_record.lineage_id)):
            return self._reject("FEATURE_UNAVAILABLE",
                                "input feature lineage node not present in the shared tracker",
                                request_contract, created_at=created_at)

        # --- model resolution / selection / version selection -----------------
        try:
            decision = self.engine.resolve(request_contract.model_ref)
        except RoutingError as exc:
            return self._reject("MODEL_NOT_FOUND", str(exc), request_contract, created_at=created_at)
        servable = self.engine.servable(decision.model_id)
        model_record = servable.model_record

        # --- request created ---------------------------------------------------
        input_key = input_feature_record.lineage_id
        request_id = mint_identity("serving_request", {
            "model_ref_key": hash_obj(dict(sorted(request_contract.model_ref.items()))),
            "feature_asset_id": request_contract.feature_asset_id, "input_key": input_key}).id
        log = make_serving_audit_log()
        lc = LifecycleTracker(request_id)
        lc.record(LifecycleState.REQUEST_CREATED, request_id)
        log.append("request_received", {
            "request_id": request_id, "model_ref": dict(sorted(request_contract.model_ref.items())),
            "feature_asset_id": request_contract.feature_asset_id}, created_at=created_at)
        req_node = self.lineage.record(make_serving_request_lineage(
            request_id, model_record.lineage_id, input_feature_record.lineage_id,
            model_id=model_record.model_id, feature_asset_id=request_contract.feature_asset_id,
            created_at=created_at))
        request_record = ServingRequestRecord(
            request_id=request_id, model_ref=dict(sorted(request_contract.model_ref.items())),
            feature_asset_id=request_contract.feature_asset_id,
            case_id=request_contract.case_id, patient_id=request_contract.patient_id,
            requested_at=created_at, lineage_id=req_node.lineage_id, audit_state=log.head)

        # --- request validated + model selected -------------------------------
        lc.record(LifecycleState.REQUEST_VALIDATED, "structure+feature+model ok")
        log.append("request_validated", {"request_id": request_id}, created_at=created_at)
        lc.record(LifecycleState.MODEL_SELECTED,
                  f"{decision.strategy}:{decision.model_id}")
        log.append("model_selected", decision.to_dict(), created_at=created_at)

        # --- inference executed (REUSE the inference foundation) --------------
        inf_outcome = self.engine.execute(servable, input_feature_record, created_at=created_at)
        asset = inf_outcome.asset
        n_classes = model_record.metadata.n_classes
        lc.record(LifecycleState.INFERENCE_EXECUTED, asset.prediction_id)
        log.append("inference_executed", {
            "prediction_id": asset.prediction_id,
            "predicted_class": asset.prediction.predicted_class}, created_at=created_at)

        # --- response generated -----------------------------------------------
        execution_id = mint_identity("serving_execution", {
            "request_id": request_id, "prediction_id": asset.prediction_id}).id
        response_body = self.prediction_service.build_response_body(
            request_record, asset, created_at=created_at)
        response_id = mint_identity("serving_response", {
            "execution_id": execution_id, "response_key": asset.prediction.signature()}).id
        lc.record(LifecycleState.RESPONSE_GENERATED, response_id)
        log.append("response_generated", {
            "response_id": response_id, "execution_id": execution_id}, created_at=created_at)

        # --- lineage: execution + response nodes ------------------------------
        exec_node = self.lineage.record(make_serving_execution_lineage(
            execution_id, req_node.lineage_id, asset.lineage_id, prediction_id=asset.prediction_id,
            created_at=created_at))
        resp_node = self.lineage.record(make_serving_response_lineage(
            response_id, exec_node.lineage_id, predicted_class=response_body.predicted_class,
            created_at=created_at))
        response_record = replace(response_body, response_id=response_id, lineage_id=resp_node.lineage_id)
        lc.record(LifecycleState.RESPONSE_DELIVERED, response_id)
        log.append("response_delivered", {"response_id": response_id}, created_at=created_at)
        lc.record(LifecycleState.EXECUTION_COMPLETED, execution_id)
        lifecycle_record = lc.to_record()
        log.append("execution_completed", {
            "execution_id": execution_id, "final_state": lifecycle_record.final_state},
            created_at=created_at)

        # --- content validation (build-time; version integrity is a post-build
        #     integrity check, kept out of the state signature to avoid self-reference) -
        response_contract = build_prediction_response_contract(response_record)
        completed = lifecycle_record.final_state == LifecycleState.EXECUTION_COMPLETED.value
        identity = ServingIdentity(
            execution_id=execution_id, request_id=request_id, response_id=response_id,
            model_id=model_record.model_id, prediction_id=asset.prediction_id,
            identity_version=SERVING_IDENTITY_VERSION)
        checks = (
            self.content_validator.request_structure(request_contract),
            self.content_validator.model_availability(True, model_record.model_id),
            self.content_validator.feature_availability(True, request_contract.feature_asset_id),
            self.content_validator.execution_integrity(lifecycle_record, completed),
            self.content_validator.response_integrity(response_record, n_classes),
            self.content_validator.contract_integrity(response_contract),
        )
        content_ok = all(p for _, p, _ in checks)
        contract_ok = next((p for n, p, _ in checks if n == "contract_integrity"), False)
        validation = ServingValidationRecord(
            validation_id=content_id("servval", {
                "execution_id": execution_id, "checks": [[n, bool(p)] for n, p, _ in checks]}),
            ok=content_ok, checks=checks)

        dependencies = (model_record.model_id, asset.prediction_id,
                        request_contract.feature_asset_id, request_id)

        # --- readiness ---------------------------------------------------------
        traceable = self.lineage.verify_chain(resp_node.lineage_id)
        readiness = self.readiness_engine.assess(
            target_id=execution_id, execution_ok=completed, contract_ok=contract_ok,
            validation_ok=content_ok, registered=True, audited=log.verify(),
            traceable=traceable, created_at=created_at)
        log.append("readiness_scored", {
            "readiness_id": readiness.readiness_id, "classification": readiness.classification.value,
            "score": readiness.score}, created_at=created_at)

        # --- status + version --------------------------------------------------
        status = ServingStatus.COMPLETED if content_ok else ServingStatus.FAILED
        state_sig = ServingExecutionRecord.state_signature_of(
            identity=identity, request=request_record, response=response_record,
            lifecycle=lifecycle_record, model_id=model_record.model_id,
            prediction_id=asset.prediction_id, feature_asset_id=request_contract.feature_asset_id,
            case_id=request_contract.case_id, patient_id=request_contract.patient_id,
            validation=validation, readiness_id=readiness.readiness_id,
            readiness_class=readiness.classification, status=status, dependencies=dependencies)
        version = ServingVersion(version=ServingVersion.compute(state_sig, None), previous=None,
                                 reason="served", created_at=created_at)
        log.append("serving_version_changed", {"version": version.version, "reason": "served"},
                   created_at=created_at)
        log.append("execution_registered", {"execution_id": execution_id, "status": status.value},
                   created_at=created_at)

        execution = ServingExecutionRecord(
            identity=identity, request=request_record, response=response_record,
            lifecycle=lifecycle_record, model_id=model_record.model_id,
            prediction_id=asset.prediction_id, feature_asset_id=request_contract.feature_asset_id,
            case_id=request_contract.case_id, patient_id=request_contract.patient_id,
            validation=validation, readiness_id=readiness.readiness_id,
            readiness_class=readiness.classification, status=status, version=version, owner=owner,
            created_at=created_at, lineage_id=exec_node.lineage_id, audit_head=log.head,
            dependencies=dependencies)

        # --- register (own registry; cross-references shared model + prediction)
        self.registry.register_request(request_record)
        self.registry.register_response(response_record)
        self.registry.register_readiness(readiness)
        self.registry.register_execution(self._registry_record(execution, readiness))

        self._audit_logs[execution_id] = log
        self._context[execution_id] = {"execution": execution, "readiness": readiness,
                                        "response_contract": response_contract, "asset": asset}
        return ServingOutcome(accepted=True, reason=status.value, execution=execution,
                              response_contract=response_contract, readiness=readiness)

    # --- validation + reports -------------------------------------------------
    def integrity(self, execution: ServingExecutionRecord):
        ctx = self._context[execution.execution_id]
        return self.integrity_validator.validate(
            execution=execution, response=execution.response, readiness=ctx["readiness"],
            registry=self.registry, audit_log=self._audit_logs[execution.execution_id],
            lineage_tracker=self.lineage)

    def reports(self, execution: ServingExecutionRecord) -> dict:
        ctx = self._context[execution.execution_id]
        log = self._audit_logs[execution.execution_id]
        integrity = self.integrity(execution)
        return {
            "serving_report": _reports.build_serving_report(execution),
            "execution_report": _reports.build_execution_report(execution),
            "validation_report": _reports.build_validation_report(execution, integrity),
            "readiness_report": _reports.build_readiness_report(execution, ctx["readiness"]),
            "registry_report": _reports.build_registry_report(self.registry),
            "audit_report": _reports.build_audit_report(execution, log),
            "lineage_report": _reports.build_lineage_report(execution, self.lineage),
            "contract_report": _reports.build_contract_report(execution),
            "service_summary_report": _reports.build_service_summary_report(
                execution, ctx["readiness"], integrity),
        }

    # --- internals ------------------------------------------------------------
    def _reject(self, code: str, message: str, request_contract: PredictionRequestContract, *,
                findings: Optional[list] = None, created_at: str = DETERMINISTIC_EPOCH) -> ServingOutcome:
        """Graceful rejection — a structured error, audited, never a crash. A rejected
        request did not execute, so nothing is registered (the registry stays orphan-free)."""
        log = make_serving_audit_log()
        log.append("request_rejected", {"code": code, "message": message,
                                        "model_ref": dict(sorted(request_contract.model_ref.items()))},
                   created_at=created_at)
        error = build_error_contract(code, message, findings=findings)
        return ServingOutcome(accepted=False, reason=code, error=error)

    def _registry_record(self, execution: ServingExecutionRecord, readiness):
        from .models.domain import ServingRegistryRecord
        return ServingRegistryRecord(
            execution_id=execution.execution_id, request_id=execution.request_id,
            response_id=execution.response_id, model_id=execution.model_id,
            prediction_id=execution.prediction_id, feature_asset_id=execution.feature_asset_id,
            case_id=execution.case_id, patient_id=execution.patient_id, status=execution.status,
            readiness_id=readiness.readiness_id, version=execution.version.version,
            owner=execution.owner, creation_date=execution.created_at,
            audit_state=execution.audit_head or "", lineage_id=execution.lineage_id or "",
            dependencies=execution.dependencies)

    @property
    def version(self) -> str:
        return SERVING_PLATFORM_VERSION


__all__ = ["ServingPlatformService", "ServingOutcome", "ServingPlatformError"]
