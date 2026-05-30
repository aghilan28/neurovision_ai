"""Deterministic workflow-artifact identity generation (V3-P3).

A workflow identity is ``"workflow+{hash16}"`` — a sha256 digest of a canonical
payload (kind, identity version, workflow type, subject id). Stable, deterministic,
collision resistant, versioned. The logical identity is the *workflow definition*
(type + subject), so re-deriving the same workflow over more events yields the same
id with a new content version (auditable), never an orphan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import WORKFLOW_IDENTITY_VERSION

_ID_RE = re.compile(r"^workflow\+[0-9a-f]{16}$")


class WorkflowIdentityError(ValueError):
    """Raised when workflow identity minting or validation fails."""


@dataclass(frozen=True)
class WorkflowIdentity:
    id: str
    workflow_type: str
    subject_id: str
    identity_version: str = WORKFLOW_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "workflow_type": self.workflow_type, "subject_id": self.subject_id,
                "identity_version": self.identity_version}


def mint_workflow(workflow_type: str, subject_id: str) -> WorkflowIdentity:
    if not workflow_type or not subject_id:
        raise WorkflowIdentityError("workflow_type and subject_id must be non-empty")
    payload = {"kind": "workflow", "identity_version": WORKFLOW_IDENTITY_VERSION,
               "workflow_type": workflow_type, "subject_id": subject_id}
    return WorkflowIdentity(id=f"workflow+{hash_obj(payload)}", workflow_type=workflow_type,
                            subject_id=subject_id)


def validate_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed workflow identity {id_str!r}"
    return True, "ok"
