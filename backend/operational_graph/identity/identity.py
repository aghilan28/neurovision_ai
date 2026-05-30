"""Deterministic graph-artifact identity generation (V3-P4).

Identities are content-addressed and typed by prefix:

  * ``gnode+{hash16}``  — derived from (node_type, source_id).
  * ``gedge+{hash16}``  — derived from (edge_type, source_node, target_node).
  * ``gproj+{hash16}``  — derived from (projection_type, scope).

Stable, deterministic, collision resistant, versioned. A node's identity is the
source entity it represents, so the graph never invents identity (no graph-only
truth): the same source always maps to the same node.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import GRAPH_IDENTITY_VERSION

_NODE_RE = re.compile(r"^gnode\+[0-9a-f]{16}$")
_EDGE_RE = re.compile(r"^gedge\+[0-9a-f]{16}$")
_PROJ_RE = re.compile(r"^gproj\+[0-9a-f]{16}$")


class GraphIdentityError(ValueError):
    """Raised when graph identity minting or validation fails."""


@dataclass(frozen=True)
class GraphIdentity:
    id: str
    kind: str            # gnode | gedge | gproj
    identity_version: str = GRAPH_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "identity_version": self.identity_version}


def mint_node(node_type: str, source_id: str) -> GraphIdentity:
    if not node_type or not source_id:
        raise GraphIdentityError("node_type and source_id must be non-empty")
    payload = {"kind": "gnode", "identity_version": GRAPH_IDENTITY_VERSION,
               "node_type": node_type, "source_id": source_id}
    return GraphIdentity(id=f"gnode+{hash_obj(payload)}", kind="gnode")


def mint_edge(edge_type: str, source_node: str, target_node: str) -> GraphIdentity:
    if not edge_type or not source_node or not target_node:
        raise GraphIdentityError("edge_type and endpoints must be non-empty")
    payload = {"kind": "gedge", "identity_version": GRAPH_IDENTITY_VERSION,
               "edge_type": edge_type, "source_node": source_node, "target_node": target_node}
    return GraphIdentity(id=f"gedge+{hash_obj(payload)}", kind="gedge")


def mint_projection(projection_type: str, scope: str) -> GraphIdentity:
    if not projection_type or not scope:
        raise GraphIdentityError("projection_type and scope must be non-empty")
    payload = {"kind": "gproj", "identity_version": GRAPH_IDENTITY_VERSION,
               "projection_type": projection_type, "scope": scope}
    return GraphIdentity(id=f"gproj+{hash_obj(payload)}", kind="gproj")


def validate_node_id(id_str: str) -> tuple[bool, str]:
    return (bool(isinstance(id_str, str) and _NODE_RE.match(id_str)),
            "ok" if isinstance(id_str, str) and _NODE_RE.match(id_str) else f"malformed node id {id_str!r}")


def validate_edge_id(id_str: str) -> tuple[bool, str]:
    return (bool(isinstance(id_str, str) and _EDGE_RE.match(id_str)),
            "ok" if isinstance(id_str, str) and _EDGE_RE.match(id_str) else f"malformed edge id {id_str!r}")


def validate_projection_id(id_str: str) -> tuple[bool, str]:
    return (bool(isinstance(id_str, str) and _PROJ_RE.match(id_str)),
            "ok" if isinstance(id_str, str) and _PROJ_RE.match(id_str) else f"malformed projection id {id_str!r}")
