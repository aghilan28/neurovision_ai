"""``backend/offline_inference/lineage`` — inference lineage (V1-P7).

Reuses the ML layer's content-addressed lineage (``ml.lineage``) to record an
``inference`` lineage node that pins the full version bundle and links to its
parent model-training / evaluation / uncertainty lineage, so every inference output
is reproducible and traceable end to end (AP-5, NR-11).
"""

from __future__ import annotations

from .lineage import make_inference_lineage

# re-export for convenience at the backend boundary
from ml.lineage import VersionBundle, LineageTracker, make_lineage_record  # allowed: backend -> ml

__all__ = ["make_inference_lineage", "VersionBundle", "LineageTracker", "make_lineage_record"]
