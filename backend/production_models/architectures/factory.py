"""Production architecture factory (DRP2-C).

A single entry point that builds any of the five production-candidate architectures
behind a uniform contract. The standard four delegate to the reused reference models;
``HYBRID_EEG`` builds the native :class:`HybridModel`. Registry-/benchmark-aware: callers
treat the returned object uniformly.
"""

from __future__ import annotations

from ..models.domain import ProductionArchitecture
from .models import HybridModel, ReferenceArchitectureWrapper, REFERENCE_OF

# The closed, ordered set of production-candidate architectures (DRP2-C).
PRODUCTION_ARCHITECTURES: tuple[ProductionArchitecture, ...] = (
    ProductionArchitecture.EEGNET,
    ProductionArchitecture.DEEPCONVNET,
    ProductionArchitecture.TEMPORAL_CNN,
    ProductionArchitecture.TRANSFORMER_EEG,
    ProductionArchitecture.HYBRID_EEG,
)


class ArchitectureError(ValueError):
    """Raised when an unknown production architecture is requested."""


def build_production_model(architecture: ProductionArchitecture, n_classes: int, *, seed: int,
                           hyperparameters: dict | None = None):
    """Build a production-candidate model exposing the uniform architecture contract."""
    if architecture not in set(ProductionArchitecture):
        raise ArchitectureError(f"unknown production architecture {architecture!r}")
    if architecture is ProductionArchitecture.HYBRID_EEG:
        return HybridModel(n_classes, seed=seed, hyperparameters=hyperparameters)
    return ReferenceArchitectureWrapper(architecture, n_classes, seed=seed,
                                        hyperparameters=hyperparameters)


def architecture_catalog() -> list[dict]:
    """A deterministic description of every supported production architecture."""
    catalog = []
    for arch in PRODUCTION_ARCHITECTURES:
        ref = REFERENCE_OF[arch]
        catalog.append({
            "architecture": arch.value,
            "family": "hybrid" if ref is None else "reference_wrapper",
            "reference_architecture": ref.value if ref is not None else None,
        })
    return catalog
