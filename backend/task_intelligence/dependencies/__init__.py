"""Task dependency analysis package (V4-P4)."""

from __future__ import annotations

from .dependencies import build_adjacency, has_cycle, topological_order, dependency_summary

__all__ = ["build_adjacency", "has_cycle", "topological_order", "dependency_summary"]
