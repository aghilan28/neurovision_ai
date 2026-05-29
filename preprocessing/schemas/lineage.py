"""Preprocessing lineage schema.

Records the full provenance of a preprocessing run so the result is reproducible
and auditable (AP-5/AP-6, NR-10/NR-11): the input recording fingerprint, the
pipeline + config versions, the ordered transformations (each a versioned, param-
fingerprinted :class:`TransformationRecord`), the output fingerprints, and links to
the validation/quality verdicts. This is the bridge that lets a future version
attach downstream artifacts to the data layer's lineage DAG without any rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class TransformationRecord:
    """One recorded transformation in a preprocessing run."""

    stage: str
    operation: str
    operation_version: str
    params_fingerprint: str | None = None
    input_fingerprint: str | None = None
    output_fingerprint: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "operation": self.operation,
            "operation_version": self.operation_version,
            "params_fingerprint": self.params_fingerprint,
            "input_fingerprint": self.input_fingerprint,
            "output_fingerprint": self.output_fingerprint,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TransformationRecord:
        return cls(
            stage=data["stage"],
            operation=data["operation"],
            operation_version=data["operation_version"],
            params_fingerprint=data.get("params_fingerprint"),
            input_fingerprint=data.get("input_fingerprint"),
            output_fingerprint=data.get("output_fingerprint"),
            parameters=dict(data.get("parameters", {})),
        )


@dataclass(frozen=True, slots=True)
class PreprocessingLineage:
    """Complete provenance of a single preprocessing run."""

    pipeline_version: str
    config_fingerprint: str
    input_fingerprint: str | None
    output_fingerprint: str | None
    transformations: tuple[TransformationRecord, ...] = ()
    input_record_id: str | None = None
    input_patient_id: str | None = None
    source_fingerprint: str | None = None  # links to data-layer artifact (e.g. file content hash)
    recorded_at: str | None = None  # provenance only
    attributes: dict[str, Any] = field(default_factory=dict)

    def stage_sequence(self) -> tuple[str, ...]:
        return tuple(t.stage for t in self.transformations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_version": self.pipeline_version,
            "config_fingerprint": self.config_fingerprint,
            "input_fingerprint": self.input_fingerprint,
            "output_fingerprint": self.output_fingerprint,
            "transformations": [t.to_dict() for t in self.transformations],
            "input_record_id": self.input_record_id,
            "input_patient_id": self.input_patient_id,
            "source_fingerprint": self.source_fingerprint,
            "recorded_at": self.recorded_at,
            "attributes": self.attributes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PreprocessingLineage:
        return cls(
            pipeline_version=data["pipeline_version"],
            config_fingerprint=data["config_fingerprint"],
            input_fingerprint=data.get("input_fingerprint"),
            output_fingerprint=data.get("output_fingerprint"),
            transformations=tuple(
                TransformationRecord.from_dict(t) for t in data.get("transformations", [])
            ),
            input_record_id=data.get("input_record_id"),
            input_patient_id=data.get("input_patient_id"),
            source_fingerprint=data.get("source_fingerprint"),
            recorded_at=data.get("recorded_at"),
            attributes=dict(data.get("attributes", {})),
        )
