"""Deterministic task-artifact identity generation (V4-P4).

A task identity is ``"task+{hash16}"`` — a sha256-derived digest of a canonical
payload (kind, identity version, task category, source plan id, task key). Because
the digest is a pure function of its inputs it is:

  * **Stable / deterministic** — same definition ⇒ same id, forever.
  * **Collision resistant** — sha256 digest space.
  * **Versioned** — the identity version is part of the hashed payload.
  * **Traceable** — the id is a function of *what the task is* (category + source plan
    + key), not of any mutable lifecycle state, so re-declaring the same task yields
    the same id with a new content version (auditable), never an orphan.

A relationship identity is ``"taskrel+{hash16}"`` (kind + endpoints + relation).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import TASK_IDENTITY_VERSION

_TASK_ID_RE = re.compile(r"^task\+[0-9a-f]{16}$")
_REL_ID_RE = re.compile(r"^taskrel\+[0-9a-f]{16}$")


class TaskIdentityError(ValueError):
    """Raised when task identity minting or validation fails."""


@dataclass(frozen=True)
class TaskIdentity:
    id: str
    category: str
    source_plan_id: str
    task_key: str
    identity_version: str = TASK_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "category": self.category, "source_plan_id": self.source_plan_id,
                "task_key": self.task_key, "identity_version": self.identity_version}


def mint_task(category: str, source_plan_id: str, task_key: str) -> TaskIdentity:
    if not (category and source_plan_id and task_key):
        raise TaskIdentityError("category, source_plan_id, and task_key must be non-empty")
    payload = {"kind": "task", "identity_version": TASK_IDENTITY_VERSION,
               "category": category, "source_plan_id": source_plan_id, "task_key": task_key}
    return TaskIdentity(id=f"task+{hash_obj(payload)}", category=category,
                        source_plan_id=source_plan_id, task_key=task_key)


def mint_relationship(source_task_id: str, relation: str, target_id: str) -> str:
    """A deterministic relationship identity ``taskrel+{hash16}``."""
    if not (source_task_id and relation and target_id):
        raise TaskIdentityError("relationship requires source, relation, and target")
    payload = {"kind": "taskrel", "identity_version": TASK_IDENTITY_VERSION,
               "source": source_task_id, "relation": relation, "target": target_id}
    return f"taskrel+{hash_obj(payload)}"


def validate_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _TASK_ID_RE.match(id_str):
        return False, f"malformed task identity {id_str!r}"
    return True, "ok"


def validate_relationship_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _REL_ID_RE.match(id_str):
        return False, f"malformed task-relationship identity {id_str!r}"
    return True, "ok"
