"""Version identities for the uncertainty & calibration layer (V1-P6).

Re-exports the canonical version constants from ``ml.version`` so uncertainty
artifacts pin their producing versions for reproducibility/audit (AP-6 / AP-9).
"""

from __future__ import annotations

from ..version import (
    CALIBRATION_VERSION,
    CONFORMAL_VERSION,
    COVERAGE_VERSION,
    RISK_VERSION,
    UNCERTAINTY_REGISTRY_VERSION,
)

# The uncertainty subsystem as a whole.
UNCERTAINTY_LAYER_VERSION: str = "uncertainty@1.0.0"
RELIABILITY_VERSION: str = "reliability@1.0.0"

__all__ = [
    "UNCERTAINTY_LAYER_VERSION",
    "CALIBRATION_VERSION",
    "CONFORMAL_VERSION",
    "COVERAGE_VERSION",
    "RISK_VERSION",
    "RELIABILITY_VERSION",
    "UNCERTAINTY_REGISTRY_VERSION",
]
