"""Model routing — resolution, selection, and version selection (DRP3-C).

Resolves a request's ``model_ref`` to a single servable ``model_id`` from the serving
engine's catalog. Registry-aware and version-aware, deterministic (ties broken by
``model_id``):

- ``{"model_id": ...}`` → that exact model (must be loaded).
- ``{"architecture": ..., "version": ...}`` → that architecture at that exact version.
- ``{"architecture": ...}`` → the **latest loaded** version of that architecture
  (highest load ordinal; ``model_id`` tiebreak).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


class RoutingError(LookupError):
    """Raised when a model reference cannot be resolved to a loaded model."""


@dataclass(frozen=True)
class RoutingDecision:
    model_id: str
    architecture: str
    version: str
    strategy: str
    candidates: tuple[str, ...]

    def to_dict(self) -> dict:
        return {"model_id": self.model_id, "architecture": self.architecture,
                "version": self.version, "strategy": self.strategy,
                "candidates": list(self.candidates)}


class ModelRouter:
    """Pure resolution over an entry catalog ``{model_id: {architecture, version, ordinal}}``."""

    def resolve(self, model_ref: Mapping[str, object], catalog: Mapping[str, dict]) -> RoutingDecision:
        if not catalog:
            raise RoutingError("no models loaded in the serving catalog")
        model_id = model_ref.get("model_id")
        architecture = model_ref.get("architecture")
        version = model_ref.get("version")

        if model_id:
            if model_id not in catalog:
                raise RoutingError(f"model {model_id!r} is not loaded")
            e = catalog[model_id]
            return RoutingDecision(model_id=str(model_id), architecture=e["architecture"],
                                   version=e["version"], strategy="by_model_id",
                                   candidates=(str(model_id),))

        if architecture:
            cands = {m: e for m, e in catalog.items() if e["architecture"] == architecture}
            if version is not None:
                cands = {m: e for m, e in cands.items() if e["version"] == version}
                strategy = "by_architecture_version"
            else:
                strategy = "by_architecture_latest"
            if not cands:
                raise RoutingError(
                    f"no loaded model for architecture={architecture!r} version={version!r}")
            # latest = highest load ordinal, tie-broken by model_id (deterministic)
            chosen = max(sorted(cands), key=lambda m: cands[m]["ordinal"])
            e = cands[chosen]
            return RoutingDecision(model_id=chosen, architecture=e["architecture"],
                                   version=e["version"], strategy=strategy,
                                   candidates=tuple(sorted(cands)))

        raise RoutingError("model_ref must contain a model_id or an architecture")


__all__ = ["ModelRouter", "RoutingDecision", "RoutingError"]
