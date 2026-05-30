"""Model-foundation lineage helpers built on the shared ``ml.lineage`` machinery.

No parallel lineage system: dataset / training-run / evaluation / model nodes are
recorded in the *same* ``ml.lineage.LineageTracker`` as every upstream node. A
dataset node parents the feature-asset nodes; a training-run node parents the
dataset node; a model node parents the training-run node. A single ``verify_chain``
from a model therefore reaches:

    Patient -> Case -> EEG -> Processed -> Feature -> Dataset -> Training Run -> Model

connecting the trained model back to the patient with complete traceability.
"""

from __future__ import annotations

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    MODEL_FOUNDATION_VERSION, MODEL_DOMAIN_VERSION, MODEL_IDENTITY_VERSION,
    MODEL_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def model_version_bundle(**extra: object) -> dict:
    bundle = {
        "model_foundation_version": MODEL_FOUNDATION_VERSION,
        "model_domain_version": MODEL_DOMAIN_VERSION,
        "model_identity_version": MODEL_IDENTITY_VERSION,
        "model_lineage_version": MODEL_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_dataset_lineage(dataset_id: str, feature_lineage_ids: tuple[str, ...], *, source: str,
                         n_samples: int, data_fingerprint: str,
                         created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A dataset lineage node parented on the contributing feature-asset nodes."""
    return make_lineage_record(
        kind="dataset", versions=model_version_bundle(),
        inputs={"feature_lineage_ids": list(feature_lineage_ids), "source": source},
        outputs={"dataset_id": dataset_id, "n_samples": n_samples,
                 "data_fingerprint": data_fingerprint},
        parents=tuple(feature_lineage_ids), created_at=created_at)


def make_training_lineage(training_run_id: str, dataset_lineage_id: str, *, architecture: str,
                          params_fingerprint: str,
                          created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A training-run lineage node parented on the dataset node."""
    return make_lineage_record(
        kind="training_run", versions=model_version_bundle(),
        inputs={"dataset_id": dataset_lineage_id, "architecture": architecture},
        outputs={"training_run_id": training_run_id, "params_fingerprint": params_fingerprint},
        parents=(dataset_lineage_id,), created_at=created_at)


def make_evaluation_lineage(evaluation_id: str, training_lineage_id: str, *,
                            created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """An evaluation lineage node parented on the training-run node."""
    return make_lineage_record(
        kind="evaluation", versions=model_version_bundle(),
        inputs={"training_run_id": training_lineage_id},
        outputs={"evaluation_id": evaluation_id}, parents=(training_lineage_id,),
        created_at=created_at)


def make_model_lineage(model_id: str, training_lineage_id: str, *, architecture: str,
                       params_fingerprint: str,
                       created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A model lineage node parented on the training-run node."""
    return make_lineage_record(
        kind="model", versions=model_version_bundle(),
        inputs={"training_run_id": training_lineage_id, "architecture": architecture},
        outputs={"model_id": model_id, "params_fingerprint": params_fingerprint},
        parents=(training_lineage_id,), created_at=created_at)
