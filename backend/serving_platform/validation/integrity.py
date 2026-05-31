"""Serving *integrity* validation (DRP3-G, post-build).

Reuses ``ml.validation.ValidationReport`` to produce the mandated checks over a finalized,
registered serving execution: request / execution / response / contract / registry / audit
/ lineage / readiness / version / traceability. The result shape matches the rest of the
platform (NR-6).
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import LIFECYCLE_ORDER, ServingVersion

# the lineage kinds that prove a served response traces to the patient
_REQUIRED_CHAIN_KINDS = {
    "patient", "case", "eeg", "processed_eeg", "feature", "dataset", "training_run", "model",
    "prediction", "serving_request", "serving_execution", "serving_response",
}


class ServingIntegrityValidator:
    """Runs the mandated serving integrity checks."""

    def validate(self, *, execution: Any, response: Any, readiness: Any, registry: Any,
                 audit_log: Any, lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()

        # --- request integrity ---
        report.add("request_integrity",
                   bool(execution.request.request_id) and bool(execution.request.lineage_id)
                   and validate_identity(execution.request_id, "serving_request")[0],
                   f"request_id={execution.request_id}")

        # --- execution integrity (lifecycle in canonical order, completed) ---
        states = list(execution.lifecycle.states)
        ordered = states == [s.value for s in LIFECYCLE_ORDER[:len(states)]]
        report.add("execution_integrity",
                   ordered and execution.lifecycle.final_state == LIFECYCLE_ORDER[-1].value,
                   f"final_state={execution.lifecycle.final_state} n_states={len(states)}")

        # --- response integrity ---
        report.add("response_integrity",
                   response.response_id == execution.response_id
                   and bool(response.confidence_level) and bool(response.calibration_quality)
                   and len(response.probability_scores) > 0,
                   f"response_id_match={response.response_id == execution.response_id}")

        # --- contract integrity (ids well-formed) ---
        ids_ok = (validate_identity(execution.execution_id, "serving_execution")[0]
                  and validate_identity(execution.response_id, "serving_response")[0]
                  and validate_identity(execution.prediction_id, "prediction")[0]
                  and validate_identity(execution.model_id, "model")[0])
        report.add("contract_integrity", bool(ids_ok), "all serving + referenced ids well-formed")

        # --- registry integrity ---
        try:
            rec = registry.get_execution(execution.execution_id)
            ok = (rec.version == execution.version.version and rec.lineage_id == execution.lineage_id
                  and rec.prediction_id == execution.prediction_id and registry.orphans() == [])
            report.add("registry_integrity", bool(ok),
                       f"registered={rec.version} orphans={len(registry.orphans())}")
        except Exception as exc:  # pragma: no cover - defensive
            report.add("registry_integrity", False, f"error: {exc}")

        # --- audit integrity ---
        try:
            ok = audit_log.verify() and execution.audit_head == audit_log.head
            report.add("audit_integrity", bool(ok),
                       f"chain_verified={audit_log.verify()} head_match={execution.audit_head == audit_log.head}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # --- lineage integrity (response chain reaches the patient) ---
        try:
            chain_ok = bool(execution.lineage_id) and lineage_tracker.verify_chain(response.lineage_id)
            kinds = ({r.kind for r in lineage_tracker.chain(response.lineage_id)}
                     if response.lineage_id else set())
            reaches = _REQUIRED_CHAIN_KINDS <= kinds
            report.add("lineage_integrity", bool(chain_ok and reaches),
                       f"chain_ok={chain_ok} reaches_patient={reaches}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # --- readiness integrity ---
        report.add("readiness_integrity",
                   readiness.readiness_id == execution.readiness_id
                   and 0.0 <= readiness.score <= 1.0 and bool(readiness.dimensions),
                   f"classification={readiness.classification.value} score={readiness.score}")

        # --- version integrity ---
        try:
            expected = ServingVersion.compute(execution.state_signature(), execution.version.previous)
            report.add("version_integrity", execution.version.version == expected,
                       f"recorded={execution.version.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        # --- traceability integrity (explicit end-to-end check) ---
        report.add("traceability_integrity",
                   bool(response.lineage_id) and lineage_tracker.verify_chain(response.lineage_id),
                   "Dataset -> Feature -> Model -> Inference -> Request -> Execution -> Response")

        return report


__all__ = ["ServingIntegrityValidator"]
