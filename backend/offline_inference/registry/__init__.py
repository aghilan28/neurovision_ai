"""``backend/offline_inference/registry`` — the inference registry (V1-P7).

No inference may exist outside the registry. Every inference is registered with its
full version coordinates (pipeline/dataset/preprocessing/model/evaluation/
calibration/conformal/output/artifact/lineage versions) and its lineage id.
"""

from __future__ import annotations

from .registry import InferenceRecord, InferenceRegistry

__all__ = ["InferenceRecord", "InferenceRegistry"]
