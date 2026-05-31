"""``certification/compliance`` — platform compliance evidence (P10).

Checks the cross-cutting platform invariants that any deployment decision must rest on:
determinism, traceability, the one-way architecture boundary (no domain package imports the
evaluation/operations/certification layers), governance documentation (ADRs), and faithful
uncertainty (NR-4). Evidence only — it changes nothing.
"""

from __future__ import annotations

import ast
import pathlib

from ..util import fingerprint
from ..version import CERTIFICATION_COMPLIANCE_VERSION

REPO = pathlib.Path(__file__).resolve().parents[2]
_DOMAIN = ("preprocessing", "datasets", "ml", "evaluation", "backend", "frontend")
_ONE_WAY_LAYERS = {"operations", "validation", "certification"}


def _imports_any(path: pathlib.Path, roots: set) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name.split(".")[0] in roots for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            if node.module.split(".")[0] in roots:
                return True
    return False


def check_boundaries() -> dict:
    """No domain package may import an evaluation/operations/certification layer (one-way)."""
    leaks = []
    for pkg in _DOMAIN:
        root = REPO / pkg
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if _imports_any(path, _ONE_WAY_LAYERS):
                leaks.append(str(path.relative_to(REPO)))
    return {"name": "architecture_boundaries_one_way", "passed": not leaks, "leaks": leaks}


def check_governance() -> dict:
    adrs = sorted((REPO / ".gcc" / "decisions").glob("ADR-*.md"))
    return {"name": "governance_documented", "passed": len(adrs) >= 22,
            "n_adrs": len(adrs)}


def collect_compliance(*, validation_result: dict, e2e_result: dict) -> dict:
    repro = validation_result.get("reproducibility", {})
    pipeline = validation_result.get("pipeline_result")
    calibration = validation_result.get("calibration", {})
    checks = [
        {"name": "determinism_preserved",
         "passed": bool(repro.get("within_instance", {}).get("reproducible"))},
        {"name": "traceability_preserved",
         "passed": bool(getattr(pipeline, "traceable", False)) and bool(e2e_result.get("ok"))},
        {"name": "faithful_uncertainty_nr4", "passed": bool(calibration.get("ok"))},
        check_boundaries(),
        check_governance(),
    ]
    ok = all(c["passed"] for c in checks)
    return {
        "compliance_version": CERTIFICATION_COMPLIANCE_VERSION, "ok": ok,
        "checks": checks, "signature": fingerprint([(c["name"], c["passed"]) for c in checks]),
    }


__all__ = ["collect_compliance", "check_boundaries", "check_governance"]
