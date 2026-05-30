"""Deterministic policy/constraint/evaluation identity generation (V4-P2).

Identities are content-addressed digests of a canonical payload:

  * policy      ``"policy+{hash16}"``      — kind + identity version + category + key
  * constraint  ``"constraint+{hash16}"``  — kind + identity version + ctype + subject + key
  * evaluation  ``"policyeval+{hash16}"``   — kind + identity version + policy id + request sig

Because each digest is a pure function of its inputs it is stable, deterministic,
collision resistant, versioned, and traceable. An evaluation's id is a function of
*the policy + the exact request*, so the same request against the same policy
reproduces the same evaluation id (deterministic, explainable, auditable).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import POLICY_IDENTITY_VERSION

_POLICY_ID_RE = re.compile(r"^policy\+[0-9a-f]{16}$")
_CONSTRAINT_ID_RE = re.compile(r"^constraint\+[0-9a-f]{16}$")
_EVAL_ID_RE = re.compile(r"^policyeval\+[0-9a-f]{16}$")


class PolicyIdentityError(ValueError):
    """Raised when policy identity minting or validation fails."""


@dataclass(frozen=True)
class PolicyIdentity:
    id: str
    category: str
    policy_key: str
    identity_version: str = POLICY_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "category": self.category, "policy_key": self.policy_key,
                "identity_version": self.identity_version}


def mint_policy(category: str, policy_key: str) -> PolicyIdentity:
    if not category or not policy_key:
        raise PolicyIdentityError("category and policy_key must be non-empty")
    payload = {"kind": "policy", "identity_version": POLICY_IDENTITY_VERSION,
               "category": category, "policy_key": policy_key}
    return PolicyIdentity(id=f"policy+{hash_obj(payload)}", category=category,
                          policy_key=policy_key)


def mint_constraint(constraint_type: str, subject_kind: str, constraint_key: str) -> str:
    if not (constraint_type and subject_kind and constraint_key):
        raise PolicyIdentityError("constraint requires type, subject_kind, and key")
    payload = {"kind": "constraint", "identity_version": POLICY_IDENTITY_VERSION,
               "constraint_type": constraint_type, "subject_kind": subject_kind,
               "constraint_key": constraint_key}
    return f"constraint+{hash_obj(payload)}"


def mint_evaluation(policy_id: str, request_signature: str) -> str:
    if not (policy_id and request_signature):
        raise PolicyIdentityError("evaluation requires a policy id and a request signature")
    payload = {"kind": "policyeval", "identity_version": POLICY_IDENTITY_VERSION,
               "policy_id": policy_id, "request_signature": request_signature}
    return f"policyeval+{hash_obj(payload)}"


def validate_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _POLICY_ID_RE.match(id_str):
        return False, f"malformed policy identity {id_str!r}"
    return True, "ok"


def validate_constraint_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _CONSTRAINT_ID_RE.match(id_str):
        return False, f"malformed constraint identity {id_str!r}"
    return True, "ok"


def validate_evaluation_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _EVAL_ID_RE.match(id_str):
        return False, f"malformed evaluation identity {id_str!r}"
    return True, "ok"
