"""Feature content validation (P3-K, build-time).

Validates the *content* of the extracted feature vectors — completeness, integrity,
consistency, and determinism — producing structured ``(name, passed, detail)``
results that the service persists in the immutable ``FeatureValidationRecord``. Pure
functions; no exceptions for bad content.
"""

from __future__ import annotations

import math
from typing import Sequence

from ..models.domain import FeatureScope, FeatureVector


class FeatureContentValidator:
    """Build-time validation of the feature vectors."""

    def feature_completeness(self, vectors: Sequence[FeatureVector],
                             expected_families: Sequence[str]) -> tuple[str, bool, dict]:
        present = {v.family.value for v in vectors}
        missing = sorted(set(expected_families) - present)
        empty = [v.name for v in vectors if v.n_values == 0]
        ok = (not missing) and (not empty) and len(vectors) > 0
        return ("feature_completeness", ok,
                {"families_present": sorted(present), "missing_families": missing,
                 "empty_vectors": empty, "n_vectors": len(vectors)})

    def feature_integrity(self, vectors: Sequence[FeatureVector]) -> tuple[str, bool, dict]:
        bad_values = [v.name for v in vectors
                      if any(not math.isfinite(x) for x in v.values)]
        bad_shape = [v.name for v in vectors
                     if int(_prod(v.shape)) != v.n_values]
        ok = not bad_values and not bad_shape
        return ("feature_integrity", ok,
                {"non_finite_vectors": bad_values, "shape_mismatch_vectors": bad_shape})

    def feature_consistency(self, vectors: Sequence[FeatureVector],
                            n_channels: int) -> tuple[str, bool, dict]:
        issues = []
        for v in vectors:
            if v.scope == FeatureScope.PER_CHANNEL and v.n_values != n_channels:
                issues.append(f"{v.name}: per-channel n_values {v.n_values} != {n_channels}")
            if v.scope == FeatureScope.PER_CHANNEL_PAIR and v.n_values != n_channels * n_channels:
                issues.append(f"{v.name}: pair n_values {v.n_values} != {n_channels ** 2}")
        return ("feature_consistency", len(issues) == 0, {"issues": issues})

    def content_checks(self, vectors: Sequence[FeatureVector], *, expected_families: Sequence[str],
                       n_channels: int, determinism_ok: bool,
                       determinism_detail: dict) -> list[tuple]:
        return [
            self.feature_completeness(vectors, expected_families),
            self.feature_integrity(vectors),
            self.feature_consistency(vectors, n_channels),
            ("feature_determinism", bool(determinism_ok), determinism_detail),
        ]


def _prod(shape) -> int:
    out = 1
    for s in shape:
        out *= int(s)
    return out
