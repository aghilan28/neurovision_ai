"""Version identity for the evaluation (validation) harness.

The evaluation version is recorded in every metric report and benchmark so results
are reproducible and auditable (AP-6 / NR-10). This module realizes the V1-P4
*integration surface* needed by V1-P5/P6: patient-disjoint metrics + calibration/
coverage measurement. It is intentionally minimal and focused on what baseline
benchmarking and uncertainty validation require.
"""

from __future__ import annotations

EVALUATION_VERSION: str = "evaluation@1.0.0"
