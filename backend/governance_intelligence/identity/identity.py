"""Deterministic governance-intelligence identity generation (V4-P7).

Every governance-intelligence artifact has a content-derived identity — a
sha256-derived digest of a canonical payload. Because the digest is a pure function
of its inputs it is stable/deterministic, collision-resistant, versioned (the
identity version is part of the hashed payload), and traceable.

Identities:
  * intelligence : ``govintel+{hash16}``   — an aggregate governance-intelligence record
  * approval     : ``govapproval+{hash16}`` — an approval-intelligence record
  * violation    : ``govviolation+{hash16}``— a violation record
  * escalation   : ``govescalation+{hash16}``— an escalation record
  * risk         : ``govrisk+{hash16}``     — a governance-risk record
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import GOVERNANCE_IDENTITY_VERSION

_INTEL_ID_RE = re.compile(r"^govintel\+[0-9a-f]{16}$")
_APPROVAL_ID_RE = re.compile(r"^govapproval\+[0-9a-f]{16}$")
_VIOLATION_ID_RE = re.compile(r"^govviolation\+[0-9a-f]{16}$")
_ESCALATION_ID_RE = re.compile(r"^govescalation\+[0-9a-f]{16}$")
_RISK_ID_RE = re.compile(r"^govrisk\+[0-9a-f]{16}$")


class GovernanceIdentityError(ValueError):
    """Raised when governance-intelligence identity minting or validation fails."""


@dataclass(frozen=True)
class GovernanceIntelligenceIdentity:
    id: str
    scope: str
    identity_version: str = GOVERNANCE_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "scope": self.scope, "identity_version": self.identity_version}


def mint_intelligence(scope: str, signature: str) -> GovernanceIntelligenceIdentity:
    if not (scope and signature):
        raise GovernanceIdentityError("scope and signature must be non-empty")
    payload = {"kind": "govintel", "identity_version": GOVERNANCE_IDENTITY_VERSION,
               "scope": scope, "signature": signature}
    return GovernanceIntelligenceIdentity(id=f"govintel+{hash_obj(payload)}", scope=scope)


def mint_approval(entity_kind: str, entity_id: str) -> str:
    if not (entity_kind and entity_id):
        raise GovernanceIdentityError("approval requires entity_kind and entity_id")
    payload = {"kind": "govapproval", "identity_version": GOVERNANCE_IDENTITY_VERSION,
               "entity_kind": entity_kind, "entity_id": entity_id}
    return f"govapproval+{hash_obj(payload)}"


def mint_violation(entity_kind: str, entity_id: str, violation_type: str) -> str:
    if not (entity_kind and entity_id and violation_type):
        raise GovernanceIdentityError("violation requires entity_kind, entity_id, type")
    payload = {"kind": "govviolation", "identity_version": GOVERNANCE_IDENTITY_VERSION,
               "entity_kind": entity_kind, "entity_id": entity_id, "type": violation_type}
    return f"govviolation+{hash_obj(payload)}"


def mint_escalation(entity_kind: str, entity_id: str) -> str:
    if not (entity_kind and entity_id):
        raise GovernanceIdentityError("escalation requires entity_kind and entity_id")
    payload = {"kind": "govescalation", "identity_version": GOVERNANCE_IDENTITY_VERSION,
               "entity_kind": entity_kind, "entity_id": entity_id}
    return f"govescalation+{hash_obj(payload)}"


def mint_risk(dimension: str, entity_kind: str, entity_id: str) -> str:
    if not (dimension and entity_kind and entity_id):
        raise GovernanceIdentityError("risk requires dimension, entity_kind, entity_id")
    payload = {"kind": "govrisk", "identity_version": GOVERNANCE_IDENTITY_VERSION,
               "dimension": dimension, "entity_kind": entity_kind, "entity_id": entity_id}
    return f"govrisk+{hash_obj(payload)}"


def validate_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _INTEL_ID_RE.match(id_str):
        return False, f"malformed governance-intelligence identity {id_str!r}"
    return True, "ok"


def validate_approval_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _APPROVAL_ID_RE.match(id_str):
        return False, f"malformed approval identity {id_str!r}"
    return True, "ok"


def validate_violation_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _VIOLATION_ID_RE.match(id_str):
        return False, f"malformed violation identity {id_str!r}"
    return True, "ok"


def validate_escalation_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ESCALATION_ID_RE.match(id_str):
        return False, f"malformed escalation identity {id_str!r}"
    return True, "ok"


def validate_risk_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _RISK_ID_RE.match(id_str):
        return False, f"malformed risk identity {id_str!r}"
    return True, "ok"
