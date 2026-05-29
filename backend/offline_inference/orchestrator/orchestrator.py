"""The master inference orchestrator (15 deterministic, audited stages).

Each stage is a method returning a record dict that contains a content
``signature``; the ``ExecutionEngine`` runs them against a shared ``context``. The
orchestrator reuses the authoritative subsystems (datasets, preprocessing, ml,
ml.uncertainty, evaluation) rather than re-implementing any of them (NR-6), and
persists every output + report as a checksummed registered artifact.

Result: an inference is reproducible (content-addressed ``inference_id``) and
traceable end to end (inference → uncertainty → evaluation → training lineage).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from datasets import generate_dataset, patient_disjoint_split, analyze  # backend -> datasets
from preprocessing import transform                                      # backend -> preprocessing
from ml.models.base import ModelConfig                                   # backend -> ml
from ml.training import Trainer
from ml.artifacts import ArtifactStore
from ml.registry import ModelRegistry, ModelStatus
from ml.lineage import LineageTracker, VersionBundle, make_lineage_record
from ml.provenance import content_id, hash_obj
from ml.uncertainty import (
    CalibrationPipeline, SplitConformalPredictor, CoverageTracker, RiskAssessor,
    CALIBRATION_VERSION, CONFORMAL_VERSION, COVERAGE_VERSION, RISK_VERSION,
)
from ml.benchmarking import EvaluationResult, BenchmarkRegistry, build_benchmark_record
from ml.version import BENCHMARK_VERSION

from evaluation import (                                                 # backend -> evaluation
    PatientDisjointEvaluator, EVALUATION_VERSION, expected_calibration_error, brier_score,
)

from ..version import (
    OFFLINE_INFERENCE_VERSION, ORCHESTRATOR_VERSION, OUTPUT_CONTRACT_VERSION, DETERMINISTIC_EPOCH,
)
from ..pipelines import PipelineConfig
from ..execution import ExecutionEngine, Stage, ExecutionResult, Clock
from ..artifacts import InferenceArtifactStore
from ..registry import InferenceRegistry, InferenceRecord
from ..lineage import make_inference_lineage
from ..validation import InferenceValidator
from ..schemas import (
    PredictionOutput, ProbabilityOutput, CalibrationOutput, ConformalOutput,
    CoverageOutput, RiskOutput, ClinicalOutput, SummaryOutput, ReportOutput, ArtifactOutput,
)
from ..reports import (
    build_inference_report, build_calibration_report, build_coverage_report,
    build_risk_report, build_audit_report, build_summary_report,
)


@dataclass
class OrchestratorResult:
    inference_id: str
    output_dir: str
    execution: ExecutionResult
    version_bundle: dict
    outputs: dict                 # contract name -> dict
    artifact_refs: dict
    inference_record: dict
    validation: dict
    audit: dict
    lineage_id: str
    registries: dict = field(default_factory=dict)


class InferenceOrchestrator:
    """Runs the 15-stage offline inference workflow deterministically."""

    version = ORCHESTRATOR_VERSION

    def __init__(self, config: Optional[PipelineConfig] = None,
                 output_dir: Optional[str] = None, clock: Optional[Clock] = None,
                 dataset=None):
        self.config = config or PipelineConfig()
        self.run_signature = content_id("offline-run", self.config.as_dict())
        self.output_dir = output_dir or f"artifacts/_runs/offline/{self.run_signature}"
        self.clock = clock
        self._provided_dataset = dataset  # optional pre-ingested EEGDataset

    # ------------------------------------------------------------------ stages
    def _stage_ingestion(self, ctx: dict) -> dict:
        dataset = self._provided_dataset or generate_dataset(self.config.synthetic)
        ctx["dataset"] = dataset
        return {"signature": hash_obj({"dataset_version": dataset.dataset_version}),
                "dataset_version": dataset.dataset_version, "n_windows": dataset.n_windows}

    def _stage_validation(self, ctx: dict) -> dict:
        dataset = ctx["dataset"]
        split = patient_disjoint_split(dataset, self.config.split)
        split.assert_patient_disjoint()  # NR-3 — fail loudly on leakage
        ctx["split"] = split
        intel = analyze(dataset, split)
        ctx["intelligence"] = intel
        quality = intel.quality
        if not quality["passed"]:
            raise ValueError(f"dataset failed quality validation: {quality}")
        return {"signature": hash_obj({"split_version": split.split_version,
                                       "quality": quality["quality_score"]}),
                "split_version": split.split_version,
                "quality_score": quality["quality_score"],
                "patient_disjoint": intel.leakage["patient_disjoint"]}

    def _stage_preprocessing(self, ctx: dict) -> dict:
        x_all = transform(ctx["dataset"].windows, self.config.preprocessing)
        ctx["x_all"] = x_all
        from preprocessing import preprocessing_signature, PREPROCESSING_VERSION
        sig = preprocessing_signature(self.config.preprocessing)
        ctx["preprocessing_version"] = PREPROCESSING_VERSION
        ctx["preprocessing_signature"] = sig
        return {"signature": sig, "preprocessing_version": PREPROCESSING_VERSION,
                "shape": list(x_all.shape)}

    def _stage_dataset_intelligence(self, ctx: dict) -> dict:
        intel = ctx["intelligence"]  # computed in validation; record it as an output
        ctx["intelligence_dict"] = intel.to_dict()
        return {"signature": intel.signature(),
                "readiness": intel.readiness["readiness_score"],
                "ready": intel.readiness["ready"]}

    def _stage_evaluation_preparation(self, ctx: dict) -> dict:
        dataset, split, x_all = ctx["dataset"], ctx["split"], ctx["x_all"]

        def sl(idx):
            return x_all[idx], dataset.labels[idx], dataset.patient_ids[idx]

        xtr, ytr, ptr = sl(split.train_idx)
        xca, yca, pca = sl(split.calibration_idx)
        xte, yte, pte = sl(split.test_idx)
        ctx["prepared"] = {
            "x_train": xtr, "y_train": ytr, "p_train": ptr,
            "x_cal": xca, "y_cal": yca, "p_cal": pca,
            "x_test": xte, "y_test": yte, "p_test": pte,
            "class_names": dataset.class_names,
        }
        return {"signature": hash_obj({"n_train": int(xtr.shape[0]), "n_cal": int(xca.shape[0]),
                                       "n_test": int(xte.shape[0]), "split": split.split_version}),
                "n_train": int(xtr.shape[0]), "n_cal": int(xca.shape[0]), "n_test": int(xte.shape[0])}

    def _stage_model_selection(self, ctx: dict) -> dict:
        dataset, split = ctx["dataset"], ctx["split"]
        model_store = ArtifactStore(os.path.join(self.output_dir, "models"))
        trainer = Trainer(model_store, ctx["model_registry"], ctx["lineage"])
        model_config = ModelConfig(
            name=self.config.model_name, n_channels=dataset.n_channels,
            n_samples=dataset.n_samples, n_classes=dataset.n_classes, seed=self.config.model_seed)
        result = trainer.run(dataset=dataset, split=split, model_config=model_config,
                             training_config=self.config.training,
                             preprocessing_config=self.config.preprocessing, owner=self.config.owner)
        ctx["model"] = result.model
        ctx["model_version"] = result.model_version
        ctx["training_lineage_id"] = result.lineage_id
        ctx["version_bundle"] = result.version_bundle
        ctx["model_store"] = model_store
        return {"signature": hash_obj({"model_version": result.model_version}),
                "model_version": result.model_version, "model_name": result.model.name,
                "training_validation_ok": result.validation_report["ok"]}

    def _stage_inference(self, ctx: dict) -> dict:
        model, prep = ctx["model"], ctx["prepared"]
        raw_test_probs = model.predict_proba(prep["x_test"])
        ctx["raw_test_probs"] = raw_test_probs
        ctx["calib_logits"] = model.forward_logits(prep["x_cal"])
        ctx["test_logits"] = model.forward_logits(prep["x_test"])
        return {"signature": hash_obj({"probs": np.round(raw_test_probs, 6).tolist()}),
                "n_inference": int(raw_test_probs.shape[0])}

    def _stage_calibration(self, ctx: dict) -> dict:
        cal_result, scaler = CalibrationPipeline().calibrate(ctx["calib_logits"], ctx["prepared"]["y_cal"])
        ctx["scaler"] = scaler
        ctx["calibration_result"] = cal_result
        ctx["calibrated_cal_probs"] = scaler.transform(ctx["calib_logits"])
        ctx["calibrated_test_probs"] = scaler.transform(ctx["test_logits"])
        return {"signature": hash_obj({"T": round(cal_result.temperature, 6),
                                       "ece_post": round(cal_result.post_ece, 6)}),
                "temperature": cal_result.temperature, "ece_post": cal_result.post_ece}

    def _stage_conformal(self, ctx: dict) -> dict:
        cp = SplitConformalPredictor(alpha=self.config.alpha).fit(
            ctx["calibrated_cal_probs"], ctx["prepared"]["y_cal"])
        conformal = cp.predict(ctx["calibrated_test_probs"], ctx["prepared"]["class_names"])
        ctx["conformal_result"] = conformal
        return {"signature": hash_obj({"qhat": round(conformal.qhat, 6),
                                       "target": conformal.target_coverage}),
                "qhat": conformal.qhat, "mean_set_size": float(conformal.set_sizes().mean())}

    def _stage_coverage(self, ctx: dict) -> dict:
        conformal = ctx["conformal_result"]
        coverage = CoverageTracker().assess(
            prediction_sets=conformal.prediction_sets, labels=ctx["prepared"]["y_test"],
            target_coverage=conformal.target_coverage, class_names=ctx["prepared"]["class_names"],
            dataset_version=ctx["dataset"].dataset_version, split_version=ctx["split"].split_version)
        ctx["coverage_result"] = coverage
        return {"signature": hash_obj({"observed": round(coverage.observed_coverage, 6)}),
                "observed_coverage": coverage.observed_coverage, "reliable": coverage.reliable}

    def _stage_risk(self, ctx: dict) -> dict:
        risk = RiskAssessor().assess(
            calibrated_probs=ctx["calibrated_test_probs"], class_names=ctx["prepared"]["class_names"],
            prediction_sets=ctx["conformal_result"].prediction_sets, labels=ctx["prepared"]["y_test"])
        ctx["risk_result"] = risk
        return {"signature": hash_obj({"abstain_rate": round(risk.abstain_rate, 6)}),
                "abstain_rate": risk.abstain_rate}

    def _stage_output_generation(self, ctx: dict) -> dict:
        dataset, split, prep = ctx["dataset"], ctx["split"], ctx["prepared"]
        cal, conf, cov, risk = (ctx["calibration_result"], ctx["conformal_result"],
                                ctx["coverage_result"], ctx["risk_result"])
        class_names = dataset.class_names

        # Evaluation through the evaluation framework (patient-disjoint, NR-3)
        evaluator = PatientDisjointEvaluator()
        ev = evaluator.evaluate(
            probabilities=ctx["raw_test_probs"], labels=prep["y_test"], patient_ids=prep["p_test"],
            class_names=class_names, dataset_version=dataset.dataset_version,
            split_version=split.split_version, train_patient_ids=split.train_patients)
        ctx["evaluation_result"] = ev

        calibrated = ctx["calibrated_test_probs"]
        class_idx = calibrated.argmax(axis=1)

        outputs = {
            "prediction": PredictionOutput(class_idx, class_names, prep["p_test"]),
            "probability": ProbabilityOutput(calibrated, class_names, calibrated=True),
            "calibration": CalibrationOutput(
                method=cal.method, temperature=cal.temperature, ece_pre=cal.pre_ece,
                ece_post=cal.post_ece, mce_post=cal.post_mce, brier_post=cal.post_brier,
                reliability_bins=cal.post_bins, calibration_version=CALIBRATION_VERSION),
            "conformal": ConformalOutput(
                conf.prediction_sets, class_names, alpha=self.config.alpha,
                target_coverage=conf.target_coverage, qhat=conf.qhat, conformal_version=CONFORMAL_VERSION),
            "coverage": CoverageOutput(
                target_coverage=cov.target_coverage, observed_coverage=cov.observed_coverage,
                coverage_drift=cov.coverage_drift, n_violations=cov.n_violations,
                violation_rate=cov.violation_rate, average_set_size=cov.average_set_size,
                per_class_coverage=cov.per_class_coverage, reliable=cov.reliable,
                coverage_version=COVERAGE_VERSION),
            "risk": RiskOutput(
                risk_scores=risk.risk_scores, confidence=risk.confidence, bands=risk.bands,
                abstain=risk.abstain, band_thresholds=risk.band_thresholds,
                abstain_rate=risk.abstain_rate, per_class_risk=risk.per_class_risk,
                risk_version=RISK_VERSION),
            "clinical": ClinicalOutput.build(
                class_indices=class_idx, calibrated_probs=calibrated,
                prediction_sets=conf.prediction_sets, risk_scores=risk.risk_scores,
                risk_bands=risk.bands, abstain=risk.abstain, class_names=class_names,
                patient_ids=prep["p_test"]),
        }

        version_bundle = ctx["version_bundle"].merged(
            evaluation_version=EVALUATION_VERSION, calibration_version=CALIBRATION_VERSION,
            conformal_version=CONFORMAL_VERSION, coverage_version=COVERAGE_VERSION,
            risk_version=RISK_VERSION, benchmark_version=BENCHMARK_VERSION)
        ctx["version_bundle"] = version_bundle

        headline = {
            "model_name": ctx["model"].name,
            "accuracy": ev.metrics["accuracy"], "macro_f1": ev.metrics["macro_f1"],
            "macro_auroc": ev.metrics["macro_auroc"], "temperature": round(cal.temperature, 6),
            "ece_post": round(cal.post_ece, 6), "target_coverage": conf.target_coverage,
            "observed_coverage": round(cov.observed_coverage, 6), "coverage_reliable": cov.reliable,
            "mean_set_size": round(float(conf.set_sizes().mean()), 6),
            "abstain_rate": round(float(risk.abstain_rate), 6),
        }
        outputs["summary"] = SummaryOutput(model_name=ctx["model"].name, headline=headline,
                                           version_bundle=version_bundle.to_dict())
        ctx["outputs"] = outputs
        ctx["headline"] = headline
        return {"signature": hash_obj({"headline": headline, "metrics": ev.metrics}),
                "accuracy": ev.metrics["accuracy"], "macro_f1": ev.metrics["macro_f1"]}

    def _stage_artifact_registration(self, ctx: dict) -> dict:
        store: InferenceArtifactStore = ctx["store"]
        outputs = ctx["outputs"]
        for name, contract in outputs.items():
            store.save_output(f"outputs/{name}_output", contract)
        store.save_json("dataset_intelligence", ctx["intelligence_dict"])

        # Benchmark registration (reuse V1-P5 benchmarking; patient-disjoint enforced)
        ev = ctx["evaluation_result"]
        cal_ece, cal_mce, _ = expected_calibration_error(ctx["calibrated_test_probs"], ctx["prepared"]["y_test"])
        ev_final = EvaluationResult(
            evaluation_version=EVALUATION_VERSION, metrics=ev.metrics, per_class=ev.per_class,
            evaluation_audit=ev.evaluation_audit,
            calibration={"calibrated_ece": round(cal_ece, 6), "calibrated_mce": round(cal_mce, 6),
                         "calibrated_brier": round(brier_score(ctx["calibrated_test_probs"], ctx["prepared"]["y_test"]), 6),
                         "temperature": round(ctx["calibration_result"].temperature, 6)},
            coverage={"target_coverage": ctx["coverage_result"].target_coverage,
                      "observed_coverage": round(ctx["coverage_result"].observed_coverage, 6),
                      "reliable": ctx["coverage_result"].reliable})
        bench = build_benchmark_record(
            model_name=ctx["model"].name, model_version=ctx["model_version"], evaluation=ev_final,
            dataset_version=ctx["dataset"].dataset_version, split_summary=ctx["split"].summary(),
            version_bundle=ctx["version_bundle"].to_dict(),
            lineage_bundle=[r.to_dict() for r in ctx["lineage"].chain(ctx["training_lineage_id"])])
        ctx["benchmark_registry"].register(bench)
        ctx["benchmark"] = bench
        store.save_json("benchmark_record", bench.to_dict())

        ctx["artifact_refs"] = store.refs()
        return {"signature": hash_obj({"artifacts": sorted(ctx["artifact_refs"])}),
                "n_artifacts": len(ctx["artifact_refs"])}

    def _stage_lineage_registration(self, ctx: dict) -> dict:
        vb = ctx["version_bundle"]
        # evaluation lineage (parent: training)
        eval_lineage = ctx["lineage"].record(make_lineage_record(
            kind="evaluation", versions=vb,
            inputs={"model_version": ctx["model_version"], "split_version": ctx["split"].split_version},
            outputs={"metrics": ctx["evaluation_result"].metrics,
                     "audit_signature": ctx["evaluation_result"].evaluation_audit["audit_signature"]},
            parents=(ctx["training_lineage_id"],)))
        # uncertainty lineage (parent: evaluation)
        unc_lineage = ctx["lineage"].record(make_lineage_record(
            kind="uncertainty", versions=vb,
            inputs={"calibration_patients": list(ctx["split"].calibration_patients),
                    "test_patients": list(ctx["split"].test_patients)},
            outputs={"temperature": ctx["calibration_result"].temperature,
                     "observed_coverage": ctx["coverage_result"].observed_coverage},
            parents=(eval_lineage.lineage_id,)))
        # inference lineage (parents: training, evaluation, uncertainty)
        inf_lineage = ctx["lineage"].record(make_inference_lineage(
            version_bundle=vb,
            inputs={"pipeline_signature": self.config.signature(),
                    "dataset_version": ctx["dataset"].dataset_version,
                    "split_version": ctx["split"].split_version},
            outputs={"headline": ctx["headline"],
                     "artifact_refs": sorted(ctx["artifact_refs"])},
            parents=(ctx["training_lineage_id"], eval_lineage.lineage_id, unc_lineage.lineage_id)))
        ctx["evaluation_lineage_id"] = eval_lineage.lineage_id
        ctx["uncertainty_lineage_id"] = unc_lineage.lineage_id
        ctx["inference_lineage_id"] = inf_lineage.lineage_id
        return {"signature": hash_obj({"inference_lineage_id": inf_lineage.lineage_id}),
                "lineage_id": inf_lineage.lineage_id}

    def _stage_audit_generation(self, ctx: dict) -> dict:
        store: InferenceArtifactStore = ctx["store"]
        vb = ctx["version_bundle"]
        # inference id is content-addressed (excludes timing)
        inference_id = content_id("inference", {
            "pipeline_signature": self.config.signature(),
            "model_version": ctx["model_version"],
            "evaluation": ctx["evaluation_result"].metrics,
            "calibration": round(ctx["calibration_result"].temperature, 6),
            "conformal": round(ctx["conformal_result"].qhat, 6),
            "coverage": round(ctx["coverage_result"].observed_coverage, 6),
            "outputs": {k: ctx["_stage_signatures"].get("output_generation")
                        for k in ["summary"]},
        })
        ctx["inference_id"] = inference_id

        inference_record = InferenceRecord(
            inference_id=inference_id, pipeline_version=self.config.pipeline_version,
            dataset_version=ctx["dataset"].dataset_version,
            preprocessing_version=ctx["preprocessing_version"], model_version=ctx["model_version"],
            evaluation_version=EVALUATION_VERSION, calibration_version=CALIBRATION_VERSION,
            conformal_version=CONFORMAL_VERSION, lineage_id=ctx["inference_lineage_id"])
        ctx["inference_registry"].register(inference_record)
        ctx["inference_record"] = inference_record.to_dict()

        execution_dict = {"content_signature": "pending", "stages": list(ctx["_stage_signatures"].keys())}
        # build reports
        reports = {
            "inference_report": build_inference_report(
                inference_id=inference_id, lineage_id=ctx["inference_lineage_id"],
                version_bundle=vb.to_dict(), prediction=ctx["outputs"]["prediction"].to_dict(),
                probability=ctx["outputs"]["probability"].to_dict(),
                evaluation_metrics=ctx["evaluation_result"].metrics, execution=execution_dict),
            "calibration_report": build_calibration_report(
                inference_id=inference_id, lineage_id=ctx["inference_lineage_id"],
                version_bundle=vb.to_dict(), calibration=ctx["outputs"]["calibration"].to_dict()),
            "coverage_report": build_coverage_report(
                inference_id=inference_id, lineage_id=ctx["inference_lineage_id"],
                version_bundle=vb.to_dict(), coverage=ctx["outputs"]["coverage"].to_dict(),
                conformal=ctx["outputs"]["conformal"].to_dict()),
            "risk_report": build_risk_report(
                inference_id=inference_id, lineage_id=ctx["inference_lineage_id"],
                version_bundle=vb.to_dict(), risk=ctx["outputs"]["risk"].to_dict()),
            "summary_report": build_summary_report(
                inference_id=inference_id, lineage_id=ctx["inference_lineage_id"],
                version_bundle=vb.to_dict(), summary=ctx["outputs"]["summary"].to_dict(),
                evaluation_metrics=ctx["evaluation_result"].metrics),
        }

        # inference validation (7 checks) — needs an audit skeleton first
        audit_skeleton = {
            "lineage_chain": [r.to_dict() for r in ctx["lineage"].chain(ctx["inference_lineage_id"])],
            "version_bundle": vb.to_dict(),
            "execution": {"content_signature": "pending"},
        }
        validator = InferenceValidator()
        vreport = validator.validate(
            version_bundle=vb.to_dict(), artifact_store=store, lineage_tracker=ctx["lineage"],
            inference_lineage_id=ctx["inference_lineage_id"],
            calibration=ctx["outputs"]["calibration"].to_dict(),
            coverage=ctx["outputs"]["coverage"].to_dict(),
            probability=ctx["outputs"]["probability"].to_dict(),
            clinical=ctx["outputs"]["clinical"].to_dict(), audit=audit_skeleton,
            n_inference=ctx["outputs"]["prediction"].to_dict()["n"])
        ctx["validation"] = vreport.to_dict()

        audit_report = build_audit_report(
            inference_id=inference_id, lineage_id=ctx["inference_lineage_id"], version_bundle=vb.to_dict(),
            lineage_chain=audit_skeleton["lineage_chain"], execution=audit_skeleton["execution"],
            validation=ctx["validation"], inference_record=ctx["inference_record"],
            intelligence=ctx["intelligence_dict"])
        reports["audit_report"] = audit_report
        ctx["audit"] = audit_report

        for name, rep in reports.items():
            store.save_json(f"reports/{name}", rep)
        ctx["reports"] = reports
        ctx["artifact_refs"] = store.refs()
        return {"signature": hash_obj({"inference_id": inference_id,
                                       "validation_ok": vreport.ok}),
                "inference_id": inference_id, "validation_ok": vreport.ok}

    # ------------------------------------------------------------------ driver
    def _stages(self) -> list[Stage]:
        return [
            Stage("dataset_ingestion", OFFLINE_INFERENCE_VERSION, self._stage_ingestion),
            Stage("validation", OFFLINE_INFERENCE_VERSION, self._stage_validation),
            Stage("preprocessing", OFFLINE_INFERENCE_VERSION, self._stage_preprocessing),
            Stage("dataset_intelligence", OFFLINE_INFERENCE_VERSION, self._stage_dataset_intelligence),
            Stage("evaluation_preparation", OFFLINE_INFERENCE_VERSION, self._stage_evaluation_preparation),
            Stage("model_selection", OFFLINE_INFERENCE_VERSION, self._stage_model_selection),
            Stage("inference", OFFLINE_INFERENCE_VERSION, self._stage_inference),
            Stage("calibration", OFFLINE_INFERENCE_VERSION, self._stage_calibration),
            Stage("conformal_prediction", OFFLINE_INFERENCE_VERSION, self._stage_conformal),
            Stage("coverage_validation", OFFLINE_INFERENCE_VERSION, self._stage_coverage),
            Stage("risk_assessment", OFFLINE_INFERENCE_VERSION, self._stage_risk),
            Stage("output_generation", OFFLINE_INFERENCE_VERSION, self._stage_output_generation),
            Stage("artifact_registration", OFFLINE_INFERENCE_VERSION, self._stage_artifact_registration),
            Stage("lineage_registration", OFFLINE_INFERENCE_VERSION, self._stage_lineage_registration),
            Stage("audit_generation", OFFLINE_INFERENCE_VERSION, self._stage_audit_generation),
        ]

    def run(self) -> OrchestratorResult:
        store = InferenceArtifactStore(self.output_dir)
        ctx = {
            "store": store,
            "model_registry": ModelRegistry(),
            "benchmark_registry": BenchmarkRegistry(),
            "inference_registry": InferenceRegistry(),
            "lineage": LineageTracker(),
        }
        engine = ExecutionEngine(self.config.pipeline_version, clock=self.clock)
        execution = engine.execute(self._stages(), ctx)
        if not execution.ok:
            raise RuntimeError(f"inference pipeline failed at stage {execution.failed_stage}: "
                               f"{[s.error for s in execution.stages if s.error]}")

        # persist execution trace + registries + a top-level index for the application
        store.save_json("execution_trace", execution.to_dict())
        store.save_json("registries/inference_registry", ctx["inference_registry"].to_dict())
        store.save_json("registries/model_registry", ctx["model_registry"].to_dict())
        store.save_json("registries/benchmark_registry", ctx["benchmark_registry"].to_dict())
        store.save_json("registries/lineage", ctx["lineage"].to_dict())

        index = {
            "offline_inference_version": OFFLINE_INFERENCE_VERSION,
            "inference_id": ctx["inference_id"],
            "run_signature": self.run_signature,
            "pipeline_config": self.config.as_dict(),
            "version_bundle": ctx["version_bundle"].to_dict(),
            "lineage_id": ctx["inference_lineage_id"],
            "execution_content_signature": execution.content_signature(),
            "validation": ctx["validation"],
            "outputs": {name: f"outputs/{name}_output.json" for name in ctx["outputs"]},
            "reports": {name: f"reports/{name}.json" for name in ctx["reports"]},
            "registries": {
                "inference_registry": "registries/inference_registry.json",
                "model_registry": "registries/model_registry.json",
                "benchmark_registry": "registries/benchmark_registry.json",
                "lineage": "registries/lineage.json",
            },
            "dataset_intelligence": "dataset_intelligence.json",
            "artifacts_verified": store.verify(),
        }
        store.save_json("inference_index", index)

        return OrchestratorResult(
            inference_id=ctx["inference_id"], output_dir=self.output_dir, execution=execution,
            version_bundle=ctx["version_bundle"].to_dict(), outputs={k: v.to_dict() for k, v in ctx["outputs"].items()},
            artifact_refs=store.refs(), inference_record=ctx["inference_record"], validation=ctx["validation"],
            audit=ctx["audit"], lineage_id=ctx["inference_lineage_id"],
            registries={"inference": ctx["inference_registry"], "model": ctx["model_registry"],
                        "benchmark": ctx["benchmark_registry"], "lineage": ctx["lineage"]})
