"""Graph edge system (V3-P4).

Edge entities are defined alongside nodes in ``nodes.domain`` (one cohesive domain
module); this package re-exports the edge type for an explicit ``edges`` import
site, per the mandated subsystem layout.
"""

from __future__ import annotations

from ..nodes.domain import GraphEdge

__all__ = ["GraphEdge"]
