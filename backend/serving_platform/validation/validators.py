"""Serving content validation (DRP3-G, request/response build-time).

Validates request structure, model availability, feature availability, execution
integrity, response integrity, contract integrity, and version integrity, producing
structured ``(name, passed, detail)`` results — pure functions, no exceptions.
"""

from __future__ import annotations

from ..contracts import PredictionRequestContract
from ..models.domain import LIFECYCLE_ORDER


class ServingContentValidator:
    """Build-time validation of the serving request/response records."""

    def request_structure(self, request_contract: PredictionRequestContract) -> tuple[str, bool, dict]:
        ok, problems = request_contract.validate()
        return ("request_structure", bool(ok), {"problems": problems})

    def model_availability(self, model_loaded: bool, model_id: str) -> tuple[str, bool, dict]:
        return ("model_availability", bool(model_loaded), {"model_id": model_id})

    def feature_availability(self, feature_present: bool, feature_asset_id: str) -> tuple[str, bool, dict]:
        return ("feature_availability", bool(feature_present), {"feature_asset_id": feature_asset_id})

    def execution_integrity(self, lifecycle_record, completed: bool) -> tuple[str, bool, dict]:
        states = list(lifecycle_record.states)
        ordered = states == [s.value for s in LIFECYCLE_ORDER[:len(states)]]
        return ("execution_integrity", bool(ordered and completed),
                {"final_state": lifecycle_record.final_state, "n_states": len(states)})

    def response_integrity(self, response_record, n_classes: int) -> tuple[str, bool, dict]:
        r = response_record
        ok = (len(r.probability_scores) == n_classes and 0 <= r.predicted_class < n_classes
              and bool(r.confidence_level) and bool(r.calibration_quality))
        return ("response_integrity", bool(ok),
                {"predicted_class": r.predicted_class, "n_scores": len(r.probability_scores)})

    def contract_integrity(self, response_contract: dict) -> tuple[str, bool, dict]:
        ok = (response_contract.get("contract") == "PredictionResponse"
              and "prediction" in response_contract and "confidence" in response_contract
              and "calibration" in response_contract and "explanation" in response_contract)
        return ("contract_integrity", bool(ok),
                {"contract_version": response_contract.get("contract_version")})

    def version_integrity(self, version_str: str) -> tuple[str, bool, dict]:
        return ("version_integrity", bool(version_str) and len(version_str) == 16,
                {"version": version_str})

    def content_checks(self, *, request_contract, model_loaded, model_id, feature_present,
                       feature_asset_id, lifecycle_record, completed, response_record, n_classes,
                       response_contract, version_str) -> list[tuple]:
        return [
            self.request_structure(request_contract),
            self.model_availability(model_loaded, model_id),
            self.feature_availability(feature_present, feature_asset_id),
            self.execution_integrity(lifecycle_record, completed),
            self.response_integrity(response_record, n_classes),
            self.contract_integrity(response_contract),
            self.version_integrity(version_str),
        ]


__all__ = ["ServingContentValidator"]
