"""``backend/model_foundation/registry`` — dataset + model registries (P4-D/I).

No dataset or model exists outside its registry; silent overwrite of a version with
different content is rejected.
"""

from __future__ import annotations

from .registry import DatasetRegistry, ModelRegistry

__all__ = ["DatasetRegistry", "ModelRegistry"]
