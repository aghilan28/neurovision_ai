"""``ml/uncertainty/reliability`` — reliability analysis artifacts (V1-P6).

Produces reliability diagrams, calibration tables, confidence histograms,
prediction confidence profiles, and risk profiles — all as JSON-able data so they
are reproducible, versioned, and renderable by any later presentation layer
without coupling the uncertainty layer to plotting.
"""

from __future__ import annotations

from .reliability import ReliabilityAnalyzer

__all__ = ["ReliabilityAnalyzer"]
