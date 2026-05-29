"""Evaluation lineage record + builder."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from evaluation._canonical import canonical_fingerprint
from evaluation._provenance import VersionBundle
from evaluation.metrics.schemas import MetricResult

#: Version of the evaluation-lineage logic.
LINEAGE_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class EvaluationLineage:
    """The complete provenance chain of an evaluation run."""

    lineage_version: str
    versions: VersionBundle
    split_population_fingerprint: str
    split_fingerprint: str
    metric_fingerprints: dict[str, str]  # metric name -> inputs fingerprint
    result_artifact_fingerprints: tuple[str, ...] = ()
    recorded_at: str | None = None  # provenance only
    attributes: dict[str, Any] = field(default_factory=dict)

    def is_complete(self) -> bool:
        """True iff the dataset/split/preprocessing/metric provenance is all present."""
        return not self.versions.missing_required()

    @property
    def content_fingerprint(self) -> str:
        return canonical_fingerprint(
            {
                "lineage_version": self.lineage_version,
                "versions": self.versions.to_dict(),
                "split_population_fingerprint": self.split_population_fingerprint,
                "split_fingerprint": self.split_fingerprint,
                "metric_fingerprints": self.metric_fingerprints,
                "result_artifact_fingerprints": sorted(self.result_artifact_fingerprints),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "lineage_version": self.lineage_version,
            "versions": self.versions.to_dict(),
            "split_population_fingerprint": self.split_population_fingerprint,
            "split_fingerprint": self.split_fingerprint,
            "metric_fingerprints": self.metric_fingerprints,
            "result_artifact_fingerprints": list(self.result_artifact_fingerprints),
            "content_fingerprint": self.content_fingerprint,
            "recorded_at": self.recorded_at,
            "attributes": self.attributes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationLineage:
        return cls(
            lineage_version=data["lineage_version"],
            versions=VersionBundle.from_dict(data["versions"]),
            split_population_fingerprint=data["split_population_fingerprint"],
            split_fingerprint=data["split_fingerprint"],
            metric_fingerprints=dict(data.get("metric_fingerprints", {})),
            result_artifact_fingerprints=tuple(data.get("result_artifact_fingerprints", ())),
            recorded_at=data.get("recorded_at"),
            attributes=dict(data.get("attributes", {})),
        )


def build_evaluation_lineage(
    versions: VersionBundle,
    *,
    split_population_fingerprint: str,
    split_fingerprint: str,
    metric_results: Mapping[str, MetricResult],
    result_artifact_fingerprints: tuple[str, ...] = (),
    recorded_at: str | None = None,
) -> EvaluationLineage:
    """Assemble the evaluation lineage record from a run's components."""
    metric_fingerprints = {name: r.inputs_fingerprint for name, r in metric_results.items()}
    return EvaluationLineage(
        lineage_version=LINEAGE_VERSION,
        versions=versions,
        split_population_fingerprint=split_population_fingerprint,
        split_fingerprint=split_fingerprint,
        metric_fingerprints=metric_fingerprints,
        result_artifact_fingerprints=result_artifact_fingerprints,
        recorded_at=recorded_at,
    )
