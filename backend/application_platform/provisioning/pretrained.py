"""`backend/application_platform/provisioning/pretrained.py` — Pretrained artifact loader for CHB-MIT model.

This provides a drop-in alternate backend for `CHBMitInferenceEngine` (the real Phase-9
trained artifact) that satisfies the downstream interface expectations without going
through the deterministic reconstruction path in ModelExecutionEngine.

It produces a ModelContext-compatible wrapper and exposes predict_proba directly
fed by the training-time `_window_features` (not FeatureEngineeringService).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional, Any

import numpy as np

from backend.real_model_training.data import _window_features, FEATURE_NAMES
from backend.application_platform.chbmit_inference import CHBMitInferenceEngine

from backend.application_backend.workflows.eeg_workflow import ModelContext

# Default artifact path (relative to repo root when run from scripts)
DEFAULT_CHBMIT_ARTIFACT = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "data", "chbmit_model.json"
)
# Also support root-level
ALT_CHBMIT_ARTIFACT = "data/chbmit_model.json"


@dataclass
class PretrainedModelRecord:
    """Minimal ModelRecord-like object for pretrained artifact.
    
    Populated with sensible synthetic-but-clear identifiers so that
    downstream ModelRecord consumers (reports, registry, audit) do not break
    and can be clearly distinguished from synthetic-bootstrap models.
    """
    model_id: str
    architecture: str = "chbmit-pretrained-phase9"
    dataset_id: str = "chbmit-phase9-pretrained"
    training_run_id: str = ""
    evaluation_id: str = ""
    metadata: dict = field(default_factory=dict)
    params_fingerprint: str = ""
    status: str = "ready"
    version: str = "phase9-pretrained"
    n_classes: int = 2
    n_features: int = len(FEATURE_NAMES)
    class_labels: tuple = (0, 1)

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "architecture": self.architecture,
            "dataset_id": self.dataset_id,
            "training_run_id": self.training_run_id,
            "evaluation_id": self.evaluation_id,
            "metadata": self.metadata,
            "params_fingerprint": self.params_fingerprint,
            "status": self.status,
            "version": self.version,
            "n_classes": self.n_classes,
            "n_features": self.n_features,
            "class_labels": self.class_labels,
        }


@dataclass
class PretrainedModelContext:
    """Drop-in replacement for ModelContext that carries the pretrained engine.
    
    - Does NOT contain train_feature_records that would be used for reconstruction.
    - Exposes direct `predict_proba(row)` that is backed by CHBMitInferenceEngine.
    - The downstream workflow will branch to use the artifact's predict path.
    """
    model_record: PretrainedModelRecord
    engine: CHBMitInferenceEngine
    dataset_key: str = "chbmit-phase9-pretrained"
    label_fn: Optional[Any] = None
    is_pretrained: bool = True
    # For compatibility: empty tuple so nothing tries to reconstruct
    train_feature_records: tuple = ()

    @property
    def model_id(self) -> str:
        return self.model_record.model_id

    def predict_proba(self, row: np.ndarray) -> np.ndarray:
        """Exactly the surface called by ModelExecutionEngine.execute in the normal path.
        
        row: (n_features,) or (1, n_features)
        """
        row = np.asarray(row, dtype=np.float64)
        if row.ndim == 1:
            row = row.reshape(1, -1)
        proba = self.engine.predict_proba(row)
        if isinstance(proba, np.ndarray) and proba.ndim == 2:
            proba = proba[0]
        return np.asarray(proba, dtype=np.float64)

    def predict_raw_window(self, window: np.ndarray, sfreq: float) -> tuple[int, np.ndarray]:
        """Convenience: direct raw window inference (uses training-time feature fn)."""
        return self.engine.predict_raw_window(window, sfreq)


def load_chbmit_pretrained(artifact_path: Optional[str] = None) -> PretrainedModelContext:
    """Load the CHB-MIT pretrained artifact and return a ModelContext-compatible wrapper.

    This is the integration point mandated by the root-cause fix.
    """
    if artifact_path is None:
        # Try multiple common locations
        candidates = [
            DEFAULT_CHBMIT_ARTIFACT,
            os.path.abspath(ALT_CHBMIT_ARTIFACT),
            os.path.abspath(os.path.join("data", "chbmit_model.json")),
            "/home/user/neurovision_ai/data/chbmit_model.json",
        ]
        artifact_path = None
        for cand in candidates:
            if os.path.exists(cand):
                artifact_path = cand
                break
        if artifact_path is None:
            artifact_path = DEFAULT_CHBMIT_ARTIFACT  # will raise inside engine

    engine = CHBMitInferenceEngine(artifact_path)

    # Create a stable model_id from the artifact file hash (content-addressed)
    import hashlib
    with open(artifact_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()[:16]
    model_id = f"chbmit-pretrained-{file_hash}"

    # Populate metadata from the artifact metrics for reporting
    metrics = engine.metrics or {}
    metadata = {
        "source": "chbmit_phase9_pretrained_artifact",
        "artifact_path": os.path.abspath(artifact_path),
        "accuracy": metrics.get("accuracy"),
        "f1_macro": metrics.get("f1_macro"),
        "sensitivity": metrics.get("sensitivity"),
        "specificity": metrics.get("specificity"),
        "roc_auc": metrics.get("roc_auc_macro"),
        "architecture_summary": engine.architecture_summary,
        "n_features": len(FEATURE_NAMES),
        "feature_names": list(FEATURE_NAMES),
    }

    record = PretrainedModelRecord(
        model_id=model_id,
        architecture="chbmit-pretrained-phase9",
        dataset_id="chbmit-phase9-pretrained",
        training_run_id=f"pretrained-{file_hash}",
        evaluation_id=f"phase9-eval-{file_hash}",
        metadata=metadata,
        params_fingerprint=f"pretrained:{file_hash}",
        status="ready",
        version="phase9-pretrained",
        n_classes=2,
        n_features=len(FEATURE_NAMES),
        class_labels=(0, 1),
    )

    ctx = PretrainedModelContext(
        model_record=record,
        engine=engine,
        dataset_key="chbmit-phase9-pretrained",
        label_fn=None,
        is_pretrained=True,
    )
    return ctx


def is_pretrained_context(ctx: Any) -> bool:
    """Utility: detect if a ModelContext (or PretrainedModelContext) is the pretrained artifact."""
    if ctx is None:
        return False
    if hasattr(ctx, "is_pretrained") and getattr(ctx, "is_pretrained", False):
        return True
    mr = getattr(ctx, "model_record", None)
    if mr is not None:
        arch = getattr(mr, "architecture", "") or ""
        if "chbmit-pretrained" in str(arch).lower() or "chbmit" in str(arch).lower():
            return True
        if hasattr(mr, "dataset_id") and "chbmit-phase9" in str(getattr(mr, "dataset_id", "")):
            return True
    # Fallback check on model_id
    mid = getattr(ctx, "model_id", "") or getattr(getattr(ctx, "model_record", None), "model_id", "")
    if isinstance(mid, str) and "chbmit-pretrained" in mid:
        return True
    return False


__all__ = [
    "PretrainedModelRecord",
    "PretrainedModelContext",
    "load_chbmit_pretrained",
    "is_pretrained_context",
    "FEATURE_NAMES",
]
