"""The five research-app workflows (build Page view-models from registered artifacts)."""

from __future__ import annotations

from ..schemas import Page
from ..state import AppState
from ..components import kv_panel, table, badges, text, metric_row
from ..visualizations import (
    eeg_metadata, channel_layout, dataset_statistics, class_distribution,
    evaluation_metrics, calibration_curve, coverage_curve, risk_profile,
    benchmark_comparison, lineage_graph, version_graph,
)


def upload_workflow(state: AppState) -> Page:
    """Workflow 1 — EEG upload: validate file, show metadata / quality / readiness."""
    di = state.dataset_intelligence
    profile = di.get("profile", {})
    quality = di.get("quality_analysis", {})
    readiness = di.get("evaluation_readiness", {})
    sections = [
        badges("File Validation", [
            ("ingested", bool(profile.get("dataset_version"))),
            ("quality passed", quality.get("passed", False)),
            ("evaluation ready", readiness.get("ready", False)),
        ]),
        kv_panel("File Metadata", {
            "dataset_version": profile.get("dataset_version"),
            "n_windows": profile.get("n_windows"),
            "n_patients": profile.get("n_patients"),
            "n_channels": profile.get("n_channels"),
            "n_samples": profile.get("n_samples"),
            "sampling_rate_hz": profile.get("sampling_rate_hz"),
        }),
        metric_row("Quality Report", {
            "quality_score": quality.get("quality_score"),
            "n_ok": quality.get("n_ok"),
            "n_with_nan": quality.get("n_with_nan"),
            "n_with_inf": quality.get("n_with_inf"),
            "n_flatline": quality.get("n_flatline"),
        }),
        table("Readiness Report", ["check", "passed", "detail"],
              [[c["name"], c["passed"], c["detail"]] for c in readiness.get("checks", [])]),
    ]
    viz = [eeg_metadata(profile), dataset_statistics(profile)]
    return Page("upload", "EEG Upload", sections, viz)


def dataset_intelligence_workflow(state: AppState) -> Page:
    """Workflow 2 — dataset intelligence."""
    di = state.dataset_intelligence
    profile = di.get("profile", {})
    patients = di.get("patient_profile", {})
    channels = di.get("channel_profile", {})
    quality = di.get("quality_analysis", {})
    leakage = di.get("leakage_analysis", {})
    readiness = di.get("evaluation_readiness", {})
    sections = [
        kv_panel("Dataset Profile", {
            "dataset_version": profile.get("dataset_version"),
            "n_windows": profile.get("n_windows"), "n_classes": profile.get("n_classes"),
            "class_counts": profile.get("class_counts"),
        }),
        kv_panel("Patient Profile", {
            "n_patients": patients.get("n_patients"),
            "windows_per_patient": patients.get("windows_per_patient"),
        }),
        table("Channel Profile", ["channel", "mean", "std", "min", "max"],
              [[c["channel"], c["mean"], c["std"], c["min"], c["max"]]
               for c in channels.get("channels", [])]),
        metric_row("Quality Analysis", {
            "quality_score": quality.get("quality_score"), "passed": quality.get("passed"),
        }),
        badges("Leakage Analysis (patient-disjoint, NR-3)", [
            ("patient_disjoint", leakage.get("patient_disjoint", False)),
            ("split_present", leakage.get("split_present", False)),
        ]),
        badges("Evaluation Readiness", [(c["name"], c["passed"]) for c in readiness.get("checks", [])]),
    ]
    viz = [class_distribution(profile), channel_layout(profile), dataset_statistics(profile)]
    return Page("dataset", "Dataset Intelligence", sections, viz)


