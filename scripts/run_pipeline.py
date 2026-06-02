"""End-to-end NeuroVision AI V1 pipeline orchestrator (V1-P5 + V1-P6).

Executes the full required deliverable with complete traceability:

    Dataset → Preprocessing → Patient-Disjoint Split → Baseline Model →
    Evaluation → Calibration → Conformal Prediction → Coverage Validation →
    Risk Assessment → Benchmark Registration

This is the single place the ``ml`` and ``evaluation`` layers are composed — which
is legal because ``scripts/`` sits above both in the DAG and may import all
modules (``ml`` itself never imports ``evaluation``, NR-8).

Everything is deterministic and reproducible: the same ``PipelineConfig`` produces
the same model versions, lineage ids, benchmark ids, and artifact checksums.

Run:
    python -m scripts.run_pipeline            # default config
    python -m scripts.run_pipeline --steps 200 --alpha 0.1 --output artifacts/_runs/demo
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np

from datasets import generate_dataset, SyntheticConfig, patient_disjoint_split, SplitConfig
from preprocessing import PreprocessingConfig

from ml.models.base import ModelConfig
from ml.training import Trainer, TrainingConfig
from ml.artifacts import ArtifactStore
from ml.registry import ModelRegistry, ModelStatus
from ml.lineage import LineageTracker, make_lineage_record
from ml.provenance import content_id
from ml.schemas import (
    ProbabilityOutput, ClassOutput, UncertaintyPlaceholder, ConformalOutput, Prediction,
)
from ml.benchmarking import EvaluationResult, BenchmarkRegistry, build_benchmark_record
from ml.uncertainty import (
    UncertaintyPipeline, UncertaintyValidator, UncertaintyRegistry, UncertaintyRecord,
    CONFORMAL_VERSION, CALIBRATION_VERSION, COVERAGE_VERSION, RISK_VERSION,
)
from ml.uncertainty.registry.registry import make_uncertainty_id
from ml.uncertainty.lineage import make_uncertainty_lineage
from ml.uncertainty.reports import (
    build_calibration_report, build_conformal_report, build_coverage_report,
    build_risk_report, build_summary_report, build_audit_report,
)
from ml.version import BENCHMARK_VERSION

from evaluation import (
    PatientDisjointEvaluator, EVALUATION_VERSION,
    expected_calibration_error, brier_score,
)


@dataclass
class PipelineConfig:
    synthetic: SyntheticConfig = field(default_factory=SyntheticConfig)
    split: SplitConfig = field(default_factory=SplitConfig)
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    models: tuple[str, ...] = ("simple_cnn", "eegnet", "tcn")
    model_seed: int = 7
    alpha: float = 0.1
    owner: str = "neurovision-ml"
    output_dir: Optional[str] = None

    def run_signature(self) -> str:
        return content_id("run", {
            "synthetic": self.synthetic.as_dict(),
            "split": self.split.as_dict(),
            "preprocessing": self.preprocessing.as_dict(),
            "training": self.training.as_dict(),
            "models": list(self.models),
            "model_seed": self.model_seed,
            "alpha": self.alpha,
        })


def run_pipeline(config: Optional[PipelineConfig] = None, verbose: bool = True) -> dict:
    cfg = config or PipelineConfig()
    run_id = cfg.run_signature()
    output_dir = cfg.output_dir or f"artifacts/_runs/{run_id}"

    store = ArtifactStore(output_dir)
    model_registry = ModelRegistry()
    benchmark_registry = BenchmarkRegistry()
    uncertainty_registry = UncertaintyRegistry()
    lineage = LineageTracker()
    evaluator = PatientDisjointEvaluator()
    uncertainty_validator = UncertaintyValidator()

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    # 1) Dataset
    dataset = generate_dataset(cfg.synthetic)
    log(f"[1] Dataset        : {dataset.dataset_version}  "
        f"(n={dataset.n_windows}, patients={len(dataset.patients())}, classes={dataset.n_classes})")

    # 2) Preprocessing + 3) Patient-Disjoint Split
    split = patient_disjoint_split(dataset, cfg.split)
    split.assert_patient_disjoint()
    log(f"[2] Preprocessing  : {cfg.preprocessing.as_dict()}")
    log(f"[3] Split          : {split.split_version}  "
        f"(train={split.train_idx.size}, cal={split.calibration_idx.size}, test={split.test_idx.size}; "
        f"patient-disjoint OK)")

    trainer = Trainer(store, model_registry, lineage)
    per_model: dict[str, dict] = {}

    for name in cfg.models:
        log(f"\n=== Model: {name} ===")
        model_config = ModelConfig(
            name=name,
            n_channels=dataset.n_channels,
            n_samples=dataset.n_samples,
            n_classes=dataset.n_classes,
            seed=cfg.model_seed,
        )

        # 4) Baseline Model (deterministic training, governed)
        result = trainer.run(
            dataset=dataset, split=split, model_config=model_config,
            training_config=cfg.training, preprocessing_config=cfg.preprocessing, owner=cfg.owner,
        )
        log(f"[4] Trained        : {result.model_version}")
        log(f"    training valid : ok={result.validation_report['ok']} "
            f"(train_acc={result.training_history['final_train_accuracy']:.3f})")

        prepared = result.prepared
        test_probs = result.model.predict_proba(prepared.x_test)

        # 5) Evaluation (patient-disjoint; through the evaluation framework)
        ev = evaluator.evaluate(
            probabilities=test_probs, labels=prepared.y_test, patient_ids=prepared.p_test,
            class_names=dataset.class_names, dataset_version=dataset.dataset_version,
            split_version=split.split_version, train_patient_ids=split.train_patients,
        )
        model_registry.attach_evaluation(result.model_version, EVALUATION_VERSION)
        model_registry.set_status(result.model_version, ModelStatus.EVALUATED)
        eval_bundle = result.version_bundle.merged(evaluation_version=EVALUATION_VERSION)
        eval_lineage = lineage.record(make_lineage_record(
            kind="evaluation", versions=eval_bundle,
            inputs={"model_version": result.model_version, "split_version": split.split_version,
                    "test_patients": list(split.test_patients)},
            outputs={"metrics": ev.metrics, "evaluation_audit_signature": ev.evaluation_audit["audit_signature"]},
            parents=(result.lineage_id,),
        ))
        log(f"[5] Evaluation     : patient_disjoint={ev.is_patient_disjoint()} "
            f"acc={ev.metrics['accuracy']:.3f} macro_f1={ev.metrics['macro_f1']:.3f} "
            f"macro_auroc={ev.metrics['macro_auroc']}")

        # 6-9) Calibration -> Conformal -> Coverage -> Risk
        calib_logits = result.model.forward_logits(prepared.x_calibration)
        test_logits = result.model.forward_logits(prepared.x_test)
        unc = UncertaintyPipeline(alpha=cfg.alpha).run(
            calib_logits=calib_logits, calib_labels=prepared.y_calibration,
            eval_logits=test_logits, eval_labels=prepared.y_test,
            class_names=dataset.class_names,
            dataset_version=dataset.dataset_version, split_version=split.split_version,
        )
        log(f"[6] Calibration    : T={unc.temperature:.3f} "
            f"ECE {unc.calibration.pre_ece:.3f}->{unc.calibration.post_ece:.3f} (improved={unc.calibration.improved()})")
        log(f"[7] Conformal      : target={unc.conformal.target_coverage:.2f} qhat={unc.conformal.qhat:.4f} "
            f"mean_set_size={float(unc.conformal.set_sizes().mean()):.2f}")
        log(f"[8] Coverage       : observed={unc.coverage.observed_coverage:.3f} "
            f"reliable={unc.coverage.reliable} violations={unc.coverage.n_violations}")
        log(f"[9] Risk           : abstain_rate={unc.risk.abstain_rate:.3f} "
            f"low_conf_alerts={unc.risk.low_confidence_alerts.size}")

        # evaluation independently measures coverage + post-calibration calibration
        coverage_meas = evaluator.measure_coverage(
            prediction_sets=unc.conformal.prediction_sets, labels=prepared.y_test,
            target_coverage=unc.conformal.target_coverage,
        )
        cal_ece, cal_mce, _ = expected_calibration_error(unc.calibrated_test_probs, prepared.y_test)
        calibration_bundle = {
            "raw": ev.calibration,
            "calibrated": {"ece": round(cal_ece, 6), "mce": round(cal_mce, 6),
                           "brier": round(brier_score(unc.calibrated_test_probs, prepared.y_test), 6),
                           "temperature": round(unc.temperature, 6)},
        }

        # uncertainty lineage (parent: evaluation -> training)
        unc_bundle = eval_bundle.merged(
            calibration_version=CALIBRATION_VERSION, conformal_version=CONFORMAL_VERSION,
            coverage_version=COVERAGE_VERSION, risk_version=RISK_VERSION,
        )
        unc_lineage = lineage.record(make_uncertainty_lineage(
            version_bundle=unc_bundle,
            inputs={"model_version": result.model_version,
                    "calibration_patients": list(split.calibration_patients),
                    "test_patients": list(split.test_patients)},
            outputs={"temperature": unc.temperature,
                     "target_coverage": unc.conformal.target_coverage,
                     "observed_coverage": unc.coverage.observed_coverage},
            parents=(eval_lineage.lineage_id,),
        ))

        # uncertainty validation
        uval = uncertainty_validator.validate(
            calibration=unc.calibration, conformal=unc.conformal, coverage=unc.coverage,
            calibration_patients=split.calibration_patients, test_patients=split.test_patients,
            lineage_tracker=lineage, lineage_id=unc_lineage.lineage_id, clinically_complete=True,
        )
        log(f"    uncertainty valid: ok={uval.ok}")

        # uncertainty registry
        uid = make_uncertainty_id(result.model_version, dataset.dataset_version, EVALUATION_VERSION,
                                  extra={"alpha": cfg.alpha})
        uncertainty_registry.register(UncertaintyRecord(
            uncertainty_id=uid, model_version=result.model_version,
            dataset_version=dataset.dataset_version, lineage_id=unc_lineage.lineage_id,
            evaluation_version=EVALUATION_VERSION, temperature=unc.temperature,
            target_coverage=unc.conformal.target_coverage, observed_coverage=unc.coverage.observed_coverage,
        ))

        # 10) Benchmark Registration (through evaluation result; refuses non-disjoint)
        ev_final = EvaluationResult(
            evaluation_version=EVALUATION_VERSION, metrics=ev.metrics, per_class=ev.per_class,
            evaluation_audit=ev.evaluation_audit, calibration=calibration_bundle, coverage=coverage_meas,
        )
        bench_bundle = unc_bundle.merged(benchmark_version=BENCHMARK_VERSION)
        bench_lineage = lineage.record(make_lineage_record(
            kind="benchmark", versions=bench_bundle,
            inputs={"model_version": result.model_version, "evaluation_version": EVALUATION_VERSION},
            outputs={"macro_f1": ev.metrics["macro_f1"], "observed_coverage": unc.coverage.observed_coverage},
            parents=(eval_lineage.lineage_id, unc_lineage.lineage_id),
        ))
        benchmark = build_benchmark_record(
            model_name=name, model_version=result.model_version, evaluation=ev_final,
            dataset_version=dataset.dataset_version, split_summary=split.summary(),
            version_bundle=bench_bundle.to_dict(),
            lineage_bundle=[r.to_dict() for r in lineage.chain(bench_lineage.lineage_id)],
        )
        benchmark_registry.register(benchmark)
        model_registry.attach_benchmark(result.model_version, BENCHMARK_VERSION)
        model_registry.set_status(result.model_version, ModelStatus.BENCHMARKED)
        model_registry.set_status(result.model_version, ModelStatus.REGISTERED)
        log(f"[10] Benchmark      : {benchmark.benchmark_id}  (registered, model status=registered)")

        # Complete clinical Prediction contract (NR-4: calibrated uncertainty attached)
        prediction = Prediction(
            probability=ProbabilityOutput(unc.calibrated_test_probs, dataset.class_names),
            classification=ClassOutput(unc.calibrated_test_probs.argmax(axis=1), dataset.class_names),
            metadata=result.metadata,
            uncertainty=UncertaintyPlaceholder(
                calibrated=True, calibration_version=CALIBRATION_VERSION, conformal_version=CONFORMAL_VERSION,
                confidence=unc.risk.confidence, risk_score=unc.risk.risk_scores, abstain=unc.risk.abstain,
                notes="calibrated (temperature) + conformal + risk attached",
            ),
            conformal=ConformalOutput(unc.conformal.prediction_sets, unc.conformal.target_coverage,
                                      dataset.class_names, CONFORMAL_VERSION),
        )

        # Reports (reproducible; written to the artifact store)
        prefix = f"{name}/{result.model_version}"
        store.save_json(f"{prefix}/reports/calibration_report", build_calibration_report(
            calibration=unc.calibration, reliability=unc.reliability,
            model_version=result.model_version, lineage_id=unc_lineage.lineage_id,
            version_bundle=unc_bundle.to_dict()))
        store.save_json(f"{prefix}/reports/conformal_report", build_conformal_report(
            conformal=unc.conformal, model_version=result.model_version,
            lineage_id=unc_lineage.lineage_id, version_bundle=unc_bundle.to_dict()))
        store.save_json(f"{prefix}/reports/coverage_report", build_coverage_report(
            coverage=unc.coverage, model_version=result.model_version,
            lineage_id=unc_lineage.lineage_id, version_bundle=unc_bundle.to_dict()))
        store.save_json(f"{prefix}/reports/risk_report", build_risk_report(
            risk=unc.risk, model_version=result.model_version,
            lineage_id=unc_lineage.lineage_id, version_bundle=unc_bundle.to_dict()))
        summary_report = build_summary_report(
            calibration=unc.calibration, conformal=unc.conformal, coverage=unc.coverage, risk=unc.risk,
            model_name=name, model_version=result.model_version, lineage_id=unc_lineage.lineage_id,
            version_bundle=bench_bundle.to_dict(), evaluation_audit=ev.evaluation_audit)
        store.save_json(f"{prefix}/reports/summary_report", summary_report)
        audit_report = build_audit_report(
            model_version=result.model_version, lineage_id=bench_lineage.lineage_id,
            version_bundle=bench_bundle.to_dict(),
            lineage_chain=[r.to_dict() for r in lineage.chain(bench_lineage.lineage_id)],
            uncertainty_record=uncertainty_registry.get(uid).to_dict(),
            validation_report={"training": result.validation_report, "uncertainty": uval.to_dict()},
            evaluation_audit=ev.evaluation_audit)
        store.save_json(f"{prefix}/reports/audit_report", audit_report)
        store.save_json(f"{prefix}/benchmark_record", benchmark.to_dict())

        per_model[name] = {
            "model_version": result.model_version,
            "status": model_registry.get(result.model_version).status.value,
            "metrics": ev.metrics,
            "patient_disjoint": ev.is_patient_disjoint(),
            "calibration": {"temperature": unc.temperature,
                            "ece_pre": unc.calibration.pre_ece, "ece_post": unc.calibration.post_ece},
            "coverage": {"target": unc.conformal.target_coverage,
                         "observed": unc.coverage.observed_coverage, "reliable": unc.coverage.reliable},
            "risk": {"abstain_rate": unc.risk.abstain_rate},
            "benchmark_id": benchmark.benchmark_id,
            "lineage": {"training": result.lineage_id, "evaluation": eval_lineage.lineage_id,
                        "uncertainty": unc_lineage.lineage_id, "benchmark": bench_lineage.lineage_id},
            "clinical_prediction_complete": prediction.is_clinically_complete(),
            "training_validation_ok": result.validation_report["ok"],
            "uncertainty_validation_ok": uval.ok,
        }

    # Persist registries + lineage + pipeline summary (reproducible artifacts)
    store.save_json("registries/model_registry", model_registry.to_dict())
    store.save_json("registries/benchmark_registry", benchmark_registry.to_dict())
    store.save_json("registries/uncertainty_registry", uncertainty_registry.to_dict())
    store.save_json("registries/lineage", lineage.to_dict())

    pipeline_summary = {
        "run_id": run_id,
        "dataset_version": dataset.dataset_version,
        "split_version": split.split_version,
        "preprocessing_version": prepared.preprocessing_version,
        "evaluation_version": EVALUATION_VERSION,
        "models": per_model,
        "leaderboard": benchmark_registry.leaderboard("macro_f1"),
        "n_models_registered": len(model_registry.list_models()),
        "n_benchmarks": len(benchmark_registry.list_benchmarks()),
        "artifacts_verified": store.verify(),
    }
    summary_ref = store.save_json("pipeline_summary", pipeline_summary)

    log("\n=== Pipeline complete ===")
    log(f"run_id={run_id}")
    log(f"artifacts at: {output_dir}  (manifest verified: {store.verify()})")
    log("leaderboard (macro_f1): " +
        ", ".join(f"{r['model_name']}={r['macro_f1']:.3f}" for r in pipeline_summary["leaderboard"]))

    return {
        "run_id": run_id,
        "output_dir": output_dir,
        "pipeline_summary": pipeline_summary,
        "summary_checksum": summary_ref.checksum,
        "store": store,
        "model_registry": model_registry,
        "benchmark_registry": benchmark_registry,
        "uncertainty_registry": uncertainty_registry,
        "lineage": lineage,
    }


def _parse_args(argv=None) -> PipelineConfig:
    p = argparse.ArgumentParser(description="Run the NeuroVision AI V1 end-to-end pipeline.")
    p.add_argument("--patients", type=int, default=SyntheticConfig().n_patients)
    p.add_argument("--windows-per-patient", type=int, default=SyntheticConfig().windows_per_patient)
    p.add_argument("--steps", type=int, default=TrainingConfig().steps)
    p.add_argument("--alpha", type=float, default=0.1)
    p.add_argument("--models", nargs="+", default=["simple_cnn", "eegnet", "tcn"])
    p.add_argument("--output", type=str, default=None)
    args = p.parse_args(argv)
    return PipelineConfig(
        synthetic=SyntheticConfig(n_patients=args.patients, windows_per_patient=args.windows_per_patient),
        training=TrainingConfig(steps=args.steps),
        models=tuple(args.models),
        alpha=args.alpha,
        output_dir=args.output,
    )


if __name__ == "__main__":
    run_pipeline(_parse_args())
