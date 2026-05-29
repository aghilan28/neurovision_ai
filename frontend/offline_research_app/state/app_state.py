"""Application state: load + expose registered artifacts (presentation only).

The frontend's only contract with the rest of the system is the **registered
artifact layout** written by the backend: ``inference_index.json`` enumerates the
paths of every output, report, registry, and the dataset-intelligence record. The
app reads those files (stdlib ``json``) — it imports no domain code (NR-8).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


def _load(path: str):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


@dataclass
class AppState:
    """Loaded, read-only view of one inference run's registered artifacts."""

    run_dir: str
    index: dict
    outputs: dict = field(default_factory=dict)             # name -> dict
    reports: dict = field(default_factory=dict)             # name -> dict
    registries: dict = field(default_factory=dict)          # name -> dict
    dataset_intelligence: dict = field(default_factory=dict)
    manifest: dict = field(default_factory=dict)

    # ---- loading -------------------------------------------------------------
    @classmethod
    def load(cls, run_dir: str) -> "AppState":
        index = _load(os.path.join(run_dir, "inference_index.json"))
        outputs = {name: _load(os.path.join(run_dir, rel)) for name, rel in index["outputs"].items()}
        reports = {name: _load(os.path.join(run_dir, rel)) for name, rel in index["reports"].items()}
        registries = {name: _load(os.path.join(run_dir, rel)) for name, rel in index["registries"].items()}
        di_path = os.path.join(run_dir, index.get("dataset_intelligence", "dataset_intelligence.json"))
        dataset_intelligence = _load(di_path) if os.path.exists(di_path) else {}
        manifest_path = os.path.join(run_dir, "_manifest.json")
        manifest = _load(manifest_path) if os.path.exists(manifest_path) else {}
        return cls(run_dir=run_dir, index=index, outputs=outputs, reports=reports,
                   registries=registries, dataset_intelligence=dataset_intelligence, manifest=manifest)

    # ---- current_* accessors (the directive's application state) -------------
    def current_inference(self) -> dict:
        return {
            "inference_id": self.index["inference_id"],
            "lineage_id": self.index["lineage_id"],
            "status": self.outputs.get("summary", {}).get("model_name") and "completed",
            "validation_ok": self.index["validation"]["ok"],
            "version_bundle": self.index["version_bundle"],
        }

    def current_dataset(self) -> dict:
        return self.dataset_intelligence.get("profile", {})

    def current_model(self) -> dict:
        vb = self.index["version_bundle"]
        return {
            "model_name": self.outputs.get("summary", {}).get("model_name"),
            "model_version": vb.get("model_version"),
            "architecture_version": vb.get("architecture_version"),
            "training_version": vb.get("training_version"),
        }

    def current_benchmark(self) -> dict:
        return self.registries.get("benchmark_registry", {})

    def current_reports(self) -> list:
        return sorted(self.reports.keys())

    def current_artifacts(self) -> dict:
        return self.manifest.get("artifacts", {})

    def audit_trail(self) -> dict:
        return {
            "lineage": self.registries.get("lineage", {}),
            "audit_report": self.reports.get("audit_report", {}),
            "inference_registry": self.registries.get("inference_registry", {}),
        }
