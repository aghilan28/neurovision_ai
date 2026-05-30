"""``backend/inference_foundation/explainability`` — structured explanations (P5-G).

Occlusion-based feature contributions/importance, band importance, input-derived
channel importance, decision factors, and a model-attribution summary. Structured
outputs only — no images, no UI, no dashboards.
"""

from __future__ import annotations

from .explainability import ExplainabilityEngine

__all__ = ["ExplainabilityEngine"]
