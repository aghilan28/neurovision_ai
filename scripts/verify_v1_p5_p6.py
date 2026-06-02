"""Final validation harness: verify the 15 directive criteria for V1-P5 + V1-P6.

Run: python -m scripts.verify_v1_p5_p6
Prints a PASS/FAIL line per criterion and exits non-zero if any fails.
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

import sys
import tempfile

import numpy as np

from datasets import SyntheticConfig, SplitConfig
from ml.training import TrainingConfig
from ml.models import available_models
from scripts.run_pipeline import run_pipeline, PipelineConfig


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))

    tmp = tempfile.mkdtemp()
    cfg = PipelineConfig(
        synthetic=SyntheticConfig(n_patients=16, windows_per_patient=24),
        split=SplitConfig(),
        training=TrainingConfig(steps=120),
        models=("simple_cnn", "eegnet", "tcn"),
        alpha=0.1,
        output_dir=tmp + "/run",
    )
    res = run_pipeline(cfg, verbose=False)
    summary = res["pipeline_summary"]
    models = summary["models"]

    # 1-3. EEGNet / TCN / CNN baseline work
    for arch in ("eegnet", "tcn", "simple_cnn"):
        m = models[arch]
        check(f"{arch} works", m["status"] == "registered" and m["metrics"]["accuracy"] > 0.5,
              f"acc={m['metrics']['accuracy']:.3f}")

    # 4. Training pipeline works
    check("training pipeline works", all(m["training_validation_ok"] for m in models.values()))

    # 5. Model registry works
    check("model registry works",
          res["model_registry"].to_dict()["n_models"] == 3 and len(set(models)) == 3)

    # 6. Lineage tracking works
    lineage = res["lineage"]
    lineage_ok = all(
        lineage.verify_chain(m["lineage"]["benchmark"]) and
        {"training", "evaluation", "uncertainty", "benchmark"} == set(m["lineage"])
        for m in models.values()
    )
    check("lineage tracking works", lineage_ok)

    # 7. Benchmark registration works
    check("benchmark registration works",
          len(res["benchmark_registry"].list_benchmarks()) == 3)

    # 8. Calibration framework works
    check("calibration framework works",
          all(m["calibration"]["temperature"] > 0 for m in models.values()))

    # 9. Reliability analysis works (reports written + non-empty diagram)
    import json, pathlib
    root = pathlib.Path(res["store"].root)
    rel_ok = True
    for mv, rec in json.loads((root / "registries/model_registry.json").read_text())["models"].items():
        cal = json.loads((root / rec["model_name"] / mv / "reports/calibration_report.json").read_text())
        rel_ok = rel_ok and bool(cal["reliability"]["reliability_diagram"])
    check("reliability analysis works", rel_ok)

    # 10. Conformal prediction works (coverage near/above target, no empty sets implied)
    check("conformal prediction works",
          all(m["coverage"]["observed"] >= m["coverage"]["target"] - 0.1 for m in models.values()))

    # 11. Coverage validation works
    check("coverage validation works", all(m["coverage"]["reliable"] for m in models.values()))

    # 12. Risk framework works
    check("risk framework works",
          all(0.0 <= m["risk"]["abstain_rate"] <= 1.0 for m in models.values()))

    # 13. All reports generate correctly
    reports = ["calibration_report", "conformal_report", "coverage_report",
               "risk_report", "summary_report", "audit_report"]
    reports_ok = True
    mr = json.loads((root / "registries/model_registry.json").read_text())["models"]
    for mv, rec in mr.items():
        for r in reports:
            reports_ok = reports_ok and (root / rec["model_name"] / mv / "reports" / f"{r}.json").exists()
    check("all reports generate correctly", reports_ok)

    # 14. Patient-disjoint + clinical completeness (NR-3, NR-4) + reproducibility
    pd_ok = all(m["patient_disjoint"] and m["clinical_prediction_complete"] for m in models.values())
    check("patient-disjoint + calibrated clinical outputs (NR-3/NR-4)", pd_ok)

    res2 = run_pipeline(PipelineConfig(**{**cfg.__dict__, "output_dir": tmp + "/run2"}), verbose=False)
    check("reproducible (run_id + summary checksum match)",
          res["run_id"] == res2["run_id"] and res["summary_checksum"] == res2["summary_checksum"])

    # 15. Artifacts verified + V0 quality-gate boundary check (ml never imports evaluation)
    check("artifacts integrity verified", res["store"].verify() is True)

    import ast, pathlib as pl
    ml_imports_eval = False
    for path in (pl.Path(__file__).resolve().parents[1] / "ml").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(a.name.split(".")[0] == "evaluation" for a in node.names):
                ml_imports_eval = True
            if isinstance(node, ast.ImportFrom) and (node.level or 0) == 0 and node.module \
                    and node.module.split(".")[0] == "evaluation":
                ml_imports_eval = True
    check("V0 quality gate: ml never imports evaluation (NR-8)", not ml_imports_eval)

    # report
    print(f"available baseline models: {available_models()}")
    width = max(len(n) for n, _, _ in checks)
    all_ok = True
    for i, (name, ok, detail) in enumerate(checks, 1):
        all_ok = all_ok and ok
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {i:2d}. {name.ljust(width)}  {detail}")
    print("\nRESULT:", "ALL CRITERIA SATISFIED" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
