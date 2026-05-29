"""Tests for the offline inference platform (V1-P7).

Covers: execution engine (status/timing/failure/recovery), the 15-stage
orchestrator end to end, registry, lineage, artifacts, validation, reports, output
contracts, and deterministic reproducibility.
"""

from __future__ import annotations

import json
import os

import pytest

from backend.offline_inference import (
    InferenceOrchestrator, PipelineConfig, FakeClock,
    ExecutionEngine, Stage, ExecutionStatus, InferenceValidator,
)
from backend.offline_inference.artifacts import verify_directory
from datasets import SyntheticConfig
from ml.training import TrainingConfig


# --- execution engine ---------------------------------------------------------
def test_execution_engine_runs_stages_in_order():
    engine = ExecutionEngine("test-pipeline@1", clock=FakeClock())
    ctx = {"trace": []}

    def make(name):
        def run(c):
            c["trace"].append(name)
            return {"signature": name}
        return Stage(name, "v1", run)

    result = engine.execute([make("a"), make("b"), make("c")], ctx)
    assert result.ok and ctx["trace"] == ["a", "b", "c"]
    assert [s.status for s in result.stages] == [ExecutionStatus.SUCCEEDED] * 3


def test_execution_engine_captures_failure_state():
    engine = ExecutionEngine("test-pipeline@1", clock=FakeClock())

    def boom(c):
        raise RuntimeError("stage exploded")

    def ok(c):
        return {"signature": "ok"}

    result = engine.execute([Stage("ok1", "v1", ok), Stage("bad", "v1", boom),
                             Stage("never", "v1", ok)], {})
    assert not result.ok
    assert result.status == ExecutionStatus.FAILED
    assert result.failed_stage == "bad"
    # the stage after the failure never ran
    assert [s.name for s in result.stages] == ["ok1", "bad"]


def test_execution_engine_recovery_resumes_after_failure():
    engine = ExecutionEngine("test-pipeline@1", clock=FakeClock())
    state = {"fail_once": True}

    def ok(c):
        return {"signature": "ok"}

    def flaky(c):
        if state["fail_once"]:
            raise RuntimeError("transient")
        return {"signature": "recovered"}

    stages = [Stage("a", "v1", ok), Stage("flaky", "v1", flaky), Stage("c", "v1", ok)]
    ctx: dict = {}
    first = engine.execute(stages, ctx)
    assert first.status == ExecutionStatus.FAILED and first.failed_stage == "flaky"

    # fix the transient condition and resume, skipping the already-succeeded stage
    state["fail_once"] = False
    second = engine.execute(stages, ctx, skip=frozenset(first.succeeded_stage_names()))
    assert second.ok and second.recovered
    statuses = {s.name: s.status for s in second.stages}
    assert statuses["a"] == ExecutionStatus.RECOVERED
    assert statuses["flaky"] == ExecutionStatus.SUCCEEDED


# --- orchestrator end to end --------------------------------------------------
def test_orchestrator_runs_15_stages(offline_run):
    result, _ = offline_run
    assert result.execution.ok
    assert len(result.execution.stages) == 15
    names = [s.name for s in result.execution.stages]
    assert names[0] == "dataset_ingestion" and names[-1] == "audit_generation"
    assert all(s.status == ExecutionStatus.SUCCEEDED for s in result.execution.stages)


def test_orchestrator_validation_passes(offline_run):
    result, _ = offline_run
    assert result.validation["ok"] is True
    names = {c["name"] for c in result.validation["checks"]}
    assert {"version_consistency", "artifact_integrity", "lineage_integrity",
            "calibration_integrity", "coverage_integrity", "output_integrity",
            "audit_integrity"}.issubset(names)


def test_inference_registered_and_lineage_verifies(offline_run):
    result, _ = offline_run
    reg = result.registries["inference"]
    assert reg.list_inferences() == [result.inference_id]
    assert result.registries["lineage"].verify_chain(result.lineage_id) is True


def test_output_contracts_present(offline_run):
    result, _ = offline_run
    for name in ["prediction", "probability", "calibration", "conformal",
                 "coverage", "risk", "clinical", "summary"]:
        assert name in result.outputs
    # clinical output is per-window and carries uncertainty (NR-4)
    clinical = result.outputs["clinical"]
    assert clinical["n"] == result.outputs["prediction"]["n"]
    assert all("conformal_set" in r and "risk_band" in r for r in clinical["records"][:5])


def test_artifacts_written_and_verified(offline_run):
    result, out = offline_run
    ok, details = verify_directory(out)
    assert ok and details["mismatched"] == [] and details["missing"] == []
    # the index references existing files
    idx = json.load(open(os.path.join(out, "inference_index.json")))
    for group in ("outputs", "reports", "registries"):
        for rel in idx[group].values():
            assert os.path.exists(os.path.join(out, rel))


def test_reports_generated(offline_run):
    _, out = offline_run
    idx = json.load(open(os.path.join(out, "inference_index.json")))
    assert set(idx["reports"]) >= {"inference_report", "calibration_report",
                                   "coverage_report", "risk_report", "summary_report",
                                   "audit_report"}


def test_silent_modification_detected(offline_run, tmp_path):
    import shutil
    _, out = offline_run
    clone = tmp_path / "clone"
    shutil.copytree(out, clone)
    # tamper with a registered artifact
    victim = os.path.join(clone, "outputs", "summary_output.json")
    with open(victim, "ab") as fh:
        fh.write(b"   ")
    ok, details = verify_directory(str(clone))
    assert ok is False and details["mismatched"]


def test_pipeline_is_reproducible(tmp_path):
    cfg = _cfg()
    r1 = InferenceOrchestrator(cfg, output_dir=str(tmp_path / "a"), clock=FakeClock()).run()
    r2 = InferenceOrchestrator(cfg, output_dir=str(tmp_path / "b"), clock=FakeClock()).run()
    assert r1.inference_id == r2.inference_id
    assert r1.execution.content_signature() == r2.execution.content_signature()
    assert r1.outputs["summary"]["headline"] == r2.outputs["summary"]["headline"]


def _cfg() -> PipelineConfig:
    return PipelineConfig(synthetic=SyntheticConfig(n_patients=12, windows_per_patient=18),
                          training=TrainingConfig(steps=60), model_name="simple_cnn")
