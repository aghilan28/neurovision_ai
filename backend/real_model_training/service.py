"""``RealModelTrainingService`` — the Real Model Training hub (Track 2).

Orchestrates the governed real-training program over the **shared** platform lineage
tracker + immutable audit log:

    real datasets (Track 1) -> window into labelled samples -> train the 5 architectures
    -> evaluate -> benchmark -> compare -> score serving readiness

It REUSES the Track-1 ``RealDatasetService`` for the real recordings/labels, the
``production_models`` + ``model_foundation`` training/evaluation/benchmark engines (no new
architecture), the shared ``ml.lineage`` tracker, and the shared ``ImmutableAuditLog``. It
trains + evaluates + benchmarks + compares + scores models; it does not serve, persist,
secure, deploy, or modify Track 1.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional, Sequence

from ml.lineage import LineageTracker

from backend.dataset_acquisition import DatasetSource as T1DatasetSource, RealDatasetService

from . import reports as _reports
from .audit import ImmutableAuditLog, make_training_audit_log
from .benchmarking import benchmark as _benchmark
from .comparison import compare as _compare
from .data import RecordingInput, build_real_training_dataset
from .evaluation import evaluate_model
from .experiments import build_experiment
from .lineage import (
    make_benchmark_lineage, make_comparison_lineage, make_dataset_lineage,
    make_evaluation_lineage, make_feature_asset_lineage, make_model_lineage,
    make_readiness_lineage, make_recording_lineage, make_training_run_lineage,
)
from .models.domain import (
    Architecture, CandidateModelRecord, EntityKind, ModelStatus, ServingReadinessClass,
    TrainingRegistryRecord,
)
from .readiness import ServingReadinessEngine
from .registry import RealModelRegistry
from .training import train_architecture
from .validation import TrainingContentValidator
from .version import DEFAULT_SEED, DETERMINISTIC_EPOCH

ALL_ARCHITECTURES = tuple(Architecture)


class RealModelTrainingError(RuntimeError):
    """Raised on hub misuse."""


@dataclass
class PreparedDataset:
    bundle: object
    dataset_record: object
    t1_outcome: object
    provenance: dict


@dataclass
class TrainingProgramOutcome:
    source: str
    dataset_record: object
    candidates: tuple
    experiments: tuple
    evaluations: tuple
    benchmarks: tuple
    readinesses: tuple
    comparison: object
    recommended_model_id: Optional[str]
    dataset_lineage_id: Optional[str]
    audit_head: Optional[str]

    @property
    def dataset_id(self) -> str:
        return self.dataset_record.dataset_id

    def ready_models(self) -> list:
        return [c for c in self.candidates
                if c.readiness_class == ServingReadinessClass.READY_FOR_SERVING]

    def best_ready_model(self):
        ready = {c.model_id: c for c in self.ready_models()}
        if self.comparison and self.comparison.recommended_model in ready:
            return ready[self.comparison.recommended_model]
        return next(iter(ready.values()), None)

    def candidate(self, model_id: str):
        return next((c for c in self.candidates if c.model_id == model_id), None)

    def to_dict(self) -> dict:
        return {"source": self.source, "dataset": self.dataset_record.to_dict(),
                "candidates": [c.to_dict() for c in self.candidates],
                "comparison": self.comparison.to_dict() if self.comparison else None,
                "recommended_model_id": self.recommended_model_id,
                "n_ready_for_serving": len(self.ready_models()),
                "dataset_lineage_id": self.dataset_lineage_id, "audit_head": self.audit_head}


class RealModelTrainingService:
    def __init__(self, *, data_root: Optional[str] = None,
                 lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[RealModelRegistry] = None) -> None:
        self.lineage = lineage_tracker or LineageTracker()
        self.dataset_service = RealDatasetService(data_root=data_root, lineage_tracker=self.lineage)
        self.registry = registry or RealModelRegistry()
        self.readiness_engine = ServingReadinessEngine()
        self.validator = TrainingContentValidator()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}
        self._outcomes: dict[str, TrainingProgramOutcome] = {}

    def audit_log_for(self, dataset_id: str) -> ImmutableAuditLog:
        return self._audit_logs[dataset_id]

    # --- T2-B: prepare the real windowed dataset -----------------------------
    def prepare(self, source: T1DatasetSource = T1DatasetSource.CHB_MIT, *,
                allow_download: bool = False, created_at: str = DETERMINISTIC_EPOCH,
                **window_kwargs) -> PreparedDataset:
        t1 = self.dataset_service.integrate(source, allow_download=allow_download,
                                            created_at=created_at)
        intervals: dict[str, list] = {}
        for label in t1.connector_result.labels:
            intervals.setdefault(label.recording_id, []).extend(
                [(e.start_seconds, e.end_seconds) for e in label.events])
        recs = [RecordingInput(
            abspath=self.dataset_service.storage.abspath(source, r.relative_path),
            patient_id=r.patient_id, recording_id=r.recording_id,
            seizure_intervals=tuple(intervals.get(r.recording_id, ())))
            for r in t1.connector_result.recordings if r.parse_ok]
        bundle, dataset_record, provenance = build_real_training_dataset(
            recs, source_dataset_id=t1.dataset_id, source=source.value, **window_kwargs)
        return PreparedDataset(bundle=bundle, dataset_record=dataset_record, t1_outcome=t1,
                               provenance=provenance)

    # --- T2-C..I: train + evaluate + benchmark + compare + score -------------
    def develop(self, source: T1DatasetSource = T1DatasetSource.CHB_MIT, *,
                architectures: Sequence[Architecture] = ALL_ARCHITECTURES,
                seed: int = DEFAULT_SEED, n_classes: int = 2, allow_download: bool = False,
                created_at: str = DETERMINISTIC_EPOCH,
                **window_kwargs) -> TrainingProgramOutcome:
        prepared = self.prepare(source, allow_download=allow_download, created_at=created_at,
                                **window_kwargs)
        bundle, ds = prepared.bundle, prepared.dataset_record

        log = make_training_audit_log()
        self._audit_logs[ds.dataset_id] = log

        # --- dataset / recording / feature-asset lineage (parents Track-1 dataset) ---
        ds_node = self.lineage.record(make_dataset_lineage(
            ds.dataset_id, prepared.t1_outcome.lineage_id,
            data_fingerprint=ds.data_fingerprint, created_at=created_at))
        rec_nodes = [self.lineage.record(make_recording_lineage(rid, ds_node.lineage_id,
                                                                created_at=created_at)).lineage_id
                     for rid in ds.recording_ids]
        fa_node = self.lineage.record(make_feature_asset_lineage(
            ds.dataset_id, rec_nodes, n_features=ds.n_features, created_at=created_at))

        log.append("dataset_windowed", {"dataset_id": ds.dataset_id, "n_windows": ds.n_windows,
                                        "n_features": ds.n_features,
                                        "class_distribution": ds.class_distribution,
                                        "split_strategy": ds.split_strategy.value},
                   created_at=created_at)
        self._register(ds.dataset_id, EntityKind.DATASET, ds.data_fingerprint, ds_node.lineage_id,
                       log.head, created_at, deps=(prepared.t1_outcome.dataset_id,))
        for rid, rnode in zip(ds.recording_ids, rec_nodes):
            self._register(rid, EntityKind.RECORDING, ds.data_fingerprint, rnode, log.head,
                           created_at, deps=(ds.dataset_id,))
        self._register(f"feature_asset+{ds.dataset_id.split('+')[-1]}", EntityKind.FEATURE_ASSET,
                       ds.data_fingerprint, fa_node.lineage_id, log.head, created_at,
                       deps=(ds.dataset_id,))

        candidates, experiments, evaluations, benchmarks, readinesses, model_nodes = \
            [], [], [], [], [], []

        for arch in architectures:
            to = train_architecture(bundle, arch, seed=seed, n_classes=n_classes,
                                    created_at=created_at)
            bench = _benchmark(to.model, bundle, model_id=to.model_id, architecture=arch,
                               n_classes=n_classes, training_time_ms=to.training_time_ms,
                               created_at=created_at)
            ev, base_eval_id, model_eval_id = evaluate_model(
                to.model, bundle, model_id=to.model_id, training_run_id=to.training_run_id,
                n_classes=n_classes, benchmark_metrics=bench.deterministic_metrics,
                created_at=created_at)
            exp = build_experiment(
                architecture=arch, dataset_id=ds.dataset_id, training_run_id=to.training_run_id,
                model_id=to.model_id,
                configuration={"seed": seed, "n_classes": n_classes,
                               "split_strategy": ds.split_strategy.value,
                               "window_seconds": ds.windowing.window_seconds},
                hyperparameters=to.hyperparameters, training_metrics=to.train_metrics,
                evaluation_metrics=ev.metrics, benchmark_metrics=bench.deterministic_metrics,
                reproducible=to.reproducible, created_at=created_at)

            # lineage: training_run -> model -> evaluation -> benchmark
            tr_node = self.lineage.record(make_training_run_lineage(
                to.training_run_id, fa_node.lineage_id, architecture=arch.value,
                params_fingerprint=to.params_fingerprint, created_at=created_at))
            m_node = self.lineage.record(make_model_lineage(
                to.model_id, tr_node.lineage_id, architecture=arch.value, created_at=created_at))
            ev_node = self.lineage.record(make_evaluation_lineage(
                ev.evaluation_id, m_node.lineage_id, created_at=created_at))
            b_node = self.lineage.record(make_benchmark_lineage(
                bench.benchmark_id, ev_node.lineage_id, created_at=created_at))
            model_nodes.append(m_node.lineage_id)
            # bind the lineage nodes back onto the records (reachable chain)
            ev = replace(ev, lineage_id=ev_node.lineage_id)
            bench = replace(bench, lineage_id=b_node.lineage_id)

            validation = self.validator.validate(dataset_record=ds, train_output=to,
                                                 evaluation_record=ev, benchmark_record=bench)
            log.append("model_trained", {"model_id": to.model_id, "architecture": arch.value,
                                        "training_run_id": to.training_run_id,
                                        "reproducible": to.reproducible}, created_at=created_at)
            log.append("model_evaluated", {"model_id": to.model_id,
                                          "evaluation_id": ev.evaluation_id,
                                          "metrics": {k: round(float(v), 6)
                                                      for k, v in ev.metrics.items()}},
                       created_at=created_at)
            log.append("model_benchmarked", {"model_id": to.model_id,
                                             "benchmark_id": bench.benchmark_id},
                       created_at=created_at)

            traceable = self.lineage.verify_chain(b_node.lineage_id)
            readiness = self.readiness_engine.assess(
                model_id=to.model_id, training_present=True,
                evaluation_present=bool(ev.metrics), benchmark_present=bool(bench.deterministic_metrics),
                validation_ok=validation.ok, registered=True, audited=True, traceable=traceable,
                created_at=created_at)
            r_node = self.lineage.record(make_readiness_lineage(
                readiness.readiness_id, b_node.lineage_id,
                classification=readiness.classification.value, created_at=created_at))
            readiness = replace(readiness, lineage_id=r_node.lineage_id)
            log.append("readiness_scored", {"model_id": to.model_id,
                                           "readiness_id": readiness.readiness_id,
                                           "classification": readiness.classification.value,
                                           "score": readiness.score}, created_at=created_at)

            headline = {k: float(ev.metrics.get(k, 0.0)) for k in
                        ("accuracy", "f1_macro", "roc_auc_macro", "sensitivity", "specificity")}
            candidate = CandidateModelRecord(
                model_id=to.model_id, architecture=arch, dataset_id=ds.dataset_id,
                training_run_id=to.training_run_id, experiment_id=exp.experiment_id,
                evaluation_id=ev.evaluation_id, benchmark_id=bench.benchmark_id,
                readiness_id=readiness.readiness_id, readiness_class=readiness.classification,
                params_fingerprint=to.params_fingerprint, reproducible=to.reproducible,
                patient_ids=ds.patient_ids, validation=validation,
                status=ModelStatus.CANDIDATE if validation.ok else ModelStatus.QUARANTINED,
                headline_metrics=headline, created_at=created_at, lineage_id=m_node.lineage_id,
                audit_head=log.head)

            # register entities (no orphans)
            self._register(to.training_run_id, EntityKind.TRAINING_RUN, to.params_fingerprint,
                           tr_node.lineage_id, log.head, created_at, deps=(ds.dataset_id,))
            self._register(to.model_id, EntityKind.MODEL, to.params_fingerprint, m_node.lineage_id,
                           log.head, created_at, deps=(to.training_run_id,))
            self._register(ev.evaluation_id, EntityKind.EVALUATION, ev.signature(),
                           ev_node.lineage_id, log.head, created_at, deps=(to.model_id,))
            self._register(bench.benchmark_id, EntityKind.BENCHMARK, bench.metrics_signature(),
                           b_node.lineage_id, log.head, created_at, deps=(ev.evaluation_id,))
            self._register(readiness.readiness_id, EntityKind.READINESS, readiness.readiness_id,
                           r_node.lineage_id, log.head, created_at, deps=(bench.benchmark_id,))

            candidates.append(candidate)
            experiments.append(exp)
            evaluations.append(ev)
            benchmarks.append(bench)
            readinesses.append(readiness)

        comparison = _compare(benchmarks, dataset_id=ds.dataset_id, created_at=created_at) \
            if len(benchmarks) >= 2 else None
        if comparison is not None:
            c_node = self.lineage.record(make_comparison_lineage(
                comparison.comparison_id, model_nodes, recommended=comparison.recommended_model,
                created_at=created_at))
            comparison = replace(comparison, lineage_id=c_node.lineage_id)
            log.append("models_compared", {"comparison_id": comparison.comparison_id,
                                          "recommended": comparison.recommended_model},
                       created_at=created_at)
            self._register(comparison.comparison_id, EntityKind.COMPARISON, comparison.comparison_id,
                           c_node.lineage_id, log.head, created_at, deps=(ds.dataset_id,))

        outcome = TrainingProgramOutcome(
            source=source.value, dataset_record=ds, candidates=tuple(candidates),
            experiments=tuple(experiments), evaluations=tuple(evaluations),
            benchmarks=tuple(benchmarks), readinesses=tuple(readinesses), comparison=comparison,
            recommended_model_id=(comparison.recommended_model if comparison else
                                  (candidates[0].model_id if candidates else None)),
            dataset_lineage_id=ds_node.lineage_id, audit_head=log.head)
        self._outcomes[ds.dataset_id] = outcome
        return outcome

    # --- T2-J: reporting -----------------------------------------------------
    def reports(self, outcome: TrainingProgramOutcome) -> dict:
        log = self._audit_logs[outcome.dataset_id]
        best = outcome.best_ready_model() or (outcome.candidates[0] if outcome.candidates else None)
        return {
            "training_report": _reports.build_training_report(outcome.dataset_record,
                                                              list(outcome.experiments)),
            "evaluation_report": _reports.build_evaluation_report(list(outcome.evaluations)),
            "benchmark_report": _reports.build_benchmark_report(list(outcome.benchmarks)),
            "comparison_report": _reports.build_comparison_report(outcome.comparison),
            "readiness_report": _reports.build_readiness_report(list(outcome.readinesses)),
            "registry_report": _reports.build_registry_report(self.registry),
            "audit_report": _reports.build_audit_report(log, subject=outcome.dataset_id),
            "lineage_report": _reports.build_lineage_report(
                self.lineage, best.lineage_id if best else outcome.dataset_lineage_id),
            "model_summary_report": (_reports.build_model_summary_report(best) if best else
                                     {"report_type": "model_summary", "model": None}),
        }

    # --- internals -----------------------------------------------------------
    def _register(self, entity_id, kind, version, lineage_id, audit_head, created_at,
                  *, deps=()) -> None:
        self.registry.register(TrainingRegistryRecord(
            entity_kind=kind, entity_id=entity_id, status="active", version=str(version),
            owner="model-training-ops", creation_date=created_at, audit_state=audit_head,
            lineage_id=lineage_id, dependencies=tuple(deps)))


__all__ = ["RealModelTrainingService", "TrainingProgramOutcome", "PreparedDataset",
           "RealModelTrainingError", "ALL_ARCHITECTURES"]
