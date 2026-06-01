"""Final validation for V1-P7 + V1-P8 + V1 Certification.

Objectively verifies the directive's 15 final-validation criteria and prints a
PASS/FAIL line per criterion. Exits non-zero if any criterion fails.

    python -m scripts.verify_v1
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

import ast
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    from datasets import SyntheticConfig
    from ml.training import TrainingConfig
    from backend.offline_inference import InferenceOrchestrator, PipelineConfig, FakeClock
    from backend.offline_inference.artifacts import verify_directory
    from frontend.offline_research_app import (
        AppState, build_app_view, render_from_run_dir,
        upload_workflow, benchmark_workflow, audit_workflow,
    )

    tmp = tempfile.mkdtemp()
    cfg = PipelineConfig(synthetic=SyntheticConfig(n_patients=14, windows_per_patient=18),
                         training=TrainingConfig(steps=100), model_name="tcn", alpha=0.1)
    result = InferenceOrchestrator(cfg, output_dir=tmp + "/run", clock=FakeClock()).run()
    out = result.output_dir

    # 1. End-to-end inference works
    check("end-to-end inference works",
          result.execution.ok and len(result.execution.stages) == 15)
    # 2. Output contracts work
    need = {"prediction", "probability", "calibration", "conformal", "coverage",
            "risk", "clinical", "summary"}
    check("output contracts work", need.issubset(result.outputs))
    # 3. Registry works
    check("inference registry works",
          result.registries["inference"].list_inferences() == [result.inference_id])
    # 4. Artifact system works
    art_ok, art_details = verify_directory(out)
    check("artifact system works", art_ok, f"{art_details['n_ok']}/{art_details['n_checked']} verified")
    # 5. Lineage works
    check("lineage works", result.registries["lineage"].verify_chain(result.lineage_id))
    # 6. Reports work
    idx = AppState.load(out).index
    check("reports work", set(idx["reports"]) >= {"inference_report", "calibration_report",
          "coverage_report", "risk_report", "summary_report", "audit_report"})

    # 7-11. Offline application + workflows + visualizations
    state = AppState.load(out)
    view = build_app_view(state).to_dict()
    check("offline application works", view["validation"]["ok"] and len(view["pages"]) == 5)
    all_viz = [v for p in view["pages"] for v in p["visualizations"]]
    check("visualizations work", len(all_viz) >= 11)
    up = upload_workflow(state).to_dict()
    check("upload workflow works", any(s["title"] == "File Metadata" for s in up["sections"]))
    bench = benchmark_workflow(state).to_dict()
    check("benchmark workflow works", any(s["title"] == "Model Benchmarks" for s in bench["sections"]))
    audit = audit_workflow(state).to_dict()
    check("audit workflow works", any(v["title"] == "Lineage Graph" for v in audit["visualizations"]))

    # 12. Deterministic reproducibility
    r2 = InferenceOrchestrator(cfg, output_dir=tmp + "/run2", clock=FakeClock()).run()
    html1 = render_from_run_dir(out)
    html2 = render_from_run_dir(r2.output_dir)
    check("deterministic reproducibility works",
          result.inference_id == r2.inference_id
          and result.execution.content_signature() == r2.execution.content_signature()
          and html1 == html2)

    # 13. Certification audit completes
    cert = REPO / "docs" / "certification" / "v1"
    cert_docs = ["V1_CERTIFICATION_STANDARD.md", "V1_READINESS_ASSESSMENT.md",
                 "V1_AUDIT_FRAMEWORK.md", "V1_RISK_REVIEW.md", "V1_GAP_ANALYSIS.md",
                 "V1_EXIT_CRITERIA.md", "V1_COMPLETION_REPORT.md", "V2_READINESS_GATE.md"]
    have = all((cert / d).exists() for d in cert_docs)
    verdict = (cert / "V1_COMPLETION_REPORT.md").read_text().find("CERTIFIED") != -1 if have else False
    check("certification audit completes", have and verdict, f"{len(cert_docs)} docs + verdict")

    # 15. V0 quality gate — boundary scan (do #15 before #14 for ordering clarity)
    boundary_ok, boundary_detail = _boundary_scan()
    check("V0 quality gates pass (boundaries/NR-8)", boundary_ok, boundary_detail)

    # 14. All tests pass (authoritative pytest gate)
    pytest_ok = _run_pytest()
    check("all tests pass (pytest)", pytest_ok)

    width = max(len(n) for n, _, _ in checks)
    all_ok = True
    print("=== V1-P7 + V1-P8 + Certification — Final Validation ===")
    for i, (name, ok, detail) in enumerate(checks, 1):
        all_ok = all_ok and ok
        print(f"[{'PASS' if ok else 'FAIL'}] {i:2d}. {name.ljust(width)}  {detail}")
    print("\nRESULT:", "ALL CRITERIA SATISFIED" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


def _boundary_scan() -> tuple[bool, str]:
    domain = {"ml", "evaluation", "datasets", "preprocessing", "backend",
              "monitoring", "deployment"}

    def imports(path):
        found = set()
        tree = ast.parse(path.read_text())
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    found.add(a.name.split(".")[0])
            elif isinstance(n, ast.ImportFrom) and (n.level or 0) == 0 and n.module:
                found.add(n.module.split(".")[0])
        return found

    violations = []
    for p in (REPO / "ml").rglob("*.py"):
        if "evaluation" in imports(p):
            violations.append(f"ml->evaluation in {p.name}")
    for p in (REPO / "backend").rglob("*.py"):
        if "frontend" in imports(p):
            violations.append(f"backend->frontend in {p.name}")
    for p in (REPO / "frontend").rglob("*.py"):
        leaked = imports(p) & domain
        if leaked:
            violations.append(f"frontend->{sorted(leaked)} in {p.name}")
    for p in (REPO / "preprocessing").rglob("*.py"):
        leaked = imports(p) & (domain - {"preprocessing"})
        if leaked:
            violations.append(f"preprocessing->{sorted(leaked)} in {p.name}")
    return (not violations), ("clean" if not violations else "; ".join(violations))


def _run_pytest() -> bool:
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                              cwd=str(REPO), capture_output=True, text=True, timeout=600)
        return proc.returncode == 0
    except Exception:
        return False


if __name__ == "__main__":
    sys.exit(main())
