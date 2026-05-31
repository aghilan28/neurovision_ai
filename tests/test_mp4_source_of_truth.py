"""MP-4 — Source of Truth Consolidation tests (repository governance, not product features).

These assert *repository truth*: the authoritative tree is complete and self-describing, the
history is a clean linear spine, documentation names the source of truth, there are no broken
references / conflict markers, and the product still imports + runs. They are filesystem- and
import-based so they pass in any fresh checkout; git-based checks are best-effort (skipped when
git metadata is absent, e.g. an exported tarball).
"""

from __future__ import annotations

import importlib
import pathlib
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]

# Every roadmap phase must be represented by its verification script in the authoritative tree.
PHASE_VERIFY_SCRIPTS = [
    "verify_v1", "verify_v2", "verify_v3_p1_p2", "verify_v4_p1_p2", "verify_v4_p9_p10",
    "verify_productization_p1", "verify_productization_p10",
    "verify_drp1_dataset_integration", "verify_drp6_clinical_validation",
    "verify_track1_real_data", "verify_track4_operations",
    "verify_dbe1_asgi_entrypoint", "verify_dbe5_authentication_reliability",
    "verify_mp1_model_provisioning", "verify_mp3_model_lifecycle",
]

# Representative subsystem packages spanning the whole product.
PRODUCT_PACKAGES = [
    "ml", "backend.eeg_foundation", "backend.signal_processing", "backend.feature_engineering",
    "backend.model_foundation", "backend.inference_foundation", "backend.application_backend",
    "backend.application_platform", "backend.application_platform.lifecycle",
    "backend.application_platform.provisioning", "backend.real_model_training",
    "backend.serving_platform", "backend.persistence_platform", "backend.security_platform",
]

REQUIRED_DOC_SECTIONS = [
    "Source Of Truth Guide", "Repository Structure Guide", "Deployment Branch Guide",
    "Operator Onboarding Guide", "Developer Onboarding Guide",
    "Repository Reality Report", "Product Completeness Report", "Merge Readiness Report",
]


def _git(*args):
    return subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True)


def _has_git() -> bool:
    return (REPO / ".git").exists() and _git("rev-parse", "--git-dir").returncode == 0


# --- MP4-B/H: the repository names its source of truth -----------------------------------
def test_repository_md_exists_and_names_authoritative_branch():
    doc = REPO / "REPOSITORY.md"
    assert doc.exists(), "REPOSITORY.md (source-of-truth doc) must exist at the repo root"
    txt = doc.read_text()
    assert "Authoritative branch: `main`" in txt
    for section in REQUIRED_DOC_SECTIONS:
        assert section in txt, f"REPOSITORY.md missing section: {section}"


def test_topology_documents_every_phase_group():
    txt = (REPO / "REPOSITORY.md").read_text()
    for group in ("V0", "V1", "V2", "V3", "V4", "Productization", "DRP-1", "Track-1",
                  "DBE-1", "MP-1", "MP-3"):
        assert group in txt, f"topology missing phase group: {group}"


# --- MP4-C: product completeness ----------------------------------------------------------
def test_all_phase_verify_scripts_present():
    missing = [s for s in PHASE_VERIFY_SCRIPTS if not (REPO / "scripts" / f"{s}.py").exists()]
    assert not missing, f"missing phase verification scripts: {missing}"


def test_core_product_layers_present():
    for path in ("ml", "backend", "frontend", "operations", "validation", "certification",
                 "requirements.txt", "pyproject.toml", "scripts", "tests"):
        assert (REPO / path).exists(), f"authoritative tree missing: {path}"
    # backend must carry the full set of governed subsystems (>= 30 of the 37)
    subsystems = [p for p in (REPO / "backend").iterdir()
                  if p.is_dir() and not p.name.startswith("__")]
    assert len(subsystems) >= 30, f"too few backend subsystems: {len(subsystems)}"


# --- MP4-I: repository integrity ----------------------------------------------------------
@pytest.mark.parametrize("module", PRODUCT_PACKAGES)
def test_product_packages_import(module):
    assert importlib.import_module(module) is not None


def test_no_conflict_markers_in_tracked_sources():
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
    assert not offenders, f"conflict markers found in: {offenders}"


def test_verify_mp4_script_and_adr_present():
    assert (REPO / "scripts" / "verify_mp4_source_of_truth.py").exists()
    assert (REPO / ".gcc" / "decisions"
            / "ADR-0039-mp4-source-of-truth-consolidation.md").exists()


# --- MP4-D / MP4-A: history is a clean linear spine (best-effort; needs git) ---------------
def test_history_is_linear_no_merge_commits():
    if not _has_git():
        pytest.skip("git metadata unavailable (exported tree)")
    merges = _git("log", "--merges", "--oneline").stdout.strip()
    assert merges == "", f"unexpected merge commits on the product spine:\n{merges}"


def test_product_runs_end_to_end(tmp_path):
    # The strongest integrity check: the consolidated tree actually serves the product.
    from fastapi.testclient import TestClient

    from backend.application_platform.server import build_application, load_config

    _svc, app = build_application(load_config({"workspace_dir": str(tmp_path)}))
    with TestClient(app) as c:
        assert c.get("/health").status_code == 200
        assert c.get("/readyz").json()["ready"] is True
