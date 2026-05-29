"""``evaluation.dataset_intelligence.channel_analysis`` — channel inventory & compatibility.

Builds a channel inventory (availability across recordings) and a montage /
cross-dataset compatibility matrix, reusing the montage definitions owned by
:mod:`preprocessing.montages` (no duplication of montage logic). Compatibility is
relevant to domain-shift readiness (AP-10, NR-15).
"""

from __future__ import annotations

from evaluation.dataset_intelligence.channel_analysis.analyzer import analyze_channels

__all__ = ["analyze_channels"]
