"""``validation`` — Validation & Performance Assurance Program (Productization P9).

Transforms the deployable product (P1-P8) into a **validated** product: it measures how
well NeuroVision actually performs and produces the evidence — benchmarks, model/pipeline
validation, robustness, reliability, reproducibility, calibration, drift, readiness
scorecards, and reports. The objective is **evidence**; it adds no capability.

This is the top-level *evaluation* layer (peer of ``scripts``/``operations``): it
**evaluates** the existing systems and **modifies none** of them. It is not one of the
six governed domain packages, so it may import ``backend``/``operations`` (lazily); no
domain package imports ``validation`` (asserted in tests).

NB: distinct from the existing ``evaluation`` package (V1-P3/P4 dataset/metric foundation),
which this layer reuses indirectly through the platform services.
"""

from __future__ import annotations

from .version import (
    VALIDATION_PROGRAM_VERSION, VALIDATION_HARNESS_VERSION, VALIDATION_BENCHMARK_VERSION,
    VALIDATION_PERFORMANCE_VERSION, VALIDATION_ROBUSTNESS_VERSION, VALIDATION_RELIABILITY_VERSION,
    VALIDATION_REPRODUCIBILITY_VERSION, VALIDATION_CALIBRATION_VERSION, VALIDATION_DRIFT_VERSION,
    VALIDATION_SCORECARD_VERSION, VALIDATION_REPORT_VERSION,
)
from .harness import PlatformHarness, PipelineResult, StageResult, ModelUnderTest
from .benchmarking import (
    BenchmarkResult, run_benchmark, ModelBenchmarkRunner, PipelineBenchmarkRunner,
    InferenceBenchmarkRunner, WorkflowBenchmarkRunner, OperationalBenchmarkRunner,
)
from .performance import PerformanceValidator, build_performance_report
from .robustness import RobustnessValidator, build_robustness_report
from .reliability import ReliabilityValidator, build_reliability_report
from .reproducibility import ReproducibilityValidator, build_reproducibility_report
from .calibration import CalibrationValidator, build_calibration_report, build_confidence_report
from .drift import DriftValidator, build_drift_report
from .scorecards import build_scorecards
from .reporting import build_all_reports, build_executive_summary, build_validation_summary
from .program import run_validation, all_architectures, COHORT_FIXTURE_NAMES

__all__ = [
    "VALIDATION_PROGRAM_VERSION", "VALIDATION_HARNESS_VERSION", "VALIDATION_BENCHMARK_VERSION",
    "VALIDATION_PERFORMANCE_VERSION", "VALIDATION_ROBUSTNESS_VERSION", "VALIDATION_RELIABILITY_VERSION",
    "VALIDATION_REPRODUCIBILITY_VERSION", "VALIDATION_CALIBRATION_VERSION", "VALIDATION_DRIFT_VERSION",
    "VALIDATION_SCORECARD_VERSION", "VALIDATION_REPORT_VERSION",
    "PlatformHarness", "PipelineResult", "StageResult", "ModelUnderTest",
    "BenchmarkResult", "run_benchmark", "ModelBenchmarkRunner", "PipelineBenchmarkRunner",
    "InferenceBenchmarkRunner", "WorkflowBenchmarkRunner", "OperationalBenchmarkRunner",
    "PerformanceValidator", "build_performance_report", "RobustnessValidator",
    "build_robustness_report", "ReliabilityValidator", "build_reliability_report",
    "ReproducibilityValidator", "build_reproducibility_report", "CalibrationValidator",
    "build_calibration_report", "build_confidence_report", "DriftValidator", "build_drift_report",
    "build_scorecards", "build_all_reports", "build_executive_summary", "build_validation_summary",
    "run_validation", "all_architectures", "COHORT_FIXTURE_NAMES",
]
