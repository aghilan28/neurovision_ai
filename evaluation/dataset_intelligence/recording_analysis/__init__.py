"""``evaluation.dataset_intelligence.recording_analysis`` — recording intelligence.

Analyzes recording lengths, sampling frequencies, annotation density, recording
variability, and temporal distribution.
"""

from __future__ import annotations

from evaluation.dataset_intelligence.recording_analysis.analyzer import analyze_recordings

__all__ = ["analyze_recordings"]
