"""Clinical-validation *integrity* validation (DRP6, post-build).

Reuses ``ml.validation.ValidationReport`` to produce the mandated checks over a finalized,
registered clinical validation: benchmark / reliability / calibration / evidence / registry /
audit / lineage / version / traceability integrity.
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import ClinicalValidationVersion

# the lineage kinds that prove the evidence traces to the patient
_REQUIRED_CHAIN_KINDS = {
    "patient", "feature", "dataset", "model", "validation_benchmark", "validation_evaluation",
    "validation_evidence", "validation_readiness",
}


class ValidationIntegrityValidator:
    """Runs the mandated clinical-validation integrity checks."""

    def validate(self, *, record: Any, benchmark: Any, reliability: Any, calibration: Any,
                 evidence: Any, registry: Any, audit_log: Any, lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()

        report.add("benchmark_integrity",
                   benchmark.benchmark_id == record.benchmark_id
                   and "sensitivity" in benchmark.deterministic_metrics,
                   f"benchmark={benchmark.benchmark_id}")
        report.add("reliability_integrity",
                   reliability.reliability_id == record.reliability_id
                   and 0.0 <= reliability.reliability_score <= 1.0,
                   f"score={reliability.reliability_score}")
        report.add("calibration_integrity",
                   calibration.calibration_id == record.calibration_id
                   and calibration.expected_calibration_error >= 0.0,
                   f"quality={calibration.quality.value}")
        report.add("evidence_integrity",
                   evidence.evidence_id == record.evidence_id and len(evidence.evidence_kinds) >= 4,
                   f"kinds={len(evidence.evidence_kinds)}")

        try:
            rec = registry.get_validation(record.validation_id)
            ok = (rec.version == record.version.version and rec.lineage_id == record.lineage_id
                  and registry.orphans() == [])
            report.add("registry_integrity", bool(ok),
                       f"registered={rec.version} orphans={len(registry.orphans())}")
        except Exception as exc:  # pragma: no cover - defensive
            report.add("registry_integrity", False, f"error: {exc}")

        try:
            ok = audit_log.verify() and record.audit_head == audit_log.head
            report.add("audit_integrity", bool(ok),
                       f"verified={audit_log.verify()} head_match={record.audit_head == audit_log.head}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        try:
            chain_ok = bool(record.lineage_id) and lineage_tracker.verify_chain(record.lineage_id)
            kinds = ({r.kind for r in lineage_tracker.chain(record.lineage_id)}
                     if record.lineage_id else set())
            reaches = _REQUIRED_CHAIN_KINDS <= kinds
            ids_ok = (validate_identity(record.validation_id, "clinical_validation")[0]
                      and validate_identity(record.benchmark_id, "validation_benchmark")[0]
                      and validate_identity(record.evidence_id, "validation_evidence")[0])
            report.add("lineage_integrity", bool(chain_ok and reaches and ids_ok),
                       f"chain_ok={chain_ok} reaches_patient={reaches}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        try:
            expected = ClinicalValidationVersion.compute(record.state_signature(),
                                                         record.version.previous)
            report.add("version_integrity", record.version.version == expected,
                       f"recorded={record.version.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        report.add("traceability_integrity",
                   bool(record.lineage_id) and lineage_tracker.verify_chain(record.lineage_id),
                   "Dataset -> Model -> Benchmark -> Evaluation -> Evidence -> Readiness")

        return report


__all__ = ["ValidationIntegrityValidator"]
