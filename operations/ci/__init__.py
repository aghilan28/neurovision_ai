"""``operations/ci`` — CI/CD foundation (P8-I).

A repository-native, vendor-neutral pipeline definition + runner. Steps are plain
commands executed in-repo (no GitHub-Actions/GitLab/Jenkins lock-in): build verification
(byte-compile), lint verification (ruff), test verification (pytest), the phase
verification scripts, quality gates, and release validation. The same definition can be
wired into any CI provider, but it runs standalone here.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

from ..version import OPERATIONS_CI_VERSION

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass(frozen=True)
class CiStep:
    name: str
    kind: str                      # build | lint | test | verify | quality | release
    command: tuple
    gate: bool = True              # a gate step must pass for the pipeline to pass

    def to_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "command": list(self.command),
                "gate": self.gate}


@dataclass(frozen=True)
class CiStepResult:
    name: str
    kind: str
    gate: bool
    passed: bool
    returncode: int
    tail: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "gate": self.gate, "passed": self.passed,
                "returncode": self.returncode, "tail": self.tail}


def default_pipeline() -> "list[CiStep]":
    py = sys.executable
    return [
        CiStep("build_verification", "build",
               (py, "-c", "import compileall,sys; "
                "sys.exit(0 if compileall.compile_dir('operations', quiet=1) else 1)")),
        CiStep("lint_verification", "lint",
               (py, "-m", "ruff", "check", "operations",
                "scripts/verify_productization_p8.py")),
        CiStep("test_verification", "test",
               (py, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_operations.py")),
        CiStep("verification_scripts", "verify",
               (py, "-m", "scripts.verify_productization_p8"), gate=False),
    ]


class CiPipeline:
    """Runs the pipeline (or a selected subset) and evaluates the quality gate."""

    def __init__(self, steps: Optional[list] = None, *, repo_root: str = REPO_ROOT):
        self.steps = steps if steps is not None else default_pipeline()
        self.repo_root = repo_root

    def run(self, *, only: Optional[list] = None, timeout: int = 600) -> "list[CiStepResult]":
        results: list[CiStepResult] = []
        for step in self.steps:
            if only is not None and step.name not in only:
                continue
            try:
                proc = subprocess.run(list(step.command), cwd=self.repo_root, capture_output=True,
                                      text=True, timeout=timeout)
                out = (proc.stdout or "") + (proc.stderr or "")
                tail = out.strip().splitlines()[-1] if out.strip() else ""
                results.append(CiStepResult(step.name, step.kind, step.gate,
                                            proc.returncode == 0, proc.returncode, tail[:300]))
            except Exception as exc:
                results.append(CiStepResult(step.name, step.kind, step.gate, False, -1,
                                            f"error: {exc}"))
        return results

    @staticmethod
    def quality_gate(results: "list[CiStepResult]") -> bool:
        """The gate passes iff every executed gate step passed."""
        return all(r.passed for r in results if r.gate)


class ReleaseValidator:
    """Combines CI results + operations validation into a release decision."""

    def validate(self, ci_results: list, ops_ok: bool) -> dict:
        gate_ok = CiPipeline.quality_gate(ci_results)
        ready = gate_ok and ops_ok
        reasons = []
        if not gate_ok:
            reasons += [f"ci gate failed: {r.name}" for r in ci_results if r.gate and not r.passed]
        if not ops_ok:
            reasons.append("operations validation failed")
        return {"release_ready": ready, "quality_gate_passed": gate_ok,
                "operations_ok": ops_ok, "reasons": reasons}


def build_ci_report(results: list, *, pipeline: Optional[CiPipeline] = None) -> dict:
    pipeline = pipeline or CiPipeline()
    return {
        "report_type": "ci", "ci_version": OPERATIONS_CI_VERSION, "vendor_neutral": True,
        "pipeline": [s.to_dict() for s in pipeline.steps],
        "executed": [r.to_dict() for r in results],
        "quality_gate_passed": CiPipeline.quality_gate(results),
    }


__all__ = ["CiStep", "CiStepResult", "CiPipeline", "ReleaseValidator", "default_pipeline",
           "build_ci_report", "REPO_ROOT"]
