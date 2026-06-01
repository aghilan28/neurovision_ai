"""``validation/benchmarking`` — benchmarking framework (P9-B).

Deterministic, repeatable, auditable benchmark runners over the real platform: model,
pipeline, inference, workflow, and operational. Each run records **deterministic**
evidence (success/failure counts, output fingerprints, model metrics) and
**informational** performance measures (latency / throughput / peak memory) that are
explicitly excluded from the result signature, so the *result* is reproducible while the
*timings* are reported but never hashed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from ..util import fingerprint, peak_memory_kb, population_stats
from ..version import VALIDATION_BENCHMARK_VERSION


@dataclass
class BenchmarkResult:
    name: str
    runs: int
    successes: int
    failures: int
    output_fingerprints: tuple                 # deterministic per run
    latency_ms: list = field(default_factory=list)        # informational
    peak_memory_kb: int = 0                                # informational
    extra: dict = field(default_factory=dict)             # deterministic metric payload

    @property
    def success_rate(self) -> float:
        return self.successes / self.runs if self.runs else 0.0

    @property
    def failure_rate(self) -> float:
        return self.failures / self.runs if self.runs else 0.0

    @property
    def deterministic(self) -> bool:
        """A benchmark is deterministic iff every run produced the same output fingerprint."""
        return len(set(self.output_fingerprints)) <= 1

    def signature(self) -> str:
        # NOTE: latency/memory are NOT included — only deterministic evidence.
        return fingerprint({"name": self.name, "runs": self.runs, "successes": self.successes,
                            "fingerprints": sorted(set(self.output_fingerprints)),
                            "extra": self.extra})

    def to_dict(self) -> dict:
        lat = population_stats(self.latency_ms)
        return {
            "name": self.name, "runs": self.runs, "successes": self.successes,
            "failures": self.failures, "success_rate": self.success_rate,
            "failure_rate": self.failure_rate, "deterministic": self.deterministic,
            "latency_ms": lat,
            "throughput_per_s": (1000.0 / lat["mean"]) if lat["mean"] > 0 else 0.0,
            "peak_memory_kb": self.peak_memory_kb, "extra": self.extra,
            "signature": self.signature(),
        }


def run_benchmark(name: str, fn: Callable, *, runs: int = 3) -> BenchmarkResult:
    """Run ``fn`` ``runs`` times. ``fn`` returns (success: bool, output_fingerprint: str)."""
    successes = failures = 0
    fps: list = []
    lat: list = []
    peak = 0
    for _ in range(runs):
        t = time.perf_counter()
        try:
            ok, fp = fn()
        except Exception as exc:                # a benchmark step must never crash the runner
            ok, fp = False, f"error:{type(exc).__name__}"
        lat.append((time.perf_counter() - t) * 1000)
        fps.append(fp)
        successes += 1 if ok else 0
        failures += 0 if ok else 1
    peak = peak_memory_kb()
    return BenchmarkResult(name, runs, successes, failures, tuple(fps), lat, peak)


# =============================================================================
# Runners
# =============================================================================
class ModelBenchmarkRunner:
    """Benchmarks the trained baseline models (reuses harness.train_models — P4)."""

    def run(self, harness, feats, architectures, *, seed: int = 7) -> dict:
        from ..util import fingerprint as _fp
        muts = harness.train_models(feats, architectures, seed=seed)
        per_model = {}
        for arch, mut in muts.items():
            ev = mut.evaluation
            metrics = {
                "accuracy": ev["metrics"]["accuracy"], "precision_macro": ev["metrics"]["precision_macro"],
                "recall_macro": ev["metrics"]["recall_macro"], "f1_macro": ev["metrics"]["f1_macro"],
                "ece": ev["calibration"]["ece"], "brier": ev["calibration"]["brier"],
                "mean_entropy": ev["uncertainty"]["mean_entropy"],
                "mean_confidence": ev["uncertainty"]["mean_confidence"],
                "confusion_matrix": ev["confusion_matrix"],
            }
            per_model[arch] = {"model_id": mut.model_id, "metrics": metrics,
                               "signature": _fp({"model_id": mut.model_id, "metrics": metrics})}
        return {"benchmark": "model", "benchmark_version": VALIDATION_BENCHMARK_VERSION,
                "models": per_model, "muts": muts}


class PipelineBenchmarkRunner:
    """Benchmarks the full ingest->process->features->predict pipeline (P1->P5)."""

    def run(self, harness, eeg_file: str, mut, *, runs: int = 3) -> BenchmarkResult:
        def one():
            res = harness.run_pipeline(eeg_file, mut, patient_key="bench-p", case_key="bench-c")
            return res.success and res.traceable, res.output_fingerprint()
        result = run_benchmark("pipeline", one, runs=runs)
        return result


class InferenceBenchmarkRunner:
    """Benchmarks the inference stage (P5) on a fixed feature asset."""

    def run(self, harness, feature_asset, mut, *, runs: int = 3) -> BenchmarkResult:
        def one():
            out = harness.svc.inference_service.predict(
                mut.model, feature_asset, train_feature_records=list(mut.train_feature_records),
                dataset_key=mut.dataset_key)
            return out.accepted, (out.asset.prediction_id if out.asset else "none")
        return run_benchmark("inference", one, runs=runs)


class WorkflowBenchmarkRunner:
    """Benchmarks one application workflow unit (the orchestrated pipeline)."""

    def run(self, harness, eeg_file: str, mut, *, runs: int = 3) -> BenchmarkResult:
        def one():
            res = harness.run_pipeline(eeg_file, mut, patient_key="wf-p", case_key="wf-c")
            return res.success, fingerprint({"stages": [s.ok for s in res.stages],
                                            "prediction": res.prediction_id})
        return run_benchmark("workflow", one, runs=runs)


class OperationalBenchmarkRunner:
    """Benchmarks the operational health stack (reuses operations.HealthChecker — P8)."""

    def run(self, *, runs: int = 3) -> BenchmarkResult:
        import tempfile
        from operations.health import HealthChecker

        def one():
            result = HealthChecker(workspace_dir=tempfile.mkdtemp(prefix="nv_p9_ops_")).check_all()
            return result["healthy"], fingerprint(
                {k: v["healthy"] for k, v in result["components"].items()})
        return run_benchmark("operational", one, runs=runs)


__all__ = [
    "BenchmarkResult", "run_benchmark", "ModelBenchmarkRunner", "PipelineBenchmarkRunner",
    "InferenceBenchmarkRunner", "WorkflowBenchmarkRunner", "OperationalBenchmarkRunner",
]
