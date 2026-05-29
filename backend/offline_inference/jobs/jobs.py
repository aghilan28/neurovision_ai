"""Job system: versioned, traceable, recoverable, auditable units of work."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ml.provenance import content_id, hash_obj  # allowed: backend -> ml

from ..version import JOB_SYSTEM_VERSION, DETERMINISTIC_EPOCH
from ..pipelines import PipelineConfig
from ..orchestrator import InferenceOrchestrator
from ..artifacts import verify_directory
from ..validation import InferenceValidator
from ..execution import Clock, RealClock


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RECOVERED = "recovered"


@dataclass
class JobResult:
    job_id: str
    job_type: str
    status: JobStatus
    signature: Optional[str]
    duration_s: float
    payload: dict = field(default_factory=dict)
    error: Optional[str] = None
    job_system_version: str = JOB_SYSTEM_VERSION

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status.value,
            "signature": self.signature,
            "duration_s": round(float(self.duration_s), 6),  # non-hashed metadata
            "error": self.error,
            "job_system_version": self.job_system_version,
            "payload": self.payload,
        }


class Job:
    """Base class. Subclasses implement ``execute(context) -> payload dict``."""

    job_type: str = "job"

    def __init__(self, spec: dict):
        self.spec = spec
        self.job_id = content_id(f"job-{self.job_type}", spec)

    def execute(self, context: dict) -> dict:  # returns payload (must be JSON-able)
        raise NotImplementedError


class InferenceJob(Job):
    job_type = "inference"

    def __init__(self, config: PipelineConfig, output_dir: Optional[str] = None,
                 clock: Optional[Clock] = None, dataset=None):
        self.config = config
        self.output_dir = output_dir
        self.clock = clock
        self.dataset = dataset
        super().__init__({"config": config.as_dict(), "output_dir": output_dir})

    def execute(self, context: dict) -> dict:
        orch = InferenceOrchestrator(self.config, output_dir=self.output_dir,
                                     clock=self.clock, dataset=self.dataset)
        result = orch.run()
        context["last_result"] = result
        return {
            "inference_id": result.inference_id,
            "output_dir": result.output_dir,
            "validation_ok": result.validation["ok"],
            "execution_status": result.execution.status.value,
            "headline": result.outputs["summary"]["headline"],
            "lineage_id": result.lineage_id,
        }


class BatchJob(Job):
    job_type = "batch"

    def __init__(self, configs: list[PipelineConfig], output_root: str,
                 clock: Optional[Clock] = None):
        self.configs = configs
        self.output_root = output_root
        self.clock = clock
        super().__init__({"configs": [c.as_dict() for c in configs], "output_root": output_root})

    def execute(self, context: dict) -> dict:
        completed = set(context.get("completed_subjobs", []))  # recovery support
        results = dict(context.get("subjob_results", {}))
        for i, cfg in enumerate(self.configs):
            key = content_id("batch-item", cfg.as_dict())
            if key in completed:
                continue  # already done in a prior (partial) run — recover/skip
            job = InferenceJob(cfg, output_dir=os.path.join(self.output_root, key), clock=self.clock)
            payload = job.execute(context)
            results[key] = payload
            completed.add(key)
        context["completed_subjobs"] = sorted(completed)
        context["subjob_results"] = results
        return {"n_configs": len(self.configs), "n_completed": len(completed),
                "inference_ids": sorted(p["inference_id"] for p in results.values())}


class ValidationJob(Job):
    job_type = "validation"

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        super().__init__({"output_dir": output_dir})

    def execute(self, context: dict) -> dict:
        idx = _load(self.output_dir, "inference_index.json")
        store_ok, details = verify_directory(self.output_dir)
        # the run already recorded its own validation; re-affirm + re-check integrity
        return {
            "inference_id": idx["inference_id"],
            "recorded_validation_ok": idx["validation"]["ok"],
            "artifact_integrity_ok": store_ok,
            "artifact_details": details,
            "overall_ok": bool(idx["validation"]["ok"] and store_ok),
        }


class AuditJob(Job):
    job_type = "audit"

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        super().__init__({"output_dir": output_dir})

    def execute(self, context: dict) -> dict:
        audit = _load(self.output_dir, "reports/audit_report.json")
        lineage = _load(self.output_dir, "registries/lineage.json")
        return {
            "inference_id": audit["inference_id"],
            "traceable": audit["traceable"],
            "lineage_records": lineage["n_records"],
            "lineage_chain_length": len(audit["lineage_chain"]),
        }


class ArtifactJob(Job):
    job_type = "artifact"

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        super().__init__({"output_dir": output_dir})

    def execute(self, context: dict) -> dict:
        ok, details = verify_directory(self.output_dir)
        return {"integrity_ok": ok, **details}


class ReportJob(Job):
    job_type = "report"

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        super().__init__({"output_dir": output_dir})

    def execute(self, context: dict) -> dict:
        idx = _load(self.output_dir, "inference_index.json")
        present = {}
        for name, rel in idx["reports"].items():
            present[name] = os.path.exists(os.path.join(self.output_dir, rel))
        return {"reports": present, "all_present": all(present.values())}


class JobRunner:
    """Executes jobs, records results, and supports retry/recovery."""

    def __init__(self, clock: Optional[Clock] = None):
        self.clock = clock or RealClock()
        self._results: dict[str, JobResult] = {}
        self._context: dict = {}

    def run(self, job: Job) -> JobResult:
        t0 = self.clock.now()
        prior = self._results.get(job.job_id)
        try:
            payload = job.execute(self._context)
            dur = self.clock.now() - t0
            status = JobStatus.RECOVERED if (prior and prior.status == JobStatus.FAILED) else JobStatus.SUCCEEDED
            result = JobResult(job.job_id, job.job_type, status,
                               hash_obj(payload), dur, payload=payload)
        except Exception as exc:
            dur = self.clock.now() - t0
            result = JobResult(job.job_id, job.job_type, JobStatus.FAILED, None, dur, error=repr(exc))
        self._results[job.job_id] = result
        return result

    def results(self) -> dict[str, JobResult]:
        return dict(self._results)

    def to_dict(self) -> dict:
        return {
            "job_system_version": JOB_SYSTEM_VERSION,
            "n_jobs": len(self._results),
            "jobs": {jid: r.to_dict() for jid, r in sorted(self._results.items())},
        }


def _load(root: str, rel: str):
    with open(os.path.join(root, rel), "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))
