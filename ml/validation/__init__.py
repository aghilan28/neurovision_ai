"""``ml/validation`` — training validation (V1-P5).

Implements the mandated pre-/post-training checks that must pass before a training
run is trusted:
  1. Dataset Exists
  2. Patient-Disjoint Split Exists
  3. Version Consistency
  4. Configuration Validity
  5. Artifact Integrity
  6. Lineage Integrity
  7. Evaluation Compatibility

These checks are the ML-layer guard that enforces NR-3 (patient-disjoint),
NR-9/NR-10 (determinism/reproducibility integrity) and NR-11 (traceability) at
training time. A failing check is stop-and-remediate, not a warning.
"""

from __future__ import annotations

from .validators import (
    CheckResult,
    ValidationReport,
    TrainingValidator,
    TrainingValidationError,
)

__all__ = ["CheckResult", "ValidationReport", "TrainingValidator", "TrainingValidationError"]
