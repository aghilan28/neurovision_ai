"""Schemas for an evaluation run (the central V1-P4 artifact)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from evaluation._canonical import canonical_fingerprint, mint_id
from evaluation._provenance import VersionBundle
from evaluation.benchmarking.schemas import BenchmarkRecord
from evaluation.lineage.tracker import EvaluationLineage
from evaluation.metrics.schemas import MetricResult
from evaluation.validation.schemas import ApprovalReport, SplitValidationReport


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    """Everything one evaluation produces: gate, metrics, benchmark, lineage, audit."""

    versions: VersionBundle
    split_id: str
    split_fingerprint: str
    split_validation: SplitValidationReport
    approval: ApprovalReport
    status: str  # "approved" | "blocked"
    metric_results: dict[str, MetricResult] = field(default_factory=dict)
    benchmark: BenchmarkRecord | None = None
    lineage: EvaluationLineage | None = None
    audit: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None  # provenance only

    def _fingerprint_payload(self) -> dict[str, Any]:
        return {
            "versions": self.versions.to_dict(),
            "split_fingerprint": self.split_fingerprint,
            "status": self.status,
            "approval": self.approval.approved,
            "metrics": {k: v.to_dict() for k, v in sorted(self.metric_results.items())},
            "benchmark": self.benchmark.content_fingerprint if self.benchmark else None,
        }

    @property
    def content_fingerprint(self) -> str:
        return canonical_fingerprint(self._fingerprint_payload())

    @property
    def run_id(self) -> str:
        return mint_id("eval", self.content_fingerprint)

    @property
    def approved(self) -> bool:
        return self.status == "approved"

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "versions": self.versions.to_dict(),
            "split_id": self.split_id,
            "split_fingerprint": self.split_fingerprint,
            "split_validation": self.split_validation.to_dict(),
            "approval": self.approval.to_dict(),
            "metric_results": {k: v.to_dict() for k, v in self.metric_results.items()},
            "benchmark": self.benchmark.to_dict() if self.benchmark else None,
            "lineage": self.lineage.to_dict() if self.lineage else None,
            "audit": self.audit,
            "content_fingerprint": self.content_fingerprint,
            "created_at": self.created_at,
        }
