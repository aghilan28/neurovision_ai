"""Deterministic intelligence-artifact identity generation.

An identity is ``"{kind}+{hash16}"`` — a sha256-derived digest of a canonical
payload (kind, identity version, content-defining components). Properties: stable,
deterministic, versioned, collision-resistant.

  * ``cohort``       — derived from a cohort *definition* (member kind + criteria).
  * ``analytics``    — derived from an analytics *scope*.
  * ``trend``        — derived from a trend *scope*.
  * ``quality``      — derived from a quality *scope*.
  * ``intel_report`` — derived from a report type + scope.

This is a separate minting authority from ``clinical_cases.identity`` and
``clinical_findings.identity`` (both left unchanged); it produces the same id
*format*, so existing format validators interoperate. The logical identity is the
*question asked* (definition/scope), never the *answer* (the computed result) —
so re-computing the same intelligence over evolved data yields the same id with a
new version (auditable), never an orphan artifact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import INTEL_IDENTITY_VERSION

_KINDS = ("cohort", "analytics", "trend", "quality", "intel_report")
_ID_RE = re.compile(r"^(cohort|analytics|trend|quality|intel_report)\+[0-9a-f]{16}$")


class IntelIdentityError(ValueError):
    """Raised when intelligence-artifact identity minting or validation fails."""


@dataclass(frozen=True)
class IntelIdentity:
    id: str
    kind: str
    identity_version: str
    components: dict

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "identity_version": self.identity_version,
                "components": self.components}


def _mint(kind: str, components: Mapping[str, object]) -> IntelIdentity:
    if kind not in _KINDS:
        raise IntelIdentityError(f"unknown intelligence identity kind {kind!r}")
    payload = {"kind": kind, "identity_version": INTEL_IDENTITY_VERSION,
               "components": dict(components)}
    return IntelIdentity(id=f"{kind}+{hash_obj(payload)}", kind=kind,
                         identity_version=INTEL_IDENTITY_VERSION, components=dict(components))


def mint_cohort(member_kind: str, criteria_payload: object, combinator: str) -> IntelIdentity:
    if not member_kind:
        raise IntelIdentityError("member_kind must be non-empty")
    return _mint("cohort", {"member_kind": member_kind, "criteria": criteria_payload,
                            "combinator": combinator})


def mint_analytics(scope: str) -> IntelIdentity:
    if not scope:
        raise IntelIdentityError("analytics scope must be non-empty")
    return _mint("analytics", {"scope": scope})


def mint_trend(scope: str) -> IntelIdentity:
    if not scope:
        raise IntelIdentityError("trend scope must be non-empty")
    return _mint("trend", {"scope": scope})


def mint_quality(scope: str) -> IntelIdentity:
    if not scope:
        raise IntelIdentityError("quality scope must be non-empty")
    return _mint("quality", {"scope": scope})


def mint_report(report_type: str, scope: str) -> IntelIdentity:
    if not report_type or not scope:
        raise IntelIdentityError("report_type and scope must be non-empty")
    return _mint("intel_report", {"report_type": report_type, "scope": scope})


def parse_identity(id_str: str) -> tuple[str, str]:
    if not _ID_RE.match(id_str or ""):
        raise IntelIdentityError(f"malformed identity string {id_str!r}")
    kind, digest = id_str.split("+", 1)
    return kind, digest


def validate_identity(id_str: str, expected_kind: Optional[str] = None) -> tuple[bool, str]:
    """Validate an intelligence identity string (+ optional kind)."""
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed identity {id_str!r}"
    kind = id_str.split("+", 1)[0]
    if expected_kind is not None and kind != expected_kind:
        return False, f"expected kind {expected_kind!r}, got {kind!r}"
    return True, "ok"
