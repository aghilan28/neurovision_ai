"""Deterministic goal-artifact identity generation (V4-P1).

A goal identity is ``"goal+{hash16}"`` — a sha256-derived digest of a canonical
payload (kind, identity version, goal category, definition key). Because the digest
is a pure function of its inputs it is:

  * **Stable / deterministic** — same definition ⇒ same id, forever.
  * **Collision resistant** — sha256 digest space.
  * **Versioned** — the identity version is part of the hashed payload.
  * **Traceable** — the id is a function of *what the goal is* (category + definition
    key), not of any mutable lifecycle state, so re-declaring the same goal yields
    the same id with a new content version (auditable), never an orphan.

A relationship identity is ``"goalrel+{hash16}"`` (kind + endpoints + relation).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import GOAL_IDENTITY_VERSION

_GOAL_ID_RE = re.compile(r"^goal\+[0-9a-f]{16}$")
_REL_ID_RE = re.compile(r"^goalrel\+[0-9a-f]{16}$")


class GoalIdentityError(ValueError):
    """Raised when goal identity minting or validation fails."""


@dataclass(frozen=True)
class GoalIdentity:
    id: str
    category: str
    definition_key: str
    identity_version: str = GOAL_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "category": self.category, "definition_key": self.definition_key,
                "identity_version": self.identity_version}


def mint_goal(category: str, definition_key: str) -> GoalIdentity:
    if not category or not definition_key:
        raise GoalIdentityError("category and definition_key must be non-empty")
    payload = {"kind": "goal", "identity_version": GOAL_IDENTITY_VERSION,
               "category": category, "definition_key": definition_key}
    return GoalIdentity(id=f"goal+{hash_obj(payload)}", category=category,
                        definition_key=definition_key)


def mint_relationship(source_goal_id: str, relation: str, target_id: str) -> str:
    """A deterministic relationship identity ``goalrel+{hash16}``."""
    if not (source_goal_id and relation and target_id):
        raise GoalIdentityError("relationship requires source, relation, and target")
    payload = {"kind": "goalrel", "identity_version": GOAL_IDENTITY_VERSION,
               "source": source_goal_id, "relation": relation, "target": target_id}
    return f"goalrel+{hash_obj(payload)}"


def validate_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _GOAL_ID_RE.match(id_str):
        return False, f"malformed goal identity {id_str!r}"
    return True, "ok"


def validate_relationship_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _REL_ID_RE.match(id_str):
        return False, f"malformed goal-relationship identity {id_str!r}"
    return True, "ok"
