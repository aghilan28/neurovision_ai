"""Versioned API request/response contracts (P6-F).

In-process, structured contracts (no HTTP server, no networking, no serving
infrastructure — those are out of scope). An :class:`ApiRequest` names a closed
:class:`ApiOperation`, the API version, an optional bearer token, and a params dict; an
:class:`ApiResponse` carries a closed :class:`ResponseStatus`, a JSON-able body, and an
optional error code. ``describe_api`` builds the :class:`APIRecord` for the whole
surface (a documented, closed operation set).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..identity import mint_identity
from ..models.domain import APIRecord, ApiOperation, ResponseStatus
from ..version import API_V1

# Params that must never enter a fingerprint, a record, a report, or a log.
_SECRET_PARAM_KEYS = frozenset({"password", "content"})


@dataclass(frozen=True)
class ApiRequest:
    """A structured, versioned API request."""

    operation: ApiOperation
    params: dict = field(default_factory=dict)
    token: Optional[str] = None
    api_version: str = API_V1

    def redacted_params(self) -> dict:
        """A secret-free projection of the params (for fingerprints/records/logs)."""
        out = {}
        for k, v in (self.params or {}).items():
            if k in _SECRET_PARAM_KEYS:
                if k == "content" and isinstance(v, (bytes, bytearray)):
                    out["content_sha256"] = hash_obj({"len": len(v)})
                else:
                    out[k] = "<redacted>"
            else:
                out[k] = v
        return dict(sorted(out.items()))

    def params_fingerprint(self) -> str:
        return hash_obj({"operation": self.operation.value, "api_version": self.api_version,
                         "params": self.redacted_params()})


@dataclass(frozen=True)
class ApiResponse:
    """A structured API response."""

    status: ResponseStatus
    body: dict = field(default_factory=dict)
    error_code: Optional[str] = None
    api_version: str = API_V1

    @property
    def ok(self) -> bool:
        return self.status.is_success

    def body_fingerprint(self) -> str:
        return hash_obj({"status": self.status.value, "body": self.body,
                         "error_code": self.error_code})

    def to_dict(self) -> dict:
        return {"status": self.status.value, "body": self.body, "error_code": self.error_code,
                "api_version": self.api_version, "ok": self.ok}


def describe_api() -> APIRecord:
    """Build the documented, versioned API surface record (closed operation set)."""
    operations = tuple(ApiOperation)
    api_id = mint_identity("api", {"name": "neurovision-application-api",
                                   "api_version": API_V1}).id
    return APIRecord(
        api_id=api_id, name="neurovision-application-api", api_version=API_V1,
        operations=operations,
        description="In-process versioned application backend API exposing the governed "
                    "EEG upload -> analysis -> prediction/confidence/explanation use case "
                    "over the reused P1-P5 platform services.")


__all__ = ["ApiRequest", "ApiResponse", "describe_api", "ResponseStatus", "ApiOperation"]
