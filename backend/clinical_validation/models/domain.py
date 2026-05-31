"""Clinical Validation domain entities + closed vocabularies (DRP6-B).

Pure data shapes (JSON-able, content-hashable). No I/O, no orchestration, no benchmarking/
training logic — this module owns only the *shapes* and the *closed vocabularies*. The
benchmark / calibration / reliability / comparison / evidence / readiness engines produce
these records; the service assembles the immutable ``ClinicalValidationRecord`` aggregate.

Mirrors the rest of the platform (NR-6). Determinism (NR-9/NR-10): deterministic metrics
enter every ``signature()`` / content id; **informational** performance measures (latency /
memory / inference time) are reported but excluded from signatures, so verdicts reproduce
bit-for-bit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    CLINICAL_DOMAIN_VERSION, CLINICAL_BENCHMARK_VERSION, CLINICAL_PERFORMANCE_VERSION,
    CLINICAL_RELIABILITY_VERSION, CLINICAL_CALIBRATION_VERSION, CLINICAL_COMPARISON_VERSION,
    CLINICAL_EVIDENCE_VERSION, CLINICAL_READINESS_VERSION, CLINICAL_REGISTRY_VERSION,
    CLINICAL_VALIDATION_RECORD_VERSION, DETERMINISTIC_EPOCH, FINGERPRINT_DECIMALS,
)


def _q(x) -> float:
    return round(float(x), FINGERPRINT_DECIMALS)


def _qmap(d: dict) -> dict:
    return {k: (_q(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
            for k, v in sorted(d.items())}


# =============================================================================
# Closed vocabularies
# =============================================================================
class ValidationStatus(str, Enum):
    VALIDATED = "validated"
    QUARANTINED = "quarantined"


class EvidenceKind(str, Enum):
    BENCHMARK = "benchmark"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    CALIBRATION = "calibration"
    COMPARISON = "comparison"


class CalibrationQuality(str, Enum):
    WELL_CALIBRATED = "well_calibrated"
    MODERATELY_CALIBRATED = "moderately_calibrated"
    POORLY_CALIBRATED = "poorly_calibrated"


class ReadinessClass(str, Enum):
    NOT_READY = "NOT_READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    READY = "READY"


class ReadinessDimension(str, Enum):
    """The closed set of validation-readiness dimensions (DRP6-I)."""

    BENCHMARK = "benchmark_readiness"
    RELIABILITY = "reliability_readiness"
    CALIBRATION = "calibration_readiness"
    EVIDENCE = "evidence_readiness"
    REGISTRY = "registry_readiness"
    AUDIT = "audit_readiness"
    LINEAGE = "lineage_readiness"


class EntityKind(str, Enum):
    VALIDATION = "clinical_validation"
    BENCHMARK = "validation_benchmark"
    PERFORMANCE = "validation_performance"
    RELIABILITY = "validation_reliability"
    CALIBRATION = "validation_calibration"
    EVIDENCE = "validation_evidence"
    COMPARISON = "validation_comparison"
    READINESS = "validation_readiness"


# =============================================================================
# Identity + versioning
# =============================================================================
@dataclass(frozen=True)
class ClinicalValidationIdentity:
    validation_id: str
    model_id: str
    evidence_id: str
    benchmark_id: str
    identity_version: str
    domain_version: str = CLINICAL_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {"validation_id": self.validation_id, "model_id": self.model_id,
                "evidence_id": self.evidence_id, "benchmark_id": self.benchmark_id,
                "identity_version": self.identity_version, "domain_version": self.domain_version}


@dataclass(frozen=True)
class ClinicalValidationVersion:
    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous, "reason": self.reason,
                "created_at": self.created_at}


# =============================================================================
# Benchmark / performance
# =============================================================================
@dataclass(frozen=True)
class BenchmarkRecord:
    """A clinical benchmark of one model on a dataset. Deterministic metrics (accuracy /
    precision / recall / F1 / ROC-AUC / PR-AUC / sensitivity / specificity) enter the id +
    signature; performance measures are informational (never hashed)."""

    benchmark_id: str
    model_id: str
    architecture: str
    dataset_label: str
    deterministic_metrics: dict
    performance: dict
    n_samples: int
    n_classes: int
    source_benchmark_id: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    benchmark_version: str = CLINICAL_BENCHMARK_VERSION

    def signature(self) -> str:
        return hash_obj({"benchmark_id": self.benchmark_id, "model_id": self.model_id,
                         "architecture": self.architecture, "dataset_label": self.dataset_label,
                         "deterministic_metrics": _qmap(self.deterministic_metrics),
                         "n_samples": self.n_samples, "n_classes": self.n_classes})

    def to_dict(self) -> dict:
        return {"benchmark_id": self.benchmark_id, "model_id": self.model_id,
                "architecture": self.architecture, "dataset_label": self.dataset_label,
                "deterministic_metrics": _qmap(self.deterministic_metrics),
                "performance": _qmap(self.performance), "n_samples": self.n_samples,
                "n_classes": self.n_classes, "source_benchmark_id": self.source_benchmark_id,
                "created_at": self.created_at, "lineage_id": self.lineage_id,
                "benchmark_version": self.benchmark_version, "benchmark_signature": self.signature()}


@dataclass(frozen=True)
class PerformanceRecord:
    """Informational performance evidence (latency / memory / inference + training time /
    throughput). Never enters a deterministic signature."""

    performance_id: str
    model_id: str
    measures: dict
    performance_version: str = CLINICAL_PERFORMANCE_VERSION

    def to_dict(self) -> dict:
        return {"performance_id": self.performance_id, "model_id": self.model_id,
                "measures": _qmap(self.measures), "performance_version": self.performance_version}


# =============================================================================
# Reliability / calibration
# =============================================================================
@dataclass(frozen=True)
class ReliabilityRecord:
    reliability_id: str
    model_id: str
    repeatable: bool
    reproducible: bool
    cross_run_stability: float
    cross_dataset_stability: float
    failure_modes: tuple[dict, ...]
    reliability_score: float
    reliability_version: str = CLINICAL_RELIABILITY_VERSION

    def signature(self) -> str:
        return hash_obj({"reliability_id": self.reliability_id, "model_id": self.model_id,
                         "repeatable": self.repeatable, "reproducible": self.reproducible,
                         "cross_run_stability": _q(self.cross_run_stability),
                         "cross_dataset_stability": _q(self.cross_dataset_stability),
                         "failure_modes": [dict(sorted(f.items())) for f in self.failure_modes],
                         "reliability_score": _q(self.reliability_score)})

    def to_dict(self) -> dict:
        return {"reliability_id": self.reliability_id, "model_id": self.model_id,
                "repeatable": self.repeatable, "reproducible": self.reproducible,
                "cross_run_stability": _q(self.cross_run_stability),
                "cross_dataset_stability": _q(self.cross_dataset_stability),
                "failure_modes": [dict(sorted(f.items())) for f in self.failure_modes],
                "reliability_score": _q(self.reliability_score),
                "reliability_version": self.reliability_version,
                "reliability_signature": self.signature()}


@dataclass(frozen=True)
class CalibrationRecord:
    calibration_id: str
    model_id: str
    expected_calibration_error: float
    brier: float
    quality: CalibrationQuality
    confidence_distribution: dict
    reliability_curve: tuple[dict, ...]
    calibration_version: str = CLINICAL_CALIBRATION_VERSION

    def signature(self) -> str:
        return hash_obj({"calibration_id": self.calibration_id, "model_id": self.model_id,
                         "expected_calibration_error": _q(self.expected_calibration_error),
                         "brier": _q(self.brier), "quality": self.quality.value,
                         "confidence_distribution": _qmap(self.confidence_distribution),
                         "reliability_curve": [dict(sorted(b.items()))
                                               for b in self.reliability_curve]})

    def to_dict(self) -> dict:
        return {"calibration_id": self.calibration_id, "model_id": self.model_id,
                "expected_calibration_error": _q(self.expected_calibration_error),
                "brier": _q(self.brier), "quality": self.quality.value,
                "confidence_distribution": _qmap(self.confidence_distribution),
                "reliability_curve": [dict(sorted(b.items())) for b in self.reliability_curve],
                "calibration_version": self.calibration_version,
                "calibration_signature": self.signature()}


# =============================================================================
# Comparison / evidence
# =============================================================================
@dataclass(frozen=True)
class ComparisonRecord:
    comparison_id: str
    n_models: int
    metrics: tuple[str, ...]
    ranking: tuple[str, ...]
    best_per_metric: dict
    recommended_model: Optional[str]
    comparison_version: str = CLINICAL_COMPARISON_VERSION

    def signature(self) -> str:
        return hash_obj({"comparison_id": self.comparison_id, "n_models": self.n_models,
                         "metrics": list(self.metrics), "ranking": list(self.ranking),
                         "recommended_model": self.recommended_model})

    def to_dict(self) -> dict:
        return {"comparison_id": self.comparison_id, "n_models": self.n_models,
                "metrics": list(self.metrics), "ranking": list(self.ranking),
                "best_per_metric": self.best_per_metric, "recommended_model": self.recommended_model,
                "comparison_version": self.comparison_version, "comparison_signature": self.signature()}


@dataclass(frozen=True)
class EvidenceRecord:
    """Aggregated evidence for one model — binds its benchmark / performance / reliability /
    calibration artifacts under one evidence fingerprint."""

    evidence_id: str
    model_id: str
    benchmark_id: str
    performance_id: str
    reliability_id: str
    calibration_id: str
    evidence_kinds: tuple[str, ...]
    fingerprint: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    evidence_version: str = CLINICAL_EVIDENCE_VERSION

    def signature(self) -> str:
        return hash_obj({"evidence_id": self.evidence_id, "model_id": self.model_id,
                         "benchmark_id": self.benchmark_id, "performance_id": self.performance_id,
                         "reliability_id": self.reliability_id, "calibration_id": self.calibration_id,
                         "evidence_kinds": list(self.evidence_kinds), "fingerprint": self.fingerprint})

    def to_dict(self) -> dict:
        return {"evidence_id": self.evidence_id, "model_id": self.model_id,
                "benchmark_id": self.benchmark_id, "performance_id": self.performance_id,
                "reliability_id": self.reliability_id, "calibration_id": self.calibration_id,
                "evidence_kinds": list(self.evidence_kinds), "fingerprint": self.fingerprint,
                "created_at": self.created_at, "lineage_id": self.lineage_id,
                "evidence_version": self.evidence_version, "evidence_signature": self.signature()}


# =============================================================================
# Readiness
# =============================================================================
@dataclass(frozen=True)
class ReadinessRecord:
    readiness_id: str
    target_id: str
    score: float
    classification: ReadinessClass
    dimensions: dict
    findings: tuple[str, ...]
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    readiness_version: str = CLINICAL_READINESS_VERSION

    def signature(self) -> str:
        return hash_obj({"readiness_id": self.readiness_id, "target_id": self.target_id,
                         "score": _q(self.score), "classification": self.classification.value,
                         "dimensions": _qmap(self.dimensions), "findings": list(self.findings)})

    def to_dict(self) -> dict:
        return {"readiness_id": self.readiness_id, "target_id": self.target_id, "score": _q(self.score),
                "classification": self.classification.value, "dimensions": _qmap(self.dimensions),
                "findings": list(self.findings), "created_at": self.created_at,
                "lineage_id": self.lineage_id, "readiness_version": self.readiness_version,
                "readiness_signature": self.signature()}


# =============================================================================
# Audit / lineage / registry projections
# =============================================================================
@dataclass(frozen=True)
class ValidationAuditRecord:
    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload,
                "prev_hash": self.prev_hash, "event_hash": self.event_hash,
                "created_at": self.created_at}


@dataclass(frozen=True)
class ValidationLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass
class ValidationRegistryRecord:
    validation_id: str
    model_id: str
    architecture: str
    dataset_label: str
    benchmark_id: str
    evidence_id: str
    readiness_id: str
    status: ValidationStatus
    readiness_class: ReadinessClass
    version: str
    owner: str
    creation_date: str
    audit_state: str
    lineage_id: str
    dependencies: tuple[str, ...]
    registry_version: str = CLINICAL_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"validation_id": self.validation_id, "model_id": self.model_id,
                         "architecture": self.architecture, "dataset_label": self.dataset_label,
                         "benchmark_id": self.benchmark_id, "evidence_id": self.evidence_id,
                         "readiness_id": self.readiness_id, "status": self.status.value,
                         "version": self.version, "lineage_id": self.lineage_id})

    def to_dict(self) -> dict:
        return {"validation_id": self.validation_id, "model_id": self.model_id,
                "architecture": self.architecture, "dataset_label": self.dataset_label,
                "benchmark_id": self.benchmark_id, "evidence_id": self.evidence_id,
                "readiness_id": self.readiness_id, "status": self.status.value,
                "readiness_class": self.readiness_class.value, "version": self.version,
                "owner": self.owner, "creation_date": self.creation_date,
                "audit_state": self.audit_state, "lineage_id": self.lineage_id,
                "dependencies": list(self.dependencies), "registry_version": self.registry_version,
                "content_signature": self.content_signature()}


# =============================================================================
# The aggregate — the immutable Clinical Validation record (per model)
# =============================================================================
@dataclass(frozen=True)
class ClinicalValidationRecord:
    """The clinical-validation aggregate — an **immutable**, versioned, auditable,
    lineage-tracked record of one model's validation evidence. Binds the benchmark,
    performance, reliability, calibration, and evidence artifacts + the readiness."""

    identity: ClinicalValidationIdentity
    model_id: str
    architecture: str
    dataset_label: str
    benchmark_id: str
    performance_id: str
    reliability_id: str
    calibration_id: str
    evidence_id: str
    readiness_id: str
    readiness_class: ReadinessClass
    validation_ok: bool
    checks: tuple[tuple, ...]
    status: ValidationStatus
    version: ClinicalValidationVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    dependencies: tuple[str, ...] = ()
    domain_version: str = CLINICAL_VALIDATION_RECORD_VERSION

    @property
    def validation_id(self) -> str:
        return self.identity.validation_id

    def validation_signature(self) -> str:
        return hash_obj({"ok": self.validation_ok,
                         "checks": [[n, bool(p)] for n, p, _ in self.checks]})

    @staticmethod
    def state_signature_of(*, identity, model_id, architecture, dataset_label, benchmark_id,
                           performance_id, reliability_id, calibration_id, evidence_id, readiness_id,
                           readiness_class, validation_ok, checks, status, dependencies) -> str:
        return hash_obj({
            "validation_id": identity.validation_id, "model_id": model_id,
            "architecture": architecture, "dataset_label": dataset_label, "benchmark_id": benchmark_id,
            "performance_id": performance_id, "reliability_id": reliability_id,
            "calibration_id": calibration_id, "evidence_id": evidence_id, "readiness_id": readiness_id,
            "readiness_class": readiness_class.value, "validation_ok": validation_ok,
            "checks": [[n, bool(p)] for n, p, _ in checks], "status": status.value,
            "dependencies": list(dependencies)})

    def state_signature(self) -> str:
        return self.state_signature_of(
            identity=self.identity, model_id=self.model_id, architecture=self.architecture,
            dataset_label=self.dataset_label, benchmark_id=self.benchmark_id,
            performance_id=self.performance_id, reliability_id=self.reliability_id,
            calibration_id=self.calibration_id, evidence_id=self.evidence_id,
            readiness_id=self.readiness_id, readiness_class=self.readiness_class,
            validation_ok=self.validation_ok, checks=self.checks, status=self.status,
            dependencies=self.dependencies)

    def to_dict(self) -> dict:
        return {"domain_version": self.domain_version, "identity": self.identity.to_dict(),
                "model_id": self.model_id, "architecture": self.architecture,
                "dataset_label": self.dataset_label, "benchmark_id": self.benchmark_id,
                "performance_id": self.performance_id, "reliability_id": self.reliability_id,
                "calibration_id": self.calibration_id, "evidence_id": self.evidence_id,
                "readiness_id": self.readiness_id, "readiness_class": self.readiness_class.value,
                "validation_ok": self.validation_ok,
                "checks": [{"name": n, "passed": bool(p), "detail": d} for n, p, d in self.checks],
                "status": self.status.value, "version": self.version.to_dict(), "owner": self.owner,
                "created_at": self.created_at, "lineage_id": self.lineage_id,
                "audit_head": self.audit_head, "dependencies": list(self.dependencies),
                "state_signature": self.state_signature()}
