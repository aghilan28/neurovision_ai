"""Evidence generation (DRP6-G).

Aggregates a model's benchmark / performance / reliability / calibration artifacts into a
single deterministic :class:`EvidenceRecord` (one evidence fingerprint over all the
artifact signatures), which the evidence registry tracks.
"""

from __future__ import annotations

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..identity import mint_identity
from ..models.domain import EvidenceKind, EvidenceRecord
from ..version import DETERMINISTIC_EPOCH


def build_evidence(*, model_id: str, benchmark, performance, reliability, calibration,
                   created_at: str = DETERMINISTIC_EPOCH) -> EvidenceRecord:
    # the evidence fingerprint is over DETERMINISTIC artifact signatures only — the performance
    # record's informational wall-clock timings never enter it (NR-9/NR-10).
    fingerprint = hash_obj({
        "benchmark": benchmark.signature(), "reliability": reliability.signature(),
        "calibration": calibration.signature(), "performance_id": performance.performance_id})
    evidence_id = mint_identity("validation_evidence", {
        "model_id": model_id, "evidence_key": fingerprint}).id
    return EvidenceRecord(
        evidence_id=evidence_id, model_id=model_id, benchmark_id=benchmark.benchmark_id,
        performance_id=performance.performance_id, reliability_id=reliability.reliability_id,
        calibration_id=calibration.calibration_id,
        evidence_kinds=(EvidenceKind.BENCHMARK.value, EvidenceKind.PERFORMANCE.value,
                        EvidenceKind.RELIABILITY.value, EvidenceKind.CALIBRATION.value),
        fingerprint=fingerprint, created_at=created_at)


__all__ = ["build_evidence"]
