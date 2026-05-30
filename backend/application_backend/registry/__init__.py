"""``backend/application_backend/registry`` — the application registry (P6-I).

One discoverable index of every application entity (users, sessions, uploads, requests,
responses, workflows, analyses, API), with no orphan records (every entry references its
audit head + lineage node).
"""

from __future__ import annotations

from .registry import BackendRegistry, RegistryError

__all__ = ["BackendRegistry", "RegistryError"]
