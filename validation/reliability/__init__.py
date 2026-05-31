"""``validation/reliability`` — reliability testing (P9-F).

Exercises the real platform under repeated / long-running / stress execution and asserts
deterministic outcomes plus registry / audit / lineage / workflow integrity. "Long
running" and "stress" are modelled as many repeated sequential executions (deterministic,
no wall-clock dependence). Every repeat must reproduce the same output fingerprint.
"""

from __future__ import annotations

from ..util import fingerprint
from ..version import VALIDATION_RELIABILITY_VERSION


class ReliabilityValidator:
    def run(self, harness, eeg_file: str, mut, *, repeats: int = 5, stress: int = 10) -> dict:
        checks = []

        # --- repeated execution (determinism) ---
        fps = []
        successes = 0
        last = None
        for i in range(repeats):
            res = harness.run_pipeline(eeg_file, mut, patient_key="rel-p", case_key="rel-c")
            fps.append(res.output_fingerprint())
            successes += 1 if res.success else 0
            last = res
        repeated_ok = (successes == repeats) and (len(set(fps)) == 1)
        checks.append({"name": "repeated_execution", "passed": repeated_ok,
                       "detail": f"{successes}/{repeats} ok; unique_fingerprints={len(set(fps))}"})

        # --- long-running execution (more repeats, still deterministic) ---
        long_fps = {harness.run_pipeline(eeg_file, mut, patient_key="rel-p", case_key="rel-c"
                                        ).output_fingerprint() for _ in range(repeats)}
        checks.append({"name": "long_running_execution", "passed": long_fps == set(fps),
                       "detail": f"stable_fingerprint={long_fps == set(fps)}"})

        # --- stress execution (repeated inference) ---
        stress_ok = True
        pred_ids = set()
        for _ in range(stress):
            out = harness.svc.inference_service.predict(
                mut.model, mut.train_feature_records[0],
                train_feature_records=list(mut.train_feature_records), dataset_key=mut.dataset_key)
            stress_ok = stress_ok and out.accepted
            pred_ids.add(out.asset.prediction_id if out.asset else None)
        checks.append({"name": "stress_execution",
                       "passed": stress_ok and len(pred_ids) == 1,
                       "detail": f"{stress} inferences; deterministic={len(pred_ids) == 1}"})

        # --- integrity checks (registry / audit / lineage / workflow) ---
        registry_ok = harness.svc.registry.orphans() == []
        checks.append({"name": "registry_integrity", "passed": registry_ok,
                       "detail": f"application_registry_orphans={len(harness.svc.registry.orphans())}"})

        try:
            audit_log = harness.svc.model_service.audit_log_for(mut.model_id)
            audit_ok = audit_log.verify() and mut.model.audit_head == audit_log.head
        except Exception:
            audit_ok = False
        checks.append({"name": "audit_integrity", "passed": bool(audit_ok),
                       "detail": "model audit log verified + head match"})

        lineage_ok = bool(last and last.traceable)
        kinds = ({n.kind for n in harness.svc.lineage.chain(last.lineage_id)}
                 if (last and last.lineage_id) else set())
        lineage_ok = lineage_ok and {"patient", "case", "eeg", "feature", "model", "prediction"} <= kinds
        checks.append({"name": "lineage_integrity", "passed": bool(lineage_ok),
                       "detail": f"chain_kinds={sorted(kinds)}"})

        workflow_ok = bool(last and last.success and len(last.stages) == 5
                           and all(s.ok for s in last.stages))
        checks.append({"name": "workflow_integrity", "passed": workflow_ok,
                       "detail": f"stages_ok={[s.ok for s in (last.stages if last else [])]}"})

        ok = all(c["passed"] for c in checks)
        return {
            "reliability_version": VALIDATION_RELIABILITY_VERSION, "ok": ok,
            "repeats": repeats, "stress": stress, "checks": checks,
            "signature": fingerprint({"fingerprint": (sorted(set(fps)) or [None])[0],
                                      "checks": [(c["name"], c["passed"]) for c in checks]}),
        }


def build_reliability_report(result: dict) -> dict:
    return {"report_type": "reliability", **result}


__all__ = ["ReliabilityValidator", "build_reliability_report"]
