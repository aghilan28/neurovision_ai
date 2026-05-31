"""``validation.program`` — the end-to-end validation run (P9).

Orchestrates every validation subsystem over the real platform and returns all results +
the nine reports. This is what ``scripts/verify_productization_p9`` and the e2e test drive.
It evaluates only; it modifies nothing.
"""

from __future__ import annotations

import tempfile
from typing import Optional, Sequence

from .harness import PlatformHarness
from .benchmarking import (
    ModelBenchmarkRunner, PipelineBenchmarkRunner, InferenceBenchmarkRunner,
    WorkflowBenchmarkRunner, OperationalBenchmarkRunner,
)
from .performance import PerformanceValidator
from .robustness import RobustnessValidator
from .reliability import ReliabilityValidator
from .reproducibility import ReproducibilityValidator
from .calibration import CalibrationValidator
from .drift import DriftValidator
from .scorecards import build_scorecards
from .reporting import build_all_reports
from .version import VALIDATION_PROGRAM_VERSION

COHORT_FIXTURE_NAMES = ["valid.edf", "valid_edf_plus.edf", "valid.bdf", "valid_bdf_plus.bdf",
                        "valid_raw.fif", "valid.set"]


def all_architectures():
    from backend.model_foundation import ModelArchitecture
    return list(ModelArchitecture)


def _cohort_files(fixtures: dict) -> list:
    return [(f"P-{i}", f"C-{i}", fixtures[n]) for i, n in enumerate(COHORT_FIXTURE_NAMES)]


def run_validation(fixtures: dict, *, architectures: Optional[Sequence] = None,
                   benchmark_runs: int = 3, reliability_repeats: int = 5, reliability_stress: int = 8,
                   cross_instance: bool = True, workspace_dir: Optional[str] = None) -> dict:
    """Run the full P9 validation program against the real platform; return results+reports."""
    architectures = list(architectures) if architectures is not None else all_architectures()
    fixtures = dict(fixtures)
    cohort_files = _cohort_files(fixtures)
    sample = fixtures["valid.edf"]
    sample_b = fixtures.get("valid.bdf", sample)

    harness = PlatformHarness(workspace_dir=workspace_dir)
    feats = harness.build_cohort(cohort_files)

    # --- model validation / benchmark (P9-C / P9-B) ---
    model_benchmark = ModelBenchmarkRunner().run(harness, feats, architectures)
    muts = model_benchmark["muts"]
    mut = muts[architectures[0].value]

    # --- a representative pipeline run (P9-D) ---
    pipeline_result = harness.run_pipeline(sample, mut, patient_key="val-p", case_key="val-c")

    # --- benchmarks (P9-B) ---
    benchmarks = {
        "pipeline": PipelineBenchmarkRunner().run(harness, sample, mut, runs=benchmark_runs),
        "inference": InferenceBenchmarkRunner().run(harness, feats[0], mut, runs=benchmark_runs),
        "workflow": WorkflowBenchmarkRunner().run(harness, sample, mut, runs=benchmark_runs),
        "operational": OperationalBenchmarkRunner().run(runs=benchmark_runs),
    }

    # --- performance / robustness / reliability / reproducibility (P9 / E / F) ---
    performance = PerformanceValidator().validate(benchmarks)
    robustness = RobustnessValidator().run(harness, fixtures)
    reliability = ReliabilityValidator().run(harness, sample, mut, repeats=reliability_repeats,
                                             stress=reliability_stress)
    def _factory():
        return PlatformHarness(workspace_dir=tempfile.mkdtemp(prefix="nv_p9_rep_"))
    reproducibility = ReproducibilityValidator().run(
        harness, sample, mut,
        build_harness=_factory if cross_instance else None,
        eeg_files=cohort_files if cross_instance else None,
        architecture=architectures[0] if cross_instance else None)

    # --- calibration / drift (P9-G / H) ---
    calibration = CalibrationValidator().run(muts, pipeline_result)
    drift = DriftValidator().run(harness, muts, feats, eeg_file_a=sample, eeg_file_b=sample_b)

    # --- operations health (reused, P8) ---
    from operations.health import HealthChecker
    operations_health = HealthChecker(
        workspace_dir=tempfile.mkdtemp(prefix="nv_p9_health_")).check_all()

    # --- scorecards (P9-I) ---
    scorecards = build_scorecards(
        pipeline_result=pipeline_result, robustness=robustness, reliability=reliability,
        calibration=calibration, drift=drift, model_benchmark=model_benchmark,
        operations_health=operations_health)

    # --- reports (P9-J) ---
    reports = build_all_reports(
        benchmarks=benchmarks, model_benchmark=model_benchmark, performance=performance,
        reliability=reliability, robustness=robustness, calibration=calibration, drift=drift,
        scorecards=scorecards, reproducibility=reproducibility)

    validation_complete = bool(reports["validation_summary"]["validation_complete"])
    return {
        "validation_program_version": VALIDATION_PROGRAM_VERSION,
        "validation_complete": validation_complete,
        "pipeline_result": pipeline_result, "benchmarks": benchmarks,
        "model_benchmark": model_benchmark, "performance": performance, "robustness": robustness,
        "reliability": reliability, "reproducibility": reproducibility, "calibration": calibration,
        "drift": drift, "operations_health": operations_health, "scorecards": scorecards,
        "reports": reports,
    }


__all__ = ["run_validation", "all_architectures", "COHORT_FIXTURE_NAMES"]
