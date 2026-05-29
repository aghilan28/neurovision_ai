"""Calibration & clinical metric **placeholders** (V1-P4).

Calibration (e.g. ECE/coverage) and clinical metrics (e.g. alarm rate) are owned by
the **future** uncertainty and clinical phases (Conformal Prediction etc.). To
respect scope (NR-13) they are *registered* here — so the framework knows they
exist and reserves their names/contracts — but their computation is intentionally
**not implemented**. Calling them raises :class:`CalibrationNotAvailable`.
"""

from __future__ import annotations


class CalibrationNotAvailable(NotImplementedError):
    """Raised when a placeholder calibration/clinical metric is invoked."""


def expected_calibration_error(*_args: object, **_kwargs: object) -> float:
    """Placeholder — calibration is owned by the future uncertainty phase."""
    raise CalibrationNotAvailable(
        "expected_calibration_error is a placeholder in V1-P4; calibration/coverage "
        "is implemented by the future uncertainty (Conformal Prediction) phase (NR-13)."
    )


def coverage(*_args: object, **_kwargs: object) -> float:
    """Placeholder — conformal coverage is owned by the future uncertainty phase."""
    raise CalibrationNotAvailable(
        "coverage is a placeholder in V1-P4; conformal coverage is implemented by the "
        "future uncertainty phase (NR-13)."
    )
