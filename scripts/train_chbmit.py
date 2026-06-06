"""Train the CHB-MIT model on the local corpus and save to data/chbmit_model.json."""

from __future__ import annotations

import os
import sys
import json
import pathlib
import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from backend.dataset_acquisition import DatasetSource as T1Src
from backend.real_model_training import RealModelTrainingService
from backend.real_model_training.training import train_architecture


def serialize_model(model) -> dict:
    """Convert any production model wrapper (Reference or Hybrid) to a JSON serializable dict."""
    if hasattr(model, "_inner"):
        # ReferenceArchitectureWrapper
        inner_model = model._inner
        weights = inner_model.get_weights()
        weights_serialized = {k: v.tolist() for k, v in weights.items()}
        return {
            "type": "reference_wrapper",
            "architecture": model.architecture.value,
            "seed": model.seed,
            "n_classes": model.n_classes,
            "hyperparameters": model.hyperparameters,
            "weights": weights_serialized
        }
    else:
        # HybridModel
        weights = {
            "mean": model._mean,
            "std": model._std,
            "proj_a": model._proj_a,
            "proj_b": model._proj_b,
            "W": model._W,
            "b": model._b
        }
        weights_serialized = {k: v.tolist() for k, v in weights.items()}
        return {
            "type": "hybrid",
            "architecture": model.architecture.value,
            "seed": model.seed,
            "n_classes": model.n_classes,
            "hyperparameters": model.hyperparameters,
            "weights": weights_serialized
        }


def main() -> int:
    print("Initializing Real Model Training Service...")
    svc = RealModelTrainingService()
    
    print("Developing models on expanded real CHB-MIT corpus...")
    # This will train all 5 architectures on the local real data
    out = svc.develop(T1Src.CHB_MIT, allow_download=False,
                      window_seconds=4.0, background_per_seizure=4)
    
    best = out.best_ready_model() or (out.candidates[0] if out.candidates else None)
    if best is None:
        print("Error: No models trained successfully.")
        return 1
        
    print(f"\n==================================================")
    print(f"BEST CANDIDATE MODEL: {best.architecture.value}")
    print(f"Metrics: {best.headline_metrics}")
    print(f"==================================================\n")
    
    # Run a dedicated final training of the best model to capture its state
    print("Preparing training bundle...")
    prepared = svc.prepare(T1Src.CHB_MIT, allow_download=False,
                           window_seconds=4.0, background_per_seizure=4)
    
    print(f"Running final training for {best.architecture.value}...")
    to = train_architecture(prepared.bundle, best.architecture)
    model = to.model
    
    print("Serializing trained model parameters...")
    model_weights_and_config = serialize_model(model)
    
    model_data = {
        "architecture_summary": best.architecture.value,
        "n_windows": out.dataset_record.n_windows,
        "class_distribution": out.dataset_record.class_distribution,
        "metrics": best.headline_metrics,
        "model_payload": model_weights_and_config
    }
    
    output_path = os.path.join(str(REPO), "data", "chbmit_model.json")
    print(f"Writing model artifact to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(model_data, fh, indent=2)
        
    print("Model training and serialization completed successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
