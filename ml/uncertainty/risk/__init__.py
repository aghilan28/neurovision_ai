"""``ml/uncertainty/risk`` — clinical risk framework (V1-P6).

Turns calibrated confidence and conformal set sizes into per-window risk scores,
confidence bands, and low-confidence alerts that drive abstain/escalate behavior
(AP-4). Includes a forward hook for future operational risk integration.
"""

from __future__ import annotations

from .risk import RiskAssessor

__all__ = ["RiskAssessor"]
