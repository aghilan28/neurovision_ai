"""The result object returned by a preprocessing run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from preprocessing.schemas.lineage import PreprocessingLineage
from preprocessing.schemas.reports import (
    FilterSpec,
    FrequencyResponseCheck,
    MontageResult,
    PreprocessingValidationReport,
    QualityReport,
    StageResult,
)
from preprocessing.schemas.signal import ProcessedSignal
from preprocessing.schemas.windows import WindowSet


@dataclass(frozen=True, eq=False)
class PreprocessingResult:
    """Everything a single preprocessing run produces (data + full evidence)."""

    status: str  # "ok" | "failed"
    processed_signal: ProcessedSignal | None
    windows: WindowSet | None
    stage_results: tuple[StageResult, ...]
    validations: tuple[PreprocessingValidationReport, ...]
    quality: QualityReport
    lineage: PreprocessingLineage
    filter_specs: tuple[FilterSpec, ...] = ()
    frequency_response_checks: tuple[FrequencyResponseCheck, ...] = ()
    montage_result: MontageResult | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "processed_signal": (
                self.processed_signal.fingerprint() if self.processed_signal else None
            ),
            "windows": self.windows.metadata_dict() if self.windows else None,
            "stage_results": [s.to_dict() for s in self.stage_results],
            "validations": [v.to_dict() for v in self.validations],
            "quality": self.quality.to_dict(),
            "lineage": self.lineage.to_dict(),
            "filter_specs": [f.to_dict() for f in self.filter_specs],
            "frequency_response_checks": [c.to_dict() for c in self.frequency_response_checks],
            "montage_result": self.montage_result.to_dict() if self.montage_result else None,
        }
