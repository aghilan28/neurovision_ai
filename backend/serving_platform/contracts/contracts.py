"""Versioned service contracts (DRP3-E).

The public request/response surface of the serving platform — the shapes a caller exchanges
with the service. In-process and transport-agnostic (no HTTP, no networking, no serving
infrastructure beyond these contracts). Every contract carries its version; builders project
the domain records into deterministic, JSON-able contract dicts.

Distinct from ``schemas/`` (which documents the *domain entity* contracts): these are the
*service* request/response/error contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import SERVING_CONTRACT_VERSION


# =============================================================================
# Request contract
# =============================================================================
@dataclass(frozen=True)
class PredictionRequestContract:
    """A prediction request: a model reference + the input recording's feature asset."""

    model_ref: dict
    feature_asset_id: str
    case_id: str
    patient_id: str
    owner: str = "serving-client"
    contract_version: str = SERVING_CONTRACT_VERSION

    def validate(self) -> tuple[bool, list]:
        problems = []
        if not isinstance(self.model_ref, dict) or not (
                self.model_ref.get("model_id") or self.model_ref.get("architecture")):
            problems.append("model_ref must contain a model_id or an architecture")
        if not self.feature_asset_id:
            problems.append("feature_asset_id is required")
        if not self.case_id or not self.patient_id:
            problems.append("case_id and patient_id are required")
        return (len(problems) == 0), problems

    def key(self) -> str:
        return hash_obj({"model_ref": dict(sorted(self.model_ref.items())),
                         "feature_asset_id": self.feature_asset_id})

    def to_dict(self) -> dict:
        return {
            "contract": "PredictionRequest", "contract_version": self.contract_version,
            "model_ref": dict(sorted(self.model_ref.items())),
            "feature_asset_id": self.feature_asset_id, "case_id": self.case_id,
            "patient_id": self.patient_id, "owner": self.owner,
        }


# =============================================================================
# Response + sub-contracts (built from domain records)
# =============================================================================
def build_model_metadata_contract(model_record) -> dict:
    return {
        "contract": "ModelMetadata", "contract_version": SERVING_CONTRACT_VERSION,
        "model_id": model_record.model_id, "architecture": model_record.architecture.value,
        "version": model_record.version.version, "training_run_id": model_record.training_run_id,
        "dataset_id": model_record.dataset_id, "n_classes": model_record.metadata.n_classes,
        "n_params": model_record.metadata.n_params,
    }


def build_execution_metadata_contract(execution_record) -> dict:
    return {
        "contract": "ExecutionMetadata", "contract_version": SERVING_CONTRACT_VERSION,
        "execution_id": execution_record.execution_id, "request_id": execution_record.request_id,
        "status": execution_record.status.value,
        "lifecycle_states": list(execution_record.lifecycle.states),
        "version": execution_record.version.version,
    }


def build_prediction_response_contract(response_record) -> dict:
    r = response_record
    return {
        "contract": "PredictionResponse", "contract_version": SERVING_CONTRACT_VERSION,
        "response_id": r.response_id, "request_id": r.request_id, "model_id": r.model_id,
        "prediction_id": r.prediction_id, "status": r.status.value,
        "prediction": {
            "predicted_class": r.predicted_class,
            "probability_scores": [round(float(v), 9) for v in r.probability_scores],
        },
        "confidence": {"level": r.confidence_level, "score": round(float(r.confidence_score), 9)},
        "calibration": {"quality": r.calibration_quality,
                        "expected_calibration_error": round(float(r.expected_calibration_error), 9)},
        "explanation": {"summary": [dict(sorted(c.items())) for c in r.explanation_summary]},
        "error": r.error,
    }


def build_error_contract(code: str, message: str, *, request_id: Optional[str] = None,
                         findings: Optional[list] = None) -> dict:
    return {
        "contract": "Error", "contract_version": SERVING_CONTRACT_VERSION, "code": code,
        "message": message, "request_id": request_id, "findings": findings or [],
    }


def build_validation_finding_contract(checks) -> dict:
    return {
        "contract": "ValidationFinding", "contract_version": SERVING_CONTRACT_VERSION,
        "findings": [{"name": n, "passed": bool(p), "detail": d} for n, p, d in checks],
    }


def build_readiness_finding_contract(readiness_record) -> dict:
    return {
        "contract": "ReadinessFinding", "contract_version": SERVING_CONTRACT_VERSION,
        "classification": readiness_record.classification.value,
        "score": round(float(readiness_record.score), 9),
        "findings": list(readiness_record.findings),
        "dimensions": {k: round(float(v), 9) for k, v in sorted(readiness_record.dimensions.items())},
    }


# A registry of the named service contracts (for documentation + the contract report).
CONTRACT_REGISTRY: dict[str, str] = {
    "PredictionRequest": SERVING_CONTRACT_VERSION,
    "PredictionResponse": SERVING_CONTRACT_VERSION,
    "Error": SERVING_CONTRACT_VERSION,
    "ValidationFinding": SERVING_CONTRACT_VERSION,
    "ExecutionMetadata": SERVING_CONTRACT_VERSION,
    "ModelMetadata": SERVING_CONTRACT_VERSION,
    "ReadinessFinding": SERVING_CONTRACT_VERSION,
}


__all__ = [
    "PredictionRequestContract", "build_model_metadata_contract",
    "build_execution_metadata_contract", "build_prediction_response_contract",
    "build_error_contract", "build_validation_finding_contract",
    "build_readiness_finding_contract", "CONTRACT_REGISTRY",
]
