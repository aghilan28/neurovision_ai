"""``ml/lineage`` — model & prediction lineage tracking (V1-P5).

Every artifact (training run, evaluation, calibration, conformal, coverage, risk,
benchmark) gets a content-addressed ``LineageRecord`` that pins the exact dataset,
preprocessing, split, model, evaluation and benchmark versions that produced it,
plus links to its parent records. This makes every prediction traceable
end-to-end (AP-5 / NR-11) and the whole pipeline auditable (AP-8).
"""

from __future__ import annotations

from .lineage import LineageRecord, LineageTracker, make_lineage_record, VersionBundle

__all__ = ["LineageRecord", "LineageTracker", "make_lineage_record", "VersionBundle"]
