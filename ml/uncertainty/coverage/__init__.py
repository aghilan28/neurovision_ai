"""``ml/uncertainty/coverage`` — coverage tracking & validation (V1-P6).

Tracks target vs. observed coverage of conformal prediction sets, coverage drift,
violations, per-class coverage, and produces a coverage audit. This is how the
platform verifies that its uncertainty guarantees actually hold on patient-disjoint
data (AP-4).
"""

from __future__ import annotations

from .coverage import CoverageTracker

__all__ = ["CoverageTracker"]
