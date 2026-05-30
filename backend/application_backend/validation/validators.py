"""Request validation + authorization policy (P6-G).

Pure, structured checks the API layer runs on every inbound request:
authentication, authorization, request structure, file structure. Each check returns a
``(name, passed, detail)`` tuple (never raises for bad input). The authorization policy
maps each closed :class:`ApiOperation` to the roles permitted to invoke it.
"""

from __future__ import annotations


from ..models.domain import ApiOperation, UserRole, UserStatus

# Operations that require no authenticated session.
PUBLIC_OPERATIONS = frozenset({ApiOperation.REGISTER_USER, ApiOperation.LOGIN})

# Operations that mutate platform state (require a write-capable role).
WRITE_OPERATIONS = frozenset({ApiOperation.UPLOAD_EEG, ApiOperation.START_ANALYSIS})

_WRITE_ROLES = frozenset({UserRole.ADMIN, UserRole.CLINICIAN, UserRole.RESEARCHER})
_ALL_ROLES = frozenset(UserRole)

# operation -> the roles permitted to invoke it (only consulted for authenticated ops).
OPERATION_ROLES: dict[ApiOperation, frozenset] = {
    ApiOperation.LOGOUT: _ALL_ROLES,
    ApiOperation.UPLOAD_EEG: _WRITE_ROLES,
    ApiOperation.START_ANALYSIS: _WRITE_ROLES,
    ApiOperation.LIST_EEG: _ALL_ROLES,
    ApiOperation.RETRIEVE_EEG: _ALL_ROLES,
    ApiOperation.RETRIEVE_PREDICTION: _ALL_ROLES,
    ApiOperation.RETRIEVE_CONFIDENCE: _ALL_ROLES,
    ApiOperation.RETRIEVE_EXPLANATION: _ALL_ROLES,
    ApiOperation.LIST_ANALYSIS_HISTORY: _ALL_ROLES,
    ApiOperation.LIST_REPORTS: _ALL_ROLES,
}

# operation -> required request parameter keys.
REQUIRED_PARAMS: dict[ApiOperation, tuple[str, ...]] = {
    ApiOperation.REGISTER_USER: ("username", "password"),
    ApiOperation.LOGIN: ("username", "password"),
    ApiOperation.LOGOUT: (),
    ApiOperation.UPLOAD_EEG: ("filename", "content"),
    ApiOperation.LIST_EEG: (),
    ApiOperation.RETRIEVE_EEG: ("upload_id",),
    ApiOperation.START_ANALYSIS: ("upload_id",),
    ApiOperation.RETRIEVE_PREDICTION: ("analysis_id",),
    ApiOperation.RETRIEVE_CONFIDENCE: ("analysis_id",),
    ApiOperation.RETRIEVE_EXPLANATION: ("analysis_id",),
    ApiOperation.LIST_ANALYSIS_HISTORY: (),
    ApiOperation.LIST_REPORTS: ("analysis_id",),
}


def is_public(operation: ApiOperation) -> bool:
    return operation in PUBLIC_OPERATIONS


class RequestValidator:
    """Build-time request checks (structured results, never exceptions)."""

    def authentication(self, operation: ApiOperation, session) -> tuple[str, bool, dict]:
        if is_public(operation):
            return ("authentication", True, {"public": True})
        ok = session is not None
        return ("authentication", bool(ok),
                {"public": False, "session": getattr(session, "session_id", None)})

    def authorization(self, operation: ApiOperation, user) -> tuple[str, bool, dict]:
        if is_public(operation):
            return ("authorization", True, {"public": True})
        if user is None:
            return ("authorization", False, {"reason": "no_user"})
        if user.status != UserStatus.ACTIVE:
            return ("authorization", False, {"reason": "user_not_active"})
        allowed = OPERATION_ROLES.get(operation, frozenset())
        ok = any(r in allowed for r in user.roles)
        return ("authorization", bool(ok),
                {"roles": sorted(r.value for r in user.roles),
                 "allowed": sorted(r.value for r in allowed)})

    def request_structure(self, operation: ApiOperation, params: dict) -> tuple[str, bool, dict]:
        required = REQUIRED_PARAMS.get(operation, ())
        missing = [k for k in required if k not in (params or {}) or params.get(k) in (None, "")]
        return ("request_structure", len(missing) == 0, {"missing": missing})

    def file_structure(self, operation: ApiOperation, params: dict) -> tuple[str, bool, dict]:
        if operation != ApiOperation.UPLOAD_EEG:
            return ("file_structure", True, {"applies": False})
        content = (params or {}).get("content")
        filename = (params or {}).get("filename")
        ok = (isinstance(content, (bytes, bytearray)) and len(content) > 0
              and isinstance(filename, str) and filename != "")
        return ("file_structure", bool(ok),
                {"applies": True, "size_bytes": len(content) if isinstance(content, (bytes, bytearray)) else 0})

    def checks(self, *, operation: ApiOperation, params: dict, session, user) -> list[tuple]:
        return [
            self.authentication(operation, session),
            self.authorization(operation, user),
            self.request_structure(operation, params),
            self.file_structure(operation, params),
        ]


__all__ = [
    "RequestValidator", "is_public", "PUBLIC_OPERATIONS", "WRITE_OPERATIONS",
    "OPERATION_ROLES", "REQUIRED_PARAMS",
]
