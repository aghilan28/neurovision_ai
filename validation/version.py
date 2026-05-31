"""Version identities for the Validation & Performance Assurance Program (P9).

Validation is the top-level *evaluation* layer (peer of ``scripts``/``operations``): it
measures the existing P1-P8 systems and modifies none of them. Every validation artifact
(benchmark, scorecard, report) records the versions that produced it so the evidence is
reproducible and auditable. Bump a version when behaviour changes.
"""

from __future__ import annotations

VALIDATION_PROGRAM_VERSION: str = "validation-program@1.0.0"

VALIDATION_HARNESS_VERSION: str = "validation-harness@1.0.0"
VALIDATION_BENCHMARK_VERSION: str = "validation-benchmark@1.0.0"
VALIDATION_PERFORMANCE_VERSION: str = "validation-performance@1.0.0"
VALIDATION_ROBUSTNESS_VERSION: str = "validation-robustness@1.0.0"
VALIDATION_RELIABILITY_VERSION: str = "validation-reliability@1.0.0"
VALIDATION_REPRODUCIBILITY_VERSION: str = "validation-reproducibility@1.0.0"
VALIDATION_CALIBRATION_VERSION: str = "validation-calibration@1.0.0"
VALIDATION_DRIFT_VERSION: str = "validation-drift@1.0.0"
VALIDATION_SCORECARD_VERSION: str = "validation-scorecard@1.0.0"
VALIDATION_REPORT_VERSION: str = "validation-report@1.0.0"

# Deterministic default timestamp — wall-clock never enters a reproducible artifact.
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
