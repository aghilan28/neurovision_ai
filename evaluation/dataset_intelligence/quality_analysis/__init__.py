"""``evaluation.dataset_intelligence.quality_analysis`` — dataset quality scoring.

Aggregates record-level signals (validation status, metadata completeness, channel
presence, sampling consistency, annotation sanity, duplicates) into a deterministic
**quality score** with structured findings. Report-only — it never alters data.
"""

from __future__ import annotations

from evaluation.dataset_intelligence.quality_analysis.analyzer import analyze_quality

__all__ = ["analyze_quality"]
