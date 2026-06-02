"""``preprocessing.pipelines`` — the deterministic preprocessing pipeline.

Composes the independently-testable stages into one auditable run:

    input validation → channel validation → resampling → filtering → montage →
    normalization → window generation → output validation → quality reporting →
    lineage recording

The pipeline never raises on *data* problems: a stage failure is captured as a
failed :class:`~preprocessing.schemas.reports.StageResult` and the run returns a
:class:`~preprocessing.pipelines.result.PreprocessingResult` with ``status =
"failed"`` plus all evidence gathered so far (structured failure, not a crash).
"""

from __future__ import annotations

from preprocessing.pipelines.pipeline import PreprocessingPipeline
from preprocessing.pipelines.result import PreprocessingResult

__all__ = ["PreprocessingPipeline", "PreprocessingResult"]