def inference_workflow(state: AppState) -> Page:
    """Workflow 3 — inference results + uncertainty (faithful, NR-4)."""
    o = state.outputs
    summary = o.get("summary", {})
    headline = summary.get("headline", {})
    clinical = o.get("clinical", {})
    coverage = o.get("coverage", {})
    calibration = o.get("calibration", {})
    conformal = o.get("conformal", {})
    risk = o.get("risk", {})
    # a small preview of per-window clinical records (faithful uncertainty per row)
    preview = clinical.get("records", [])[:10]
    sections = [
        badges("Inference Status", [
            ("completed", True),
            ("validation ok", state.index["validation"]["ok"]),
            ("coverage reliable", coverage.get("reliable", False)),
        ]),
        metric_row("Headline", headline),
        kv_panel("Calibration", {
            "method": calibration.get("method"), "temperature": calibration.get("temperature"),
            "ece_post": (calibration.get("ece") or {}).get("post"),
        }),
        kv_panel("Conformal", {
            "target_coverage": conformal.get("target_coverage"), "qhat": conformal.get("qhat"),
            "mean_set_size": conformal.get("mean_set_size"),
        }),
        kv_panel("Coverage", {
            "observed_coverage": coverage.get("observed_coverage"),
            "coverage_drift": coverage.get("coverage_drift"),
            "n_violations": coverage.get("n_violations"), "reliable": coverage.get("reliable"),
        }),
        kv_panel("Risk", {"abstain_rate": risk.get("abstain_rate"),
                          "band_counts": risk.get("band_counts")}),
        table("Per-window Predictions (preview)",
              ["#", "predicted", "confidence", "conformal set", "risk band", "abstain"],
              [[r["window_index"], r["predicted_class"], r["calibrated_confidence"],
                ", ".join(r["conformal_set"]), r["risk_band"], r["abstain"]] for r in preview]),
        kv_panel("Version Bundle", state.index["version_bundle"]),
    ]
    viz = [calibration_curve(calibration), coverage_curve(coverage), risk_profile(risk)]
    return Page("inference", "Inference", sections, viz)


def benchmark_workflow(state: AppState) -> Page:
    """Workflow 4 — benchmarks."""
    breg = state.registries.get("benchmark_registry", {})
    o = state.outputs
    metrics = state.reports.get("summary_report", {}).get("evaluation_metrics", {})
    split = None
    rows = []
    for bid, rec in breg.get("benchmarks", {}).items():
        rows.append([rec.get("model_name"), bid.split("+")[-1][:8],
                     rec.get("metrics", {}).get("accuracy"),
                     rec.get("metrics", {}).get("macro_f1"),
                     rec.get("metrics", {}).get("macro_auroc")])
        split = rec.get("split_summary")
    sections = [
        table("Model Benchmarks", ["model", "benchmark", "accuracy", "macro_f1", "macro_auroc"], rows),
        kv_panel("Evaluation Results", {k: metrics.get(k) for k in
                                        ["accuracy", "balanced_accuracy", "macro_f1",
                                         "macro_sensitivity", "macro_specificity", "macro_auroc"]}),
        kv_panel("Split Information (patient-disjoint)", {
            "split_version": (split or {}).get("split_version"),
            "n_train": (split or {}).get("n_train"), "n_calibration": (split or {}).get("n_calibration"),
            "n_test": (split or {}).get("n_test"),
            "train_patients": (split or {}).get("train_patients"),
            "test_patients": (split or {}).get("test_patients"),
        }),
        table("Benchmark History", ["benchmark_id", "model"],
              [[bid, rec.get("model_name")] for bid, rec in breg.get("benchmarks", {}).items()]),
    ]
    viz = [benchmark_comparison(breg, "macro_f1"),
           evaluation_metrics(metrics)]
    return Page("benchmark", "Benchmarks", sections, viz)


def audit_workflow(state: AppState) -> Page:
    """Workflow 5 — audit: lineage, artifacts, registries, versions, trails."""
    audit = state.audit_trail()
    lineage = audit["lineage"]
    artifacts = state.current_artifacts()
    inf_registry = audit["inference_registry"]
    audit_report = audit["audit_report"]
    inf_records = list(inf_registry.get("inferences", {}).values())
    sections = [
        badges("Validation Trail", [
            (c["name"], c["passed"]) for c in state.index["validation"].get("checks", [])]),
        kv_panel("Inference Record", inf_records[0] if inf_records else {}),
        table("Lineage (decision/provenance trail)", ["lineage_id", "kind", "parents"],
              [[lid, rec.get("kind"), ", ".join(p.split("+")[-1][:6] for p in rec.get("parents", []))]
               for lid, rec in lineage.get("records", {}).items()]),
        table("Registered Artifacts (checksummed)", ["artifact", "checksum", "bytes"],
              [[name, ref.get("checksum", "")[:16], ref.get("size_bytes")]
               for name, ref in sorted(artifacts.items())]),
        kv_panel("Registries", {
            "inference": inf_registry.get("n_inferences"),
            "models": state.registries.get("model_registry", {}).get("n_models"),
            "benchmarks": state.registries.get("benchmark_registry", {}).get("n_benchmarks"),
            "lineage_records": lineage.get("n_records"),
        }),
        badges("Traceability", [("traceable", audit_report.get("traceable", False))]),
    ]
    viz = [lineage_graph(lineage), version_graph(state.index["version_bundle"])]
    return Page("audit", "Audit", sections, viz)


def all_workflows(state: AppState) -> list:
    return [
        upload_workflow(state),
        dataset_intelligence_workflow(state),
        inference_workflow(state),
        benchmark_workflow(state),
        audit_workflow(state),
    ]
