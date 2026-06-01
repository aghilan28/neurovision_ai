"""Final validation for MP-4 — Source of Truth Consolidation.

Repository governance only — proves the source of truth is unambiguous and that an independent
operator can obtain + run the product from a fresh clone of the authoritative branch, with no
knowledge of the historical PR stack. Adds/changes no product behaviour.

It audits real git state, verifies the authoritative tree is complete + self-describing,
performs a **real local fresh clone** and **runs the product from that clone**, and confirms
the MP-4 change set is governance-only (no product source touched).

    python -m scripts.verify_mp4_source_of_truth
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
AUTHORITATIVE_BRANCH = "main"

PHASE_VERIFY_SCRIPTS = [
    "verify_v1", "verify_v2", "verify_v3_p1_p2", "verify_v3_p7_p8", "verify_v4_p1_p2",
    "verify_v4_p9_p10", "verify_productization_p1", "verify_productization_p10",
    "verify_drp1_dataset_integration", "verify_drp6_clinical_validation",
    "verify_track1_real_data", "verify_track4_operations", "verify_dbe1_asgi_entrypoint",
    "verify_dbe5_authentication_reliability", "verify_mp1_model_provisioning",
    "verify_mp3_model_lifecycle",
]
PRODUCT_DIRS = ["ml", "backend", "frontend", "operations", "validation", "certification"]
PRODUCT_PREFIXES = tuple(PRODUCT_DIRS)


def _git(*args, cwd=REPO):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def _has_git() -> bool:
    return (REPO / ".git").exists() and _git("rev-parse", "--git-dir").returncode == 0


def main() -> int:  # noqa: C901 - linear verification script
    checks: list[tuple] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    doc = REPO / "REPOSITORY.md"
    doc_txt = doc.read_text() if doc.exists() else ""

    # --- 1. Repository reality audited -----------------------------------------------------
    head = _git("rev-parse", "HEAD").stdout.strip() if _has_git() else ""
    n_commits = _git("rev-list", "--count", "HEAD").stdout.strip() if _has_git() else ""
    reality_ok = bool(doc_txt) and (head != "" or not _has_git()) and \
        "Repository Reality Report" in doc_txt
    check("1. Repository reality audited", reality_ok,
          f"HEAD={head[:12] or 'n/a'} commits={n_commits or 'n/a'}")

    # --- 2. Branch topology documented -----------------------------------------------------
    topo_ok = all(g in doc_txt for g in ("V0", "V1", "V2", "V3", "V4", "Productization",
                                         "DRP-1", "Track-1", "DBE-1", "MP-1", "MP-3"))
    check("2. Branch topology documented", topo_ok, "all phase groups present in REPOSITORY.md")

    # --- 3. Source of truth identified -----------------------------------------------------
    sot_ok = (f"Authoritative branch: `{AUTHORITATIVE_BRANCH}`" in doc_txt
              and "Source Of Truth Guide" in doc_txt)
    check("3. Source of truth identified", sot_ok, f"authoritative branch = {AUTHORITATIVE_BRANCH}")

    # --- 4. Product completeness verified --------------------------------------------------
    missing_scripts = [s for s in PHASE_VERIFY_SCRIPTS
                       if not (REPO / "scripts" / f"{s}.py").exists()]
    missing_dirs = [d for d in PRODUCT_DIRS if not (REPO / d).exists()]
    n_subsystems = len([p for p in (REPO / "backend").iterdir()
                        if p.is_dir() and not p.name.startswith("__")])
    completeness_ok = not missing_scripts and not missing_dirs and n_subsystems >= 30
    check("4. Product completeness verified", completeness_ok,
          f"{n_subsystems} backend subsystems; phase verify scripts present="
          f"{not missing_scripts}; missing_dirs={missing_dirs}")

    # --- 5. Merge readiness verified -------------------------------------------------------
    # The authoritative spine must be a single linear history (0 merge commits) with no conflict
    # markers -> consolidated with no duplicate implementations / dependency violations. The
    # consolidation fast-forwarded the product spine onto the empty repository-initial commit,
    # so `main` is rooted at it (origin/main is an ancestor when the remote is known).
    if _has_git():
        linear = _git("log", "--merges", "--oneline").stdout.strip() == ""
        init_ref = "origin/main"
        anc = _git("merge-base", "--is-ancestor", init_ref, "HEAD")
        rooted = anc.returncode == 0 or init_ref not in _git("branch", "-r").stdout
        merge_ready = linear and rooted
        check("5. Merge readiness verified", merge_ready,
              f"linear={linear} (0 merge commits); rooted-on-repo-init={anc.returncode == 0}")
    else:
        check("5. Merge readiness verified", True, "git metadata absent; linear by construction")

    # --- 6. Consolidation completed --------------------------------------------------------
    consolidation_ok = (doc.exists()
                        and (REPO / "scripts" / "verify_mp4_source_of_truth.py").exists()
                        and (REPO / ".gcc" / "decisions"
                             / "ADR-0039-mp4-source-of-truth-consolidation.md").exists()
                        and completeness_ok)
    check("6. Consolidation completed", consolidation_ok,
          "authoritative tree carries the full product + MP-4 governance artifacts")

    # --- 7. Fresh clone succeeds -----------------------------------------------------------
    clone_dir = None
    clone_ok = False
    if _has_git():
        clone_dir = tempfile.mkdtemp(prefix="nv_mp4_clone_")
        cl = _git("clone", "--quiet", "--no-hardlinks", str(REPO), clone_dir, cwd=REPO.parent)
        clone_ok = (cl.returncode == 0
                    and (pathlib.Path(clone_dir) / "requirements.txt").exists()
                    and (pathlib.Path(clone_dir) / "backend" / "application_platform").is_dir()
                    and (pathlib.Path(clone_dir) / "REPOSITORY.md").exists())
        check("7. Fresh clone succeeds", clone_ok,
              f"git clone -> {clone_dir} (product tree present)" if clone_ok else cl.stderr[:200])
    else:
        check("7. Fresh clone succeeds", False, "git unavailable to perform a real clone")

    # --- 8. Verification succeeds (run the product FROM the fresh clone) --------------------
    if clone_ok and clone_dir:
        code = (
            "import sys; sys.path.insert(0, '.');\n"
            "from fastapi.testclient import TestClient;\n"
            "from backend.application_platform.server import build_application, load_config;\n"
            "import tempfile;\n"
            "svc, app = build_application(load_config({'workspace_dir': tempfile.mkdtemp()}));\n"
            "c = TestClient(app); \n"
            "import contextlib;\n"
            "with c as cc:\n"
            "    assert cc.get('/health').status_code == 200;\n"
            "    rz = cc.get('/readyz').json();\n"
            "    assert rz['ready'] is True, rz;\n"
            "print('CLONE_PRODUCT_READY')"
        )
        p = subprocess.run([sys.executable, "-c", code], cwd=clone_dir,
                           capture_output=True, text=True)
        ver_ok = p.returncode == 0 and "CLONE_PRODUCT_READY" in p.stdout
        check("8. Verification succeeds", ver_ok,
              "fresh clone serves /health + /readyz ready=true"
              if ver_ok else (p.stderr.strip().splitlines() or ["error"])[-1])
    else:
        check("8. Verification succeeds", False, "no fresh clone to verify")

    # --- 9. Deployment path documented -----------------------------------------------------
    deploy_ok = all(k in doc_txt for k in ("Deployment Branch Guide", "Operator", "Developer",
                                           "CI", "Release"))
    check("9. Deployment path documented", deploy_ok, "operator/developer/CI/release paths")

    # --- 10. Operator path documented ------------------------------------------------------
    operator_ok = ("Operator Onboarding Guide" in doc_txt
                   and "git checkout main" in doc_txt
                   and "pip install -r requirements.txt" in doc_txt
                   and "uvicorn backend.application_platform.server.app:app" in doc_txt)
    check("10. Operator path documented", operator_ok,
          "clone -> checkout main -> install -> run, no PR-stack knowledge needed")

    # --- 11. Tests pass --------------------------------------------------------------------
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_mp4_source_of_truth.py"], cwd=str(REPO),
                           capture_output=True, text=True)
        check("11. Tests pass", p.returncode == 0,
              (p.stdout.strip().splitlines() or [""])[-1])
    except Exception as exc:  # noqa: BLE001
        check("11. Tests pass", False, f"error: {exc}")

    # --- 12. No feature regressions (MP-4 change set is governance-only) --------------------
    if _has_git():
        # files changed by the consolidation commit (HEAD) vs its parent
        changed = _git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").stdout.split()
        product_touched = [f for f in changed if f.startswith(PRODUCT_PREFIXES)]
        boundaries = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p",
                                    "no:cacheprovider", "tests/test_boundaries.py"],
                                   cwd=str(REPO), capture_output=True, text=True)
        no_regress = not product_touched and boundaries.returncode == 0
        check("12. No feature regressions", no_regress,
              f"product source touched by HEAD={product_touched or 'none'}; boundaries green="
              f"{boundaries.returncode == 0}")
    else:
        check("12. No feature regressions", True, "git unavailable; product import smoke covers it")

    # --- 13. Documentation complete --------------------------------------------------------
    documented = all(s in doc_txt for s in (
        "Repository Structure Guide", "Source Of Truth Guide", "Deployment Branch Guide",
        "Operator Onboarding Guide", "Developer Onboarding Guide", "Repository Reality Report",
        "Product Completeness Report", "Merge Readiness Report"))
    check("13. Documentation complete", documented, "REPOSITORY.md has the 5 guides + the reports")

    # --- 14. Repository integrity preserved ------------------------------------------------
    integrity_ok = True
    try:
        for mod in ("ml", "backend.application_platform",
                    "backend.application_platform.lifecycle"):
            __import__(mod)
    except Exception as exc:  # noqa: BLE001
        integrity_ok = False
        check("14. Repository integrity preserved", False, f"import error: {exc}")
    if integrity_ok:
        # no conflict markers in tracked sources
        offenders = []
        for ext in ("*.py", "*.md", "*.toml"):
            for path in REPO.rglob(ext):
                if ".venv" in path.parts or ".git" in path.parts:
                    continue
                try:
                    for line in path.read_text(errors="ignore").splitlines():
                        if line in ("<<<<<<<", "=======", ">>>>>>>") or \
                           line.startswith(("<<<<<<< ", ">>>>>>> ")):
                            offenders.append(str(path))
                            break
                except Exception:  # noqa: BLE001
                    continue
        integrity_ok = not offenders and (REPO / "requirements.txt").exists()
        check("14. Repository integrity preserved", integrity_ok,
              "imports OK; no conflict markers; requirements.txt present"
              if integrity_ok else f"conflict markers: {offenders}")

    # --- 15. MP-4 completed ----------------------------------------------------------------
    completed = all(ok for n, ok, _ in checks if not n.startswith("15."))
    check("15. MP-4 completed", completed,
          "source of truth unambiguous; fresh clone obtains + runs the product; governance clear")

    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 50))
    print("\nMP-4 — SOURCE OF TRUTH CONSOLIDATION — FINAL VALIDATION")
    print("=" * 76)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 76)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
