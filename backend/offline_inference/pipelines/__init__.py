"""``backend/offline_inference/pipelines`` — deterministic inference pipeline (V1-P7).

Holds the pinned ``PipelineConfig`` and its content-addressed pipeline signature.
The orchestrator builds the concrete stage list from this config; identical config
=> identical pipeline signature => reproducible inference.
"""

from __future__ import annotations

from .pipeline import PipelineConfig

__all__ = ["PipelineConfig"]
