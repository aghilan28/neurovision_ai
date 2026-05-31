"""``validation/reproducibility`` — reproducibility analysis (P9).

Confirms the platform is bit-for-bit reproducible: the same inputs reproduce identical
output identities both **within** a platform instance (repeated runs) and **across**
independent instances (a fresh harness reproduces the same prediction id + fingerprints).
This is the strongest determinism evidence (NR-9/NR-10).
"""

from __future__ import annotations

from ..util import fingerprint
from ..version import VALIDATION_REPRODUCIBILITY_VERSION


class ReproducibilityValidator:
    def within_instance(self, harness, eeg_file: str, mut, *, runs: int = 3) -> dict:
        fps = [harness.run_pipeline(eeg_file, mut, patient_key="rep-p", case_key="rep-c"
                                   ).output_fingerprint() for _ in range(runs)]
        return {"runs": runs, "unique": len(set(fps)), "reproducible": len(set(fps)) == 1,
                "fingerprint": fps[0] if fps else None}

    def cross_instance(self, build_harness, eeg_files, architecture, eeg_file: str) -> dict:
        """``build_harness`` is a 0-arg factory returning a fresh PlatformHarness."""
        def one(factory_seed):
            h = build_harness()
            feats = h.build_cohort(eeg_files)
            mut = h.train_models(feats, [architecture])[architecture.value]
            res = h.run_pipeline(eeg_file, mut, patient_key="rep-p", case_key="rep-c")
            return res.prediction_id, res.output_fingerprint(), mut.model_id
        a = one("a")
        b = one("b")
        return {"reproducible": a == b, "a": {"prediction_id": a[0], "fingerprint": a[1],
                                              "model_id": a[2]},
                "b": {"prediction_id": b[0], "fingerprint": b[1], "model_id": b[2]}}

    def run(self, harness, eeg_file: str, mut, *, build_harness=None, eeg_files=None,
            architecture=None) -> dict:
        within = self.within_instance(harness, eeg_file, mut)
        result = {"reproducibility_version": VALIDATION_REPRODUCIBILITY_VERSION,
                  "within_instance": within}
        if build_harness and eeg_files and architecture:
            cross = self.cross_instance(build_harness, eeg_files, architecture, eeg_file)
            result["cross_instance"] = cross
            result["ok"] = within["reproducible"] and cross["reproducible"]
        else:
            result["ok"] = within["reproducible"]
        result["signature"] = fingerprint({"within": within["fingerprint"], "ok": result["ok"]})
        return result


def build_reproducibility_report(result: dict) -> dict:
    return {"report_type": "reproducibility", **result}


__all__ = ["ReproducibilityValidator", "build_reproducibility_report"]
