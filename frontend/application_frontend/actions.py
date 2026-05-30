"""Shared controller action result (stdlib only).

Every UI controller returns an :class:`ActionResult`: did the action succeed, which page
to show next, a flash (level, message) for the user, and any structured data the page
needs. Controllers contain no business logic — they call the gateway and shape results.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    page: str
    level: str = "info"               # info | success | warning | error
    message: str = ""
    data: dict = field(default_factory=dict)
    field_errors: tuple = ()

    def to_dict(self) -> dict:
        return {"ok": self.ok, "page": self.page, "level": self.level, "message": self.message,
                "data": self.data, "field_errors": list(self.field_errors)}


def from_api_error(response: dict, *, page: str) -> ActionResult:
    """Map an unsuccessful API response dict to a friendly ActionResult."""
    body = response.get("body") or {}
    status = response.get("status", "error")
    message = body.get("error") or body.get("reason") or f"Request failed ({status})."
    if isinstance(body.get("errors"), list) and body["errors"]:
        parts = [str(e.get("check") or e.get("detail") or "") if isinstance(e, dict) else str(e)
                 for e in body["errors"]]
        message = "; ".join(p for p in parts if p) or message
    return ActionResult(ok=False, page=page, level="error", message=message,
                        data={"status": status, "error_code": response.get("error_code")})


__all__ = ["ActionResult", "from_api_error"]
