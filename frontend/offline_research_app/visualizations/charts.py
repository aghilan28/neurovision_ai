"""Deterministic chart-spec builders (the eleven mandated visualizations).

Each returns a ``Visualization`` whose ``spec`` is a plain, JSON-able dict. No
randomness, no recomputation of domain values — they only reshape registered
artifact data for display.
"""

from __future__ import annotations

from ..schemas import Visualization


def eeg_metadata(profile: dict) -> Visualization:
    spec = {
        "rows": [
            ["dataset_version", profile.get("dataset_version")],
            ["n_windows", profile.get("n_windows")],
            ["n_patients", profile.get("n_patients")],
            ["n_channels", profile.get("n_channels")],
            ["n_samples", profile.get("n_samples")],
            ["sampling_rate_hz", profile.get("sampling_rate_hz")],
            ["n_classes", profile.get("n_classes")],
            ["sites", profile.get("sites")],
            ["montages", profile.get("montages")],
        ]
    }
    return Visualization("table", "EEG Metadata", spec)


def channel_layout(profile: dict) -> Visualization:
    """A simple 2-column hemisphere layout from channel names (L*/R*)."""
    names = profile.get("channel_names", [])
    nodes = []
    left = [n for n in names if str(n).startswith("L")]
    right = [n for n in names if str(n).startswith("R")]
    for i, n in enumerate(left):
        nodes.append({"label": n, "x": 0.3, "y": round((i + 1) / (len(left) + 1), 4), "group": "left"})
    for i, n in enumerate(right):
        nodes.append({"label": n, "x": 0.7, "y": round((i + 1) / (len(right) + 1), 4), "group": "right"})
    return Visualization("layout", "Channel Layout", {"nodes": nodes})


def dataset_statistics(profile: dict) -> Visualization:
    spec = {"labels": ["windows", "patients", "channels", "classes"],
            "values": [profile.get("n_windows", 0), profile.get("n_patients", 0),
                       profile.get("n_channels", 0), profile.get("n_classes", 0)]}
    return Visualization("bar", "Dataset Statistics", spec)


def class_distribution(profile: dict) -> Visualization:
    counts = profile.get("class_counts", {})
    return Visualization("bar", "Class Distribution",
                         {"labels": list(counts.keys()), "values": list(counts.values())})


def evaluation_metrics(metrics: dict) -> Visualization:
    keys = ["accuracy", "balanced_accuracy", "macro_f1", "macro_sensitivity",
            "macro_specificity", "macro_auroc"]
    labels, values = [], []
    for k in keys:
        v = metrics.get(k)
        if isinstance(v, (int, float)):
            labels.append(k)
            values.append(round(float(v), 4))
    return Visualization("bar", "Evaluation Metrics", {"labels": labels, "values": values, "max": 1.0})


def calibration_curve(calibration: dict) -> Visualization:
    """Reliability curve: bin mean-confidence (x) vs accuracy (y)."""
    bins = calibration.get("reliability_bins", [])
    points = [{"x": b["confidence"], "y": b["accuracy"]}
              for b in bins if b.get("confidence") is not None and b.get("accuracy") is not None]
    return Visualization("line", "Calibration Curve",
                         {"points": points, "diagonal": True,
                          "x_label": "confidence", "y_label": "accuracy",
                          "temperature": calibration.get("temperature")})


def coverage_curve(coverage: dict) -> Visualization:
    per_class = coverage.get("per_class_coverage", {})
    labels = list(per_class.keys())
    values = [round(float(per_class[k].get("coverage") or 0.0), 4) for k in labels]
    return Visualization("bar", "Coverage by Class",
                         {"labels": labels, "values": values, "max": 1.0,
                          "target_line": coverage.get("target_coverage"),
                          "observed": coverage.get("observed_coverage")})


def risk_profile(risk: dict) -> Visualization:
    band_counts = risk.get("band_counts", {})
    order = ["low", "medium", "high"]
    labels = [b for b in order if b in band_counts] + [b for b in band_counts if b not in order]
    values = [band_counts[b] for b in labels]
    return Visualization("bar", "Risk Band Profile",
                         {"labels": labels, "values": values,
                          "abstain_rate": risk.get("abstain_rate")})


def benchmark_comparison(benchmark_registry: dict, metric: str = "macro_f1") -> Visualization:
    rows = []
    for bid, rec in benchmark_registry.get("benchmarks", {}).items():
        rows.append({"model": rec.get("model_name"), "value": rec.get("metrics", {}).get(metric)})
    rows.sort(key=lambda r: (r["value"] is None, -(r["value"] or 0.0)))
    return Visualization("bar", f"Benchmark Comparison ({metric})",
                         {"labels": [r["model"] for r in rows],
                          "values": [round(float(r["value"]), 4) if r["value"] is not None else 0.0 for r in rows],
                          "max": 1.0, "metric": metric})


def lineage_graph(lineage_registry: dict) -> Visualization:
    """Nodes = lineage records (by kind); edges = parent links."""
    records = lineage_registry.get("records", {})
    nodes, edges = [], []
    for lid, rec in records.items():
        nodes.append({"id": lid, "label": rec.get("kind", "?"), "short": lid.split("+")[-1][:8]})
        for parent in rec.get("parents", []):
            edges.append({"from": parent, "to": lid})
    return Visualization("graph", "Lineage Graph", {"nodes": nodes, "edges": edges})


def version_graph(version_bundle: dict) -> Visualization:
    nodes = [{"label": k, "value": v} for k, v in version_bundle.items() if v]
    return Visualization("table", "Version Bundle",
                         {"rows": [[n["label"], n["value"]] for n in nodes]})
