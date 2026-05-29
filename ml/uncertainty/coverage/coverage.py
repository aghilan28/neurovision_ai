"""Coverage tracking for conformal prediction sets.

Given prediction sets and true labels (on a patient-disjoint test set), compute:
  * observed coverage vs. target,
  * coverage drift (observed - target),
  * violations (windows whose true label is not in the set),
  * per-class coverage,
  * a coverage audit with a reliability verdict and an audit signature.
"""

from __future__ import annotations

import numpy as np

from ...provenance import hash_obj
from ..schemas import CoverageResult


class CoverageTracker:
    def __init__(self, tolerance: float = 0.05):
        # acceptable shortfall below target before coverage is deemed unreliable
        self.tolerance = float(tolerance)

    def assess(
        self,
        *,
        prediction_sets: np.ndarray,
        labels: np.ndarray,
        target_coverage: float,
        class_names: tuple[str, ...],
        dataset_version: str | None = None,
        split_version: str | None = None,
    ) -> CoverageResult:
        sets = np.asarray(prediction_sets, dtype=bool)
        y = np.asarray(labels, dtype=int)
        n = y.size
        hit = sets[np.arange(n), y]  # true label in set?
        observed = float(np.mean(hit)) if n else 0.0
        drift = observed - target_coverage
        violations = np.nonzero(~hit)[0]
        sizes = sets.sum(axis=1)

        per_class: dict[str, dict] = {}
        for c, name in enumerate(class_names):
            mask = y == c
            cnt = int(mask.sum())
            cov = float(np.mean(hit[mask])) if cnt else None
            per_class[name] = {
                "support": cnt,
                "coverage": None if cov is None else round(cov, 6),
                "mean_set_size": round(float(sizes[mask].mean()), 6) if cnt else None,
            }

        reliable = observed >= (target_coverage - self.tolerance)
        audit = {
            "n": int(n),
            "target_coverage": round(float(target_coverage), 6),
            "observed_coverage": round(observed, 6),
            "tolerance": self.tolerance,
            "reliable": reliable,
            "dataset_version": dataset_version,
            "split_version": split_version,
            "audit_signature": hash_obj({
                "target": target_coverage,
                "observed": round(observed, 6),
                "dataset_version": dataset_version,
                "split_version": split_version,
            }),
        }

        return CoverageResult(
            target_coverage=float(target_coverage),
            observed_coverage=observed,
            coverage_drift=float(drift),
            n_violations=int(violations.size),
            violation_rate=float(violations.size / n) if n else 0.0,
            per_class_coverage=per_class,
            average_set_size=float(sizes.mean()) if n else 0.0,
            reliable=bool(reliable),
            audit=audit,
        )
