"""``ml/uncertainty/validation`` — uncertainty validation (V1-P6).

Checks that an uncertainty run is trustworthy before its outputs are used:
calibration was measured, conformal coverage was assessed, the calibration set was
patient-disjoint, versions are consistent, lineage is intact, and the clinical
completeness gate (calibrated uncertainty attached) is satisfied (NR-4).
"""

from __future__ import annotations

from .validators import UncertaintyValidator, UncertaintyValidationError

__all__ = ["UncertaintyValidator", "UncertaintyValidationError"]
