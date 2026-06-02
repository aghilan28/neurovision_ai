"""``backend/signal_processing/quality`` — deterministic signal-quality engine (P2-D).

Computes channel/recording quality, noise, stability, completeness, sampling
consistency, and quality scores, producing a ``SignalQualityRecord`` with findings,
severities, a grade band, and recommendations.
"""

from __future__ import annotations

from .quality import SignalQualityEngine

__all__ = ["SignalQualityEngine"]
