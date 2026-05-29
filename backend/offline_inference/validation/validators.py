"""Inference validation checks (V1-P7).

Reuses ``ml.validation.ValidationReport`` for a consistent result shape. Each check
is a pure assertion over the inference bundle (versions, artifact store, lineage
tracker, output contracts, audit record).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ml.validation import ValidationReport  # allowed: backend -> ml


class InferenceValidationError(RuntimeError):
    """Raised when a mandated inference-validation check fails."""


class InferenceValidator:
    def validate(
        self,
        *,
        version_bundle: dict,
        artifact_store: Any,
        lineage_tracker: Any,
        inference_lineage_id: str,
        calibration: dict,
        coverage: dict,
        probability: dict,
        clinical: dict,
        audit: dict,
        n_inference: int,
    ) -> ValidationReport:
        report = ValidationReport()

        # 1. version consistency — all core versions present and non-empty
        required = ["dataset_version", "preprocessing_version", "split_version",
                    "model_version", "evaluation_version", "calibration_version",
                    "conformal_version"]
        missing = [k for k in required if not version_bundle.get(k)]
        report.add("version_consistency", not missing, f"missing={missing}")

        # 2. artifact integrity — every checksum verifies
        try:
            ok = artifact_store.verify()
            report.add("artifact_integrity", bool(ok), f"all checksums verified: {ok}")
        except Exception as exc:  # pragma: no cover - defensive
            report.add("artifact_integrity", False, f"error: {exc}")

        # 3. lineage integrity — inference lineage chain has no broken links
        try:
            ok = lineage_tracker.verify_chain(inference_lineage_id)
            report.add("lineage_integrity", bool(ok), f"chain verified: {ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 4. calibration integrity — positive temperature, finite ECE
        temp = calibration.get("temperature")
        ece_post = (calibration.get("ece") or {}).get("post")
        cal_ok = temp is not None and temp > 0 and ece_post is not None and ece_post >= 0
        report.add("calibration_integrity", bool(cal_ok), f"T={temp} ece_post={ece_post}")

        # 5. coverage integrity — observed in [0,1] and reliability flag present
        obs = coverage.get("observed_coverage")
        cov_ok = obs is not None and 0.0 <= obs <= 1.0 and "reliable" in coverage
        report.add("coverage_integrity", bool(cov_ok),
                   f"observed={obs} reliable={coverage.get('reliable')}")

        # 6. output integrity — probabilities valid + clinical record count matches
        probs = np.asarray(probability.get("probabilities", []), dtype=float)
        prob_ok = probs.ndim == 2 and probs.shape[0] == n_inference and \
            bool(np.allclose(probs.sum(axis=1), 1.0, atol=1e-3))
        clinical_ok = clinical.get("n") == n_inference
        report.add("output_integrity", bool(prob_ok and clinical_ok),
                   f"probs_ok={prob_ok} clinical_n={clinical.get('n')} expected={n_inference}")

        # 7. audit integrity — audit carries lineage chain + version bundle + exec sig
        audit_ok = bool(audit.get("lineage_chain")) and bool(audit.get("version_bundle")) \
            and bool(audit.get("execution", {}).get("content_signature"))
        report.add("audit_integrity", audit_ok, "audit references present")

        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise InferenceValidationError(f"inference validation failed: {names}")
