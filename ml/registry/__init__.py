"""``ml/registry`` — the model registry (V1-P5).

No model may exist outside the registry. Every trained model is registered with
its full version coordinates, lineage id, owner and status, so the platform can
always answer "what is this model, where did it come from, and is it allowed to be
used?" (AP-5 / AP-8 / AP-9).
"""

from __future__ import annotations

from .model_registry import ModelRecord, ModelRegistry, ModelStatus

__all__ = ["ModelRecord", "ModelRegistry", "ModelStatus"]
