"""``backend/signal_processing/filtering`` — deterministic EEG filters (P2-C).

Bandpass / highpass / lowpass / notch / reference correction implemented with
scipy (zero-phase, stable on short recordings). Every filter returns a new array +
its tracked ``FilterConfig``; inputs are never mutated.
"""

from __future__ import annotations

from .filters import FilteringEngine, FilteringError

__all__ = ["FilteringEngine", "FilteringError"]
