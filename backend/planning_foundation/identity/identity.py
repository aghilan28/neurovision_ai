"""Deterministic plan-artifact identity generation (V4-P3).

A plan identity is ``"plan+{hash16}"`` — a sha256-derived digest of a canonical
payload (kind, identity version, plan category, source goal id, plan key). Because
the digest is a pure function of its inputs it is:

  * **Stable / deterministic** — same definition ⇒ same id, forever.
  * **Collision resistant** — sha256 digest space.
  * **Versioned** — the identity version is part of the hashed payload.
  * **Traceable** — the id is a function of *what the plan is* (category + source
    goal + key), not of any mutable lifecycle state, so re-declaring the same plan
    yields the same id with a new content version (auditable), never an orphan.

A relationship identity is ``"planrel+{hash16}"`` (kind + endpoints + relation).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import PLAN_IDENTITY_VERSION

_PLAN_ID_RE = re.compile(r"^plan\+[0-9a-f]{16}$")
_REL_ID_RE = re.compile(r"^planrel\+[0-9a-f]{16}$")


class PlanIdentityError(ValueError):
    """Raised when plan identity minting or validation fails."""


@dataclass(frozen=True)
class PlanIdentity:
    id: str
    category: str
    source_goal_id: str
    plan_key: str
    identity_version: str = PLAN_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "category": self.category, "source_goal_id": self.source_goal_id,
                "plan_key": self.plan_key, "identity_version": self.identity_version}


def mint_plan(category: str, source_goal_id: str, plan_key: str) -> PlanIdentity:
    if not (category and source_goal_id and plan_key):
        raise PlanIdentityError("category, source_goal_id, and plan_key must be non-empty")
    payload = {"kind": "plan", "identity_version": PLAN_IDENTITY_VERSION,
               "category": category, "source_goal_id": source_goal_id, "plan_key": plan_key}
    return PlanIdentity(id=f"plan+{hash_obj(payload)}", category=category,
                        source_goal_id=source_goal_id, plan_key=plan_key)


def mint_relationship(source_plan_id: str, relation: str, target_id: str) -> str:
    """A deterministic relationship identity ``planrel+{hash16}``."""
    if not (source_plan_id and relation and target_id):
        raise PlanIdentityError("relationship requires source, relation, and target")
    payload = {"kind": "planrel", "identity_version": PLAN_IDENTITY_VERSION,
               "source": source_plan_id, "relation": relation, "target": target_id}
    return f"planrel+{hash_obj(payload)}"


def validate_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _PLAN_ID_RE.match(id_str):
        return False, f"malformed plan identity {id_str!r}"
    return True, "ok"


def validate_relationship_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _REL_ID_RE.match(id_str):
        return False, f"malformed plan-relationship identity {id_str!r}"
    return True, "ok"
