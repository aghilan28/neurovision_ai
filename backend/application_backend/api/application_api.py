"""ApplicationAPI — the versioned in-process API surface (P6-F).

The single governed entry point for application access. For every request it:

    mint request id -> authenticate (if not public) -> validate
    (auth/authorization/request-structure/file-structure) -> dispatch to the reused
    domain operation -> build a structured response -> record the request + response
    (immutably audited, registered)

No HTTP, no networking, no serving infrastructure (out of scope) — this is an
in-process, structured, versioned (``v1``) contract layer over the hub service. Every
request/response is content-addressed and tracked with audit + lineage references (no
orphan records).
"""

from __future__ import annotations


from ml.lineage import make_lineage_record

from ..version import API_V1, DETERMINISTIC_EPOCH
from ..identity import mint_identity
from ..lineage import application_version_bundle
from ..models.domain import (
    ApiOperation, BackendRegistryRecord, EntityKind, RequestRecord, RequestStatus, ResponseRecord,
    ResponseStatus, UserRole,
)
from ..audit import make_backend_audit_log
from ..storage import make_request_store, make_response_store
from ..validation import RequestValidator, is_public
from ..auth import AuthError
from .contracts import ApiRequest, ApiResponse, describe_api


class ApplicationAPI:
    """A thin, governed dispatcher over the hub service (no business logic of its own)."""

    def __init__(self, service):
        self.service = service
        self.lineage = service.lineage
        self.registry = service.registry
        self.validator = RequestValidator()
        self.api_record = describe_api()
        self.requests = make_request_store()
        self.responses = make_response_store()
        self.audit = make_backend_audit_log()
        self._seq = 0
        # A single API root lineage node (so request/response/api registrations are
        # never orphans). It is a root, not part of the clinical chain.
        node = self.lineage.record(make_lineage_record(
            kind="api", versions=application_version_bundle(),
            inputs={"name": self.api_record.name}, outputs={"api_id": self.api_record.api_id},
            parents=(), created_at=DETERMINISTIC_EPOCH))
        self._api_lineage_id = node.lineage_id
        self.audit.append("api_initialized", {"api_id": self.api_record.api_id,
                                              "api_version": API_V1}, created_at=DETERMINISTIC_EPOCH)
        self.registry.register(BackendRegistryRecord(
            entity_kind=EntityKind.API, entity_id=self.api_record.api_id, status="active",
            version=API_V1, owner="application-ops", creation_date=DETERMINISTIC_EPOCH,
            audit_state=self.audit.head, lineage_id=self._api_lineage_id, dependencies=()))

    @property
    def version(self) -> str:
        return API_V1

    # --- the single entry point -----------------------------------------------
    def handle(self, request: ApiRequest, *, created_at: str = DETERMINISTIC_EPOCH) -> ApiResponse:
        self._seq += 1
        request_id = mint_identity("request", {
            "operation": request.operation.value,
            "request_key": _req_key(request, self._seq)}).id

        session = user = None
        if not is_public(request.operation) and request.token:
            session = self.service.auth.validate_session(request.token)
            if session is not None:
                user = self.service.users.get_user(session.user_id)

        checks = self.validator.checks(operation=request.operation, params=request.params,
                                       session=session, user=user)
        failed = [(n, d) for (n, ok, d) in checks if not ok]
        if failed:
            response = self._failure_response(failed)
            self._record(request, request_id, RequestStatus.REJECTED, session, user, response,
                         created_at)
            return response

        try:
            response = self._dispatch(request, session, user, created_at)
            status = RequestStatus.ACCEPTED
        except AuthError as exc:
            response = ApiResponse(ResponseStatus.UNAUTHORIZED, {"error": str(exc)},
                                   error_code="authentication")
            status = RequestStatus.REJECTED
        except (KeyError, LookupError) as exc:
            response = ApiResponse(ResponseStatus.NOT_FOUND, {"error": str(exc)},
                                   error_code="not_found")
            status = RequestStatus.REJECTED
        except (ValueError, RuntimeError) as exc:
            response = ApiResponse(ResponseStatus.BAD_REQUEST, {"error": str(exc)},
                                   error_code="bad_request")
            status = RequestStatus.REJECTED
        self._record(request, request_id, status, session, user, response, created_at)
        return response

    # --- dispatch -------------------------------------------------------------
    def _dispatch(self, request: ApiRequest, session, user,
                  created_at: str) -> ApiResponse:
        op = request.operation
        p = request.params or {}

        if op == ApiOperation.REGISTER_USER:
            rec = self.service.do_register(
                username=p["username"], password=p["password"],
                roles=p.get("roles"), metadata=p.get("metadata"), created_at=created_at)
            return ApiResponse(ResponseStatus.CREATED, {
                "user_id": rec.user_id, "username": rec.username,
                "roles": sorted(r.value for r in rec.roles), "status": rec.status.value})

        if op == ApiOperation.LOGIN:
            result = self.service.auth.login(username=p["username"], password=p["password"],
                                            created_at=created_at)
            return ApiResponse(ResponseStatus.OK, {
                "token": result.token, "session_id": result.session.session_id,
                "user_id": result.session.user_id})

        if op == ApiOperation.LOGOUT:
            revoked = self.service.auth.revoke_session(token=request.token, created_at=created_at)
            return ApiResponse(ResponseStatus.OK, {"session_id": revoked.session_id,
                                                   "status": revoked.status.value})

        if op == ApiOperation.UPLOAD_EEG:
            upload = self.service.do_upload(user=user, filename=p["filename"], content=p["content"],
                                           created_at=created_at)
            return ApiResponse(ResponseStatus.CREATED, {
                "upload_id": upload.upload_id, "filename": upload.filename,
                "content_fingerprint": upload.content_fingerprint, "size_bytes": upload.size_bytes,
                "status": upload.status.value})

        if op == ApiOperation.LIST_EEG:
            uploads = self.service.list_uploads_for_user(user.user_id)
            return ApiResponse(ResponseStatus.OK, {"uploads": [u.to_dict() for u in uploads]})

        if op == ApiOperation.RETRIEVE_EEG:
            upload = self._owned_upload(p["upload_id"], user)
            return ApiResponse(ResponseStatus.OK, {"upload": upload.to_dict()})

        if op == ApiOperation.START_ANALYSIS:
            outcome = self.service.do_start_analysis(
                user=user, upload_id=p["upload_id"], patient_key=p.get("patient_key"),
                case_key=p.get("case_key"), created_at=created_at)
            if not outcome.accepted:
                return ApiResponse(ResponseStatus.ERROR, {"reason": outcome.reason},
                                   error_code="workflow_failed")
            a = outcome.analysis
            return ApiResponse(ResponseStatus.CREATED, {
                "analysis_id": a.analysis_id, "workflow_id": a.workflow_id,
                "prediction_id": a.prediction_id, "predicted_class": a.predicted_class,
                "predicted_label": a.predicted_label, "confidence_level": a.confidence_level,
                "calibration_quality": a.calibration_quality, "status": a.status.value})

        if op in (ApiOperation.RETRIEVE_PREDICTION, ApiOperation.RETRIEVE_CONFIDENCE,
                  ApiOperation.RETRIEVE_EXPLANATION):
            analysis = self._owned_analysis(p["analysis_id"], user)
            facet = {ApiOperation.RETRIEVE_PREDICTION: "prediction",
                     ApiOperation.RETRIEVE_CONFIDENCE: "confidence",
                     ApiOperation.RETRIEVE_EXPLANATION: "explanation"}[op]
            return ApiResponse(ResponseStatus.OK,
                               {facet: self.service.analysis_facet(analysis.analysis_id, facet)})

        if op == ApiOperation.LIST_ANALYSIS_HISTORY:
            analyses = self.service.list_analyses_for_user(user.user_id)
            return ApiResponse(ResponseStatus.OK, {"analyses": [a.to_dict() for a in analyses]})

        if op == ApiOperation.LIST_REPORTS:
            analysis = self._owned_analysis(p["analysis_id"], user)
            reports = self.service.analysis_reports(analysis.analysis_id)
            return ApiResponse(ResponseStatus.OK,
                               {"report_names": sorted(reports), "reports": reports})

        return ApiResponse(ResponseStatus.BAD_REQUEST, {"error": f"unhandled operation {op.value}"},
                           error_code="unhandled")

    # --- ownership helpers ----------------------------------------------------
    def _owned_upload(self, upload_id: str, user):
        upload = self.service.get_upload(upload_id)
        if upload.user_id != user.user_id and not user.has_role(UserRole.ADMIN):
            raise LookupError(f"upload {upload_id!r} not found")
        return upload

    def _owned_analysis(self, analysis_id: str, user):
        analysis = self.service.get_analysis(analysis_id)
        if analysis.user_id != user.user_id and not user.has_role(UserRole.ADMIN):
            raise LookupError(f"analysis {analysis_id!r} not found")
        return analysis

    # --- request/response recording -------------------------------------------
    def _failure_response(self, failed) -> ApiResponse:
        first = failed[0][0]
        status = {
            "authentication": ResponseStatus.UNAUTHORIZED,
            "authorization": ResponseStatus.FORBIDDEN,
        }.get(first, ResponseStatus.BAD_REQUEST)
        return ApiResponse(status, {"errors": [{"check": n, "detail": d} for n, d in failed]},
                           error_code=first)

    def _record(self, request: ApiRequest, request_id: str, status: RequestStatus, session, user,
                response: ApiResponse, created_at: str) -> None:
        params_fp = request.params_fingerprint()
        request_record = RequestRecord(
            request_id=request_id, operation=request.operation, api_version=request.api_version,
            user_id=getattr(user, "user_id", None), session_id=getattr(session, "session_id", None),
            params_fingerprint=params_fp, status=status, created_at=created_at)
        self.requests.put(request_record)

        body_fp = response.body_fingerprint()
        response_id = mint_identity("response", {"request_id": request_id,
                                                "response_key": body_fp}).id
        response_record = ResponseRecord(
            response_id=response_id, request_id=request_id, status=response.status,
            body_fingerprint=body_fp, error_code=response.error_code, created_at=created_at)
        self.responses.put(response_record)

        self.audit.append("api_request", {"request_id": request_id,
                                          "operation": request.operation.value,
                                          "status": status.value}, created_at=created_at)
        self.audit.append("api_response", {"response_id": response_id, "request_id": request_id,
                                           "status": response.status.value}, created_at=created_at)
        audit_head = self.audit.head
        self.registry.register(BackendRegistryRecord(
            entity_kind=EntityKind.REQUEST, entity_id=request_id, status=status.value,
            version=params_fp, owner=getattr(user, "user_id", None) or "anonymous",
            creation_date=created_at, audit_state=audit_head, lineage_id=self._api_lineage_id,
            user_id=getattr(user, "user_id", None), dependencies=()))
        self.registry.register(BackendRegistryRecord(
            entity_kind=EntityKind.RESPONSE, entity_id=response_id, status=response.status.value,
            version=body_fp, owner=getattr(user, "user_id", None) or "anonymous",
            creation_date=created_at, audit_state=audit_head, lineage_id=self._api_lineage_id,
            user_id=getattr(user, "user_id", None), dependencies=(request_id,)))


def _req_key(request: ApiRequest, seq: int) -> str:
    from ml.provenance import hash_obj
    return hash_obj({"params_fp": request.params_fingerprint(), "seq": seq})


__all__ = ["ApplicationAPI"]
