"""``validation/robustness`` — robustness testing (P9-E).

Feeds degraded / adversarial inputs to the real EEG ingestion (corrupted, partial, empty,
truncated, unsupported, and the committed corrupted/unsupported fixtures) and asserts the
platform handles them **gracefully** — it never raises; it returns a structured outcome
(rejected with a reason, or quarantined). Also validates **recovery**: a good input after
a bad one still succeeds. Produces robustness, failure-analysis, and recovery reports.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Optional

from ..util import fingerprint
from ..version import VALIDATION_ROBUSTNESS_VERSION


@dataclass
class RobustnessCase:
    name: str
    path: str
    expectation: str               # "graceful" — handled without raising


def _write(tmp: str, name: str, data: bytes) -> str:
    path = os.path.join(tmp, name)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def build_cases(tmp_dir: str, fixtures: dict) -> list:
    """Construct the robustness input set from committed fixtures + synthesized degradations."""
    os.makedirs(tmp_dir, exist_ok=True)
    valid_edf = fixtures.get("valid.edf")
    raw = open(valid_edf, "rb").read() if valid_edf and os.path.exists(valid_edf) else b"\x00" * 4096
    cases = [
        RobustnessCase("corrupted_eeg", fixtures.get("corrupted.edf", ""), "graceful"),
        RobustnessCase("unsupported_input", fixtures.get("unsupported.eeg", ""), "graceful"),
        RobustnessCase("empty_eeg", _write(tmp_dir, "empty.edf", b""), "graceful"),
        RobustnessCase("partial_eeg", _write(tmp_dir, "partial.edf", raw[: max(1, len(raw) // 4)]),
                       "graceful"),
        RobustnessCase("tiny_eeg", _write(tmp_dir, "tiny.edf", raw[:8]), "graceful"),
        RobustnessCase("header_only_eeg", _write(tmp_dir, "header.edf", raw[:256]), "graceful"),
        RobustnessCase("noisy_bytes_eeg",
                       _write(tmp_dir, "noisy.edf", bytes((b ^ 0x5A) for b in raw[:2048])), "graceful"),
        RobustnessCase("nonexistent_path", os.path.join(tmp_dir, "does_not_exist.edf"), "graceful"),
    ]
    return [c for c in cases if c.path]


class RobustnessValidator:
    """Runs the robustness cases against the real ingestion via the harness probe."""

    def run(self, harness, fixtures: dict, *, tmp_dir: Optional[str] = None) -> dict:
        tmp_dir = tmp_dir or tempfile.mkdtemp(prefix="nv_p9_robust_")
        cases = build_cases(tmp_dir, fixtures)
        results = []
        for i, case in enumerate(cases):
            probe = harness.probe_ingest(case.path, case_key=f"robust-{i}-{case.name}")
            results.append({"case": case.name, "graceful": probe["graceful"],
                            "raised": probe["raised"], "accepted": probe["accepted"],
                            "status": probe["status"], "reason": probe["reason"][:120]})
        # recovery: a valid input after all the bad ones must still succeed
        recovery = harness.probe_ingest(fixtures.get("valid.edf", ""), case_key="robust-recovery")
        recovered = recovery["graceful"] and recovery["accepted"]
        all_graceful = all(r["graceful"] for r in results)
        return {
            "robustness_version": VALIDATION_ROBUSTNESS_VERSION,
            "ok": all_graceful and recovered,
            "n_cases": len(results), "all_graceful": all_graceful, "recovered": recovered,
            "cases": results,
            "signature": fingerprint({"cases": [(r["case"], r["graceful"]) for r in results],
                                      "recovered": recovered}),
        }


def build_robustness_report(result: dict) -> dict:
    failures = [c for c in result["cases"] if not c["graceful"]]
    return {
        "report_type": "robustness", **result,
        "failure_analysis": {"n_failures": len(failures), "failures": failures},
        "recovery_analysis": {"recovered_after_failures": result["recovered"]},
    }


__all__ = ["RobustnessValidator", "RobustnessCase", "build_cases", "build_robustness_report"]
