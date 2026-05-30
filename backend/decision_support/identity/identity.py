"""Deterministic decision-support identity generation.

An identity is ``"{kind}+{hash16}"`` — a sha256-derived digest of a canonical
payload (kind, identity version, content-defining components). Properties: stable,
deterministic, versioned, collision-resistant.

  * ``decision_context``  — derived from a case id.
  * ``evidence_bundle``   — derived from a context id.
  * ``risk_context``      — derived from a context id.
  * ``prioritization``    — derived from a context id.
  * ``guidance``          — derived from a context id.
  * ``decision_support``  — derived from a context id (the top-level record).
  * ``decision_report``   — derived from a report type + scope.

This is a separate minting authority from ``clinical_cases.identity`` (left
unchanged). It deliberately does **not** mint the bare ``decision`` kind, which the
case identity system reserves and blocks — V2-P6 introduces decision *support*
artifacts (context/evidence/risk/prioritization/guidance), never an autonomous
``decision``. The id *format* matches, so existing validators interoperate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import DECISION_IDENTITY_VERSION

_KINDS = ("decision_context", "evidence_bundle", "risk_context", "prioritization",
          "guidance", "decision_support", "decision_report")
_ID_RE = re.compile(
    r"^(decision_context|evidence_bundle|risk_context|prioritization|guidance|"
    r"decision_support|decision_report)\+[0-9a-f]{16}$")


class DecisionIdentityError(ValueError):
    """Raised when decision-support identity minting or validation fails."""


@dataclass(frozen=True)
class DecisionIdentity:
    id: str
    kind: str
    identity_version: str
    components: dict

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "identity_version": self.identity_version,
                "components": self.components}


def _mint(kind: str, components: Mapping[str, object]) -> DecisionIdentity:
    if kind not in _KINDS:
        raise DecisionIdentityError(f"unknown decision identity kind {kind!r}")
    payload = {"kind": kind, "identity_version": DECISION_IDENTITY_VERSION,
               "components": dict(components)}
    return DecisionIdentity(id=f"{kind}+{hash_obj(payload)}", kind=kind,
                            identity_version=DECISION_IDENTITY_VERSION, components=dict(components))


def mint_context(case_id: str) -> DecisionIdentity:
    if not case_id:
        raise DecisionIdentityError("case_id must be non-empty")
    return _mint("decision_context", {"case_id": case_id})


def mint_evidence_bundle(context_id: str) -> DecisionIdentity:
    return _mint("evidence_bundle", {"context_id": context_id})


def mint_risk_context(context_id: str) -> DecisionIdentity:
    return _mint("risk_context", {"context_id": context_id})


def mint_prioritization(context_id: str) -> DecisionIdentity:
    return _mint("prioritization", {"context_id": context_id})


def mint_guidance(context_id: str) -> DecisionIdentity:
    return _mint("guidance", {"context_id": context_id})


def mint_decision_support(context_id: str) -> DecisionIdentity:
    return _mint("decision_support", {"context_id": context_id})


def mint_report(report_type: str, scope: str) -> DecisionIdentity:
    if not report_type or not scope:
        raise DecisionIdentityError("report_type and scope must be non-empty")
    return _mint("decision_report", {"report_type": report_type, "scope": scope})


def parse_identity(id_str: str) -> tuple[str, str]:
    if not _ID_RE.match(id_str or ""):
        raise DecisionIdentityError(f"malformed identity string {id_str!r}")
    kind, digest = id_str.split("+", 1)
    return kind, digest


def validate_identity(id_str: str, expected_kind: Optional[str] = None) -> tuple[bool, str]:
    """Validate a decision-support identity string (+ optional kind)."""
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed identity {id_str!r}"
    kind = id_str.split("+", 1)[0]
    if expected_kind is not None and kind != expected_kind:
        return False, f"expected kind {expected_kind!r}, got {kind!r}"
    return True, "ok"
