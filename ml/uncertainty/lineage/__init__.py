"""``ml/uncertainty/lineage`` — uncertainty lineage helpers (V1-P6).

Reuses the ML layer's lineage machinery (``ml.lineage``) to create content-
addressed lineage records for uncertainty stages, linking each back to its parent
model-training and evaluation lineage. Every uncertainty output is therefore
traceable end-to-end (NR-11).
"""

from __future__ import annotations

from .lineage import make_uncertainty_lineage

__all__ = ["make_uncertainty_lineage"]
