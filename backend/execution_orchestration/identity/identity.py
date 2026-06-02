"""Deterministic execution-artifact identity generation (V4-P6).

An execution identity is ``"execution+{hash16}"`` — a sha256-derived digest of a
canonical payload (kind, identity version, source task id, agent assignment id,
execution key). Because the digest is a pure function of its inputs it is:

  * **Stable / deterministic** — same definition ⇒ same id, forever.
  * **Collision resistant** — sha256 digest space.
  * **Versioned** — the identity version is part of the hashed payload.
  * **Traceable** — the id is a function of *what the execution coordinates* (the task
    + the approved agent assignment), not of any mutable lifecycle state.

A relationship identity is ``"execrel+{hash16}"``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import EXECUTION_IDENTITY_VERSION

_EXEC_ID_RE = re.compile(r"^execution\+[0-9a-f]{16}$")
_REL_ID_RE = re.compile(r"^execrel\+[0-9a-f]{16}$")


class ExecutionIdentityError(ValueError):
    """Raised when execution identity minting or validation fails."""


@dataclass(frozen=True)
class ExecutionIdentity:
    id: str
    source_task_id: str
    assignment_id: str
    execution_key: str
    identity_version: str = EXECUTION_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "source_task_id": self.source_task_id,
                "assignment_id": self.assignment_id, "execution_key": self.execution_key,
                "identity_version": self.identity_version}


def mint_execution(source_task_id: str, assignment_id: str, execution_key: str
                   ) -> ExecutionIdentity:
    if not (source_task_id and assignment_id and execution_key):
        raise ExecutionIdentityError(
            "source_task_id, assignment_id, and execution_key must be non-empty")
    payload = {"kind": "execution", "identity_version": EXECUTION_IDENTITY_VERSION,
               "source_task_id": source_task_id, "assignment_id": assignment_id,
               "execution_key": execution_key}
    return ExecutionIdentity(id=f"execution+{hash_obj(payload)}", source_task_id=source_task_id,
                             assignment_id=assignment_id, execution_key=execution_key)


def mint_relationship(source_execution_id: str, relation: str, target_id: str) -> str:
    """A deterministic relationship identity ``execrel+{hash16}``."""
    if not (source_execution_id and relation and target_id):
        raise ExecutionIdentityError("relationship requires source, relation, and target")
    payload = {"kind": "execrel", "identity_version": EXECUTION_IDENTITY_VERSION,
               "source": source_execution_id, "relation": relation, "target": target_id}
    return f"execrel+{hash_obj(payload)}"


def validate_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _EXEC_ID_RE.match(id_str):
        return False, f"malformed execution identity {id_str!r}"
    return True, "ok"


def validate_relationship_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _REL_ID_RE.match(id_str):
        return False, f"malformed execution-relationship identity {id_str!r}"
    return True, "ok"
