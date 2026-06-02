"""Schemas (contracts + value objects) for the preprocessing DSP layer.

* **Input/output signal contracts** — :class:`~preprocessing.schemas.signal.RawRecording`
  (the standardized input the pipeline consumes) and
  :class:`~preprocessing.schemas.signal.ProcessedSignal`.
* **Windows** — :class:`~preprocessing.schemas.windows.WindowSet` and
  :class:`~preprocessing.schemas.windows.WindowMetadata`.
* **Config** — frozen, fingerprintable stage configs and the composed
  :class:`~preprocessing.schemas.config.PipelineConfig`.
* **Reports** — stage results, filter specs, frequency-response checks, quality &
  validation reports.
* **Lineage** — :class:`~preprocessing.schemas.lineage.PreprocessingLineage`.

All array payloads are NumPy ``float64``; all metadata is JSON-serializable.
``RawRecording`` is preprocessing's *own* input contract — the layer never imports
``datasets`` (it is the dependency-graph leaf).
"""

from __future__ import annotations

from preprocessing.schemas.config import (
    FilterConfig,
    MontageConfig,
    NormalizationConfig,
    PipelineConfig,
    ResampleConfig,
    WindowConfig,
)
from preprocessing.schemas.enums import (
    BoundaryPolicy,
    MissingChannelPolicy,
    MontageType,
    NormalizationMethod,
    QualitySeverity,
    StageName,
    StageStatus,
)
from preprocessing.schemas.lineage import PreprocessingLineage, TransformationRecord
from preprocessing.schemas.reports import (
    FilterSpec,
    FrequencyResponseCheck,
    MontageResult,
    PreprocessingValidationReport,
    QualityIssue,
    QualityReport,
    StageResult,
    ValidationIssue,
)
from preprocessing.schemas.signal import ProcessedSignal, RawRecording
from preprocessing.schemas.windows import WindowMetadata, WindowSet

__all__ = [
    "BoundaryPolicy",
    "FilterConfig",
    "FilterSpec",
    "FrequencyResponseCheck",
    "MissingChannelPolicy",
    "MontageConfig",
    "MontageResult",
    "MontageType",
    "NormalizationConfig",
    "NormalizationMethod",
    "PipelineConfig",
    "PreprocessingLineage",
    "PreprocessingValidationReport",
    "ProcessedSignal",
    "QualityIssue",
    "QualityReport",
    "QualitySeverity",
    "RawRecording",
    "ResampleConfig",
    "StageName",
    "StageResult",
    "StageStatus",
    "TransformationRecord",
    "ValidationIssue",
    "WindowConfig",
    "WindowMetadata",
    "WindowSet",
]
