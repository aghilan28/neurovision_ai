"""Production architecture framework (DRP2-C)."""

from __future__ import annotations

from .models import HybridModel, ReferenceArchitectureWrapper, REFERENCE_OF
from .factory import (
    PRODUCTION_ARCHITECTURES, ArchitectureError, architecture_catalog, build_production_model,
)

__all__ = [
    "HybridModel", "ReferenceArchitectureWrapper", "REFERENCE_OF", "PRODUCTION_ARCHITECTURES",
    "ArchitectureError", "architecture_catalog", "build_production_model",
]
