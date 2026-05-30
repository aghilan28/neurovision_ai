"""Deterministic agent-artifact identity generation (V4-P5).

An agent identity is ``"agent+{hash16}"`` — a sha256-derived digest of a canonical
payload (kind, identity version, agent category, agent key). Because the digest is a
pure function of its inputs it is:

  * **Stable / deterministic** — same definition ⇒ same id, forever.
  * **Collision resistant** — sha256 digest space.
  * **Versioned** — the identity version is part of the hashed payload.
  * **Traceable** — the id is a function of *what the agent is* (category + key), not
    of any mutable lifecycle state, so re-declaring the same agent yields the same id
    with a new content version (auditable), never an orphan.

A relationship identity is ``"agentrel+{hash16}"`` and an assignment identity is
``"agentassign+{hash16}"``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import AGENT_IDENTITY_VERSION

_AGENT_ID_RE = re.compile(r"^agent\+[0-9a-f]{16}$")
_REL_ID_RE = re.compile(r"^agentrel\+[0-9a-f]{16}$")
_ASSIGN_ID_RE = re.compile(r"^agentassign\+[0-9a-f]{16}$")


class AgentIdentityError(ValueError):
    """Raised when agent identity minting or validation fails."""


@dataclass(frozen=True)
class AgentIdentity:
    id: str
    category: str
    agent_key: str
    identity_version: str = AGENT_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "category": self.category, "agent_key": self.agent_key,
                "identity_version": self.identity_version}


def mint_agent(category: str, agent_key: str) -> AgentIdentity:
    if not (category and agent_key):
        raise AgentIdentityError("category and agent_key must be non-empty")
    payload = {"kind": "agent", "identity_version": AGENT_IDENTITY_VERSION,
               "category": category, "agent_key": agent_key}
    return AgentIdentity(id=f"agent+{hash_obj(payload)}", category=category, agent_key=agent_key)


def mint_relationship(source_agent_id: str, relation: str, target_id: str) -> str:
    """A deterministic relationship identity ``agentrel+{hash16}``."""
    if not (source_agent_id and relation and target_id):
        raise AgentIdentityError("relationship requires source, relation, and target")
    payload = {"kind": "agentrel", "identity_version": AGENT_IDENTITY_VERSION,
               "source": source_agent_id, "relation": relation, "target": target_id}
    return f"agentrel+{hash_obj(payload)}"


def mint_assignment(agent_id: str, target_kind: str, target_id: str) -> str:
    """A deterministic assignment identity ``agentassign+{hash16}``."""
    if not (agent_id and target_kind and target_id):
        raise AgentIdentityError("assignment requires agent, target_kind, and target")
    payload = {"kind": "agentassign", "identity_version": AGENT_IDENTITY_VERSION,
               "agent": agent_id, "target_kind": target_kind, "target": target_id}
    return f"agentassign+{hash_obj(payload)}"


def validate_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _AGENT_ID_RE.match(id_str):
        return False, f"malformed agent identity {id_str!r}"
    return True, "ok"


def validate_relationship_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _REL_ID_RE.match(id_str):
        return False, f"malformed agent-relationship identity {id_str!r}"
    return True, "ok"


def validate_assignment_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ASSIGN_ID_RE.match(id_str):
        return False, f"malformed agent-assignment identity {id_str!r}"
    return True, "ok"
