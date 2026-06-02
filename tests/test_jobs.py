"""Tests for the offline-inference job system (V1-P7)."""

from __future__ import annotations

import pytest

from backend.offline_inference import (
    JobRunner, JobStatus, InferenceJob, BatchJob, ValidationJob, AuditJob,
    ArtifactJob, ReportJob, PipelineConfig, FakeClock,
)
from datasets import SyntheticConfig
from ml.training import TrainingConfig


def _cfg(seed=7):
    return PipelineConfig(synthetic=SyntheticConfig(n_patients=12, windows_per_patient=18),
                          training=TrainingConfig(steps=50), model_seed=seed)


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory):
    out = tmp_path_factory.mktemp("jobs_run")
    runner = JobRunner(clock=FakeClock())
    res = runner.run(InferenceJob(_cfg(), output_dir=str(out / "run1"), clock=FakeClock()))
    assert res.status == JobStatus.SUCCEEDED
    return str(out / "run1")


def test_inference_job_runs_and_is_versioned(tmp_path):
    runner = JobRunner(clock=FakeClock())
    job = InferenceJob(_cfg(), output_dir=str(tmp_path / "r"), clock=FakeClock())
    assert job.job_id.startswith("job-inference+")
    res = runner.run(job)
    assert res.status == JobStatus.SUCCEEDED
    assert res.payload["validation_ok"] is True
    assert res.signature  # traceable content signature


def test_validation_audit_artifact_report_jobs(run_dir):
    runner = JobRunner(clock=FakeClock())
    vr = runner.run(ValidationJob(run_dir))
    assert vr.payload["overall_ok"] is True
    ar = runner.run(AuditJob(run_dir))
    assert ar.payload["traceable"] is True and ar.payload["lineage_chain_length"] >= 3
    af = runner.run(ArtifactJob(run_dir))
    assert af.payload["integrity_ok"] is True
    rr = runner.run(ReportJob(run_dir))
    assert rr.payload["all_present"] is True


def test_batch_job_runs_multiple_and_is_recoverable(tmp_path):
    runner = JobRunner(clock=FakeClock())
    bj = BatchJob([_cfg(7), _cfg(9)], output_root=str(tmp_path / "batch"), clock=FakeClock())
    res = runner.run(bj)
    assert res.status == JobStatus.SUCCEEDED
    assert res.payload["n_completed"] == 2
    assert len(res.payload["inference_ids"]) == 2


def test_artifact_job_detects_tamper(run_dir, tmp_path):
    import os, shutil
    clone = tmp_path / "clone"
    shutil.copytree(run_dir, clone)
    with open(os.path.join(clone, "outputs", "risk_output.json"), "ab") as fh:
        fh.write(b" ")
    runner = JobRunner(clock=FakeClock())
    res = runner.run(ArtifactJob(str(clone)))
    assert res.payload["integrity_ok"] is False


def test_job_runner_records_history(run_dir):
    runner = JobRunner(clock=FakeClock())
    runner.run(ArtifactJob(run_dir))
    runner.run(AuditJob(run_dir))
    d = runner.to_dict()
    assert d["n_jobs"] == 2 and d["job_system_version"]
