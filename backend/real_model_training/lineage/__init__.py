"""``backend/real_model_training/lineage`` — real-training lineage (T2-I).

No parallel lineage system: every node is recorded in the same ``ml.lineage.LineageTracker``
as the rest of the platform. The required chain is

    Dataset -> Recording -> Feature Asset -> Training Run -> Model -> Evaluation ->
    Benchmark -> Readiness Assessment

and the dataset node parents the **Track-1** dataset node, so one ``verify_chain`` from a
readiness node reaches the original dataset source (and the patient). Deterministic
(content-addressed ids; ``created_at`` excluded from the id).
"""

from __future__ import annotations

from ml.lineage import LineageRecord, LineageTracker, make_lineage_record

from ..version import (
    REAL_MODEL_TRAINING_VERSION, TRAINING_DOMAIN_VERSION, TRAINING_LINEAGE_VERSION,
    DETERMINISTIC_EPOCH,
)


def _versions(**extra) -> dict:
    bundle = {"real_model_training_version": REAL_MODEL_TRAINING_VERSION,
              "rmt_domain_version": TRAINING_DOMAIN_VERSION,
              "rmt_lineage_version": TRAINING_LINEAGE_VERSION}
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_dataset_lineage(dataset_id, source_dataset_node, *, data_fingerprint,
                         created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    parents = (source_dataset_node,) if source_dataset_node else ()
    return make_lineage_record(kind="training_dataset", versions=_versions(),
                               inputs={"data_fingerprint": data_fingerprint},
                               outputs={"dataset_id": dataset_id}, parents=parents,
                               created_at=created_at)


def make_recording_lineage(recording_id, dataset_node, *,
                           created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="training_recording", versions=_versions(),
                               inputs={"recording_id": recording_id},
                               outputs={"recording_id": recording_id}, parents=(dataset_node,),
                               created_at=created_at)


def make_feature_asset_lineage(dataset_id, recording_nodes, *, n_features,
                               created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="training_feature_asset", versions=_versions(),
                               inputs={"dataset_id": dataset_id, "n_features": n_features},
                               outputs={"feature_asset_for": dataset_id},
                               parents=tuple(recording_nodes), created_at=created_at)


def make_training_run_lineage(training_run_id, feature_asset_node, *, architecture,
                              params_fingerprint, created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="training_run", versions=_versions(),
                               inputs={"architecture": architecture,
                                       "params_fingerprint": params_fingerprint},
                               outputs={"training_run_id": training_run_id},
                               parents=(feature_asset_node,), created_at=created_at)


def make_model_lineage(model_id, training_run_node, *, architecture,
                       created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="trained_model", versions=_versions(),
                               inputs={"architecture": architecture},
                               outputs={"model_id": model_id}, parents=(training_run_node,),
                               created_at=created_at)


def make_evaluation_lineage(evaluation_id, model_node, *,
                            created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="model_evaluation", versions=_versions(),
                               inputs={"evaluation_id": evaluation_id},
                               outputs={"evaluation_id": evaluation_id}, parents=(model_node,),
                               created_at=created_at)


def make_benchmark_lineage(benchmark_id, evaluation_node, *,
                           created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="model_benchmark", versions=_versions(),
                               inputs={"benchmark_id": benchmark_id},
                               outputs={"benchmark_id": benchmark_id}, parents=(evaluation_node,),
                               created_at=created_at)


def make_readiness_lineage(readiness_id, benchmark_node, *, classification,
                           created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="readiness_assessment", versions=_versions(),
                               inputs={"classification": classification},
                               outputs={"readiness_id": readiness_id}, parents=(benchmark_node,),
                               created_at=created_at)


def make_comparison_lineage(comparison_id, model_nodes, *, recommended,
                            created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="model_comparison", versions=_versions(),
                               inputs={"recommended": recommended},
                               outputs={"comparison_id": comparison_id},
                               parents=tuple(model_nodes), created_at=created_at)


__all__ = [
    "LineageTracker", "make_dataset_lineage", "make_recording_lineage",
    "make_feature_asset_lineage", "make_training_run_lineage", "make_model_lineage",
    "make_evaluation_lineage", "make_benchmark_lineage", "make_readiness_lineage",
    "make_comparison_lineage",
]
