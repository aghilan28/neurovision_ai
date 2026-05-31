"""The evidence registry (DRP6-G).

Tracks benchmarks, performance, reliability + calibration studies, comparisons, evidence
artifacts, readiness assessments, and the per-model validation registry entries. **No orphan
evidence**: every validation entry references a lineage node + an audit head + registered
benchmark/evidence/readiness, and re-registering the same ``(validation_id, version)`` with
different content is rejected.
"""

from __future__ import annotations

from ..models.domain import (
    BenchmarkRecord, CalibrationRecord, ComparisonRecord, EvidenceRecord, PerformanceRecord,
    ReadinessRecord, ReliabilityRecord, ValidationRegistryRecord,
)
from ..version import CLINICAL_REGISTRY_VERSION

GENESIS = "0" * 16


class RegistryError(RuntimeError):
    """Raised on orphan evidence or a silent-overwrite attempt."""


class EvidenceRegistry:
    """In-memory registry of clinical-validation evidence, keyed by id."""

    version = CLINICAL_REGISTRY_VERSION

    def __init__(self) -> None:
        self._benchmarks: dict[str, BenchmarkRecord] = {}
        self._performance: dict[str, PerformanceRecord] = {}
        self._reliability: dict[str, ReliabilityRecord] = {}
        self._calibration: dict[str, CalibrationRecord] = {}
        self._comparisons: dict[str, ComparisonRecord] = {}
        self._evidence: dict[str, EvidenceRecord] = {}
        self._readiness: dict[str, ReadinessRecord] = {}
        self._validations: dict[str, ValidationRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}

    # --- registration ---------------------------------------------------------
    def register_benchmark(self, r: BenchmarkRecord) -> BenchmarkRecord:
        self._benchmarks[r.benchmark_id] = r
        return r

    def register_performance(self, r: PerformanceRecord) -> PerformanceRecord:
        self._performance[r.performance_id] = r
        return r

    def register_reliability(self, r: ReliabilityRecord) -> ReliabilityRecord:
        self._reliability[r.reliability_id] = r
        return r

    def register_calibration(self, r: CalibrationRecord) -> CalibrationRecord:
        self._calibration[r.calibration_id] = r
        return r

    def register_comparison(self, r: ComparisonRecord) -> ComparisonRecord:
        self._comparisons[r.comparison_id] = r
        return r

    def register_evidence(self, r: EvidenceRecord) -> EvidenceRecord:
        self._evidence[r.evidence_id] = r
        return r

    def register_readiness(self, r: ReadinessRecord) -> ReadinessRecord:
        self._readiness[r.readiness_id] = r
        return r

    def register_validation(self, r: ValidationRegistryRecord) -> ValidationRegistryRecord:
        if not r.lineage_id:
            raise RegistryError(f"{r.validation_id!r} has no lineage node (orphans forbidden)")
        if not r.audit_state or r.audit_state == GENESIS:
            raise RegistryError(f"{r.validation_id!r} has no audit head (orphans forbidden)")
        if (r.benchmark_id not in self._benchmarks or r.evidence_id not in self._evidence
                or r.readiness_id not in self._readiness):
            raise RegistryError(f"{r.validation_id!r} references unregistered evidence (orphans)")
        key = (r.validation_id, r.version)
        sig = r.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise RegistryError(
                f"validation {r.validation_id} v{r.version} already registered with different content")
        self._version_sigs[key] = sig
        self._validations[r.validation_id] = r
        return r

    # --- accessors ------------------------------------------------------------
    def get_validation(self, validation_id: str) -> ValidationRegistryRecord:
        if validation_id not in self._validations:
            raise KeyError(f"validation {validation_id!r} not in registry")
        return self._validations[validation_id]

    def exists(self, validation_id: str) -> bool:
        return validation_id in self._validations

    def list_validations(self) -> list[str]:
        return sorted(self._validations)

    def counts(self) -> dict:
        return {"benchmark": len(self._benchmarks), "performance": len(self._performance),
                "reliability": len(self._reliability), "calibration": len(self._calibration),
                "comparison": len(self._comparisons), "evidence": len(self._evidence),
                "readiness": len(self._readiness), "validation": len(self._validations)}

    def orphans(self) -> list[str]:
        out = []
        for vid, r in self._validations.items():
            if (r.benchmark_id not in self._benchmarks or r.evidence_id not in self._evidence
                    or r.readiness_id not in self._readiness or not r.lineage_id
                    or not r.audit_state or r.audit_state == GENESIS):
                out.append(vid)
        return sorted(out)

    def to_dict(self) -> dict:
        return {
            "evidence_registry_version": self.version, "counts": self.counts(),
            "benchmarks": {b: r.to_dict() for b, r in sorted(self._benchmarks.items())},
            "reliability": {r_id: r.to_dict() for r_id, r in sorted(self._reliability.items())},
            "calibration": {c: r.to_dict() for c, r in sorted(self._calibration.items())},
            "comparisons": {c: r.to_dict() for c, r in sorted(self._comparisons.items())},
            "evidence": {e: r.to_dict() for e, r in sorted(self._evidence.items())},
            "readiness": {r_id: r.to_dict() for r_id, r in sorted(self._readiness.items())},
            "validations": {v: r.to_dict() for v, r in sorted(self._validations.items())},
        }


__all__ = ["EvidenceRegistry", "RegistryError"]
