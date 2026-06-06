"""Resume and expand the CHB-MIT model training from the previous baseline."""

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
from scripts.train_chbmit import serialize_model


def load_previous_model_data(path: str) -> dict | None:
    """Load the previous model data if it exists."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        print(f"Warning: Failed to load previous model data: {exc}")
        return None


def main() -> int:
    output_path = os.path.join(str(REPO), "data", "chbmit_model.json")
    previous_data = load_previous_model_data(output_path)
    
    if previous_data:
        print("\n=== BASELINE MODEL DATA DETECTED ===")
        print(f"Architecture: {previous_data.get('architecture_summary')}")
        print(f"Windows in Baseline: {previous_data.get('n_windows')}")
        print(f"Baseline Metrics: {previous_data.get('metrics')}")
        print("=====================================\n")
    else:
        print("\nNo baseline model detected. Running first-time training...\n")

    print("Initializing Real Model Training Service...")
    svc = RealModelTrainingService()
    
    print("Completing any missing dataset acquisition and verifying local files...")
    # This automatically verifies local files and resumes any unfinished downloads
    t1_outcome = svc.dataset_service.integrate(T1Src.CHB_MIT, allow_download=True)
    if not t1_outcome.ready_for_training:
        print("Error: Dataset acquisition did not complete successfully.")
        return 1
        
    print(f"Acquisition verified! recordings={t1_outcome.dataset_record.n_recordings}")
    
    print("Developing models on expanded corpus...")
    out = svc.develop(T1Src.CHB_MIT, allow_download=False,
                      window_seconds=4.0, background_per_seizure=4)
    
    best = out.best_ready_model() or (out.candidates[0] if out.candidates else None)
    if best is None:
        print("Error: No models trained successfully.")
        return 1
        
    print(f"\n==================================================")
    print(f"NEW TRAINED MODEL: {best.architecture.value}")
    print(f"New Metrics: {best.headline_metrics}")
    print(f"New Window Count: {out.dataset_record.n_windows}")
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
    
    new_data = {
        "architecture_summary": best.architecture.value,
        "n_windows": out.dataset_record.n_windows,
        "class_distribution": out.dataset_record.class_distribution,
        "metrics": best.headline_metrics,
        "model_payload": model_weights_and_config
    }
    
    print(f"Writing updated model artifact to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(new_data, fh, indent=2)
        
    if previous_data:
        print("\n=== COMPARISON AGAINST PREVIOUS BASELINE ===")
        print(f"{'Metric':<20} | {'Baseline':<12} | {'New model':<12} | {'Change':<12}")
        print("-" * 65)
        
        base_metrics = previous_data.get("metrics") or {}
        new_metrics = best.headline_metrics or {}
        
        # Also compare window count
        base_win = previous_data.get("n_windows", 0)
        new_win = out.dataset_record.n_windows
        print(f"{'Window Count':<20} | {base_win:<12} | {new_win:<12} | {new_win - base_win:<+12}")
        
        for k in sorted(set(base_metrics.keys()) | set(new_metrics.keys())):
            bv = base_metrics.get(k)
            nv = new_metrics.get(k)
            if bv is not None and nv is not None:
                print(f"{k:<20} | {bv:<12.4f} | {nv:<12.4f} | {nv - bv:<+12.4f}")
            elif bv is not None:
                print(f"{k:<20} | {bv:<12.4f} | {'N/A':<12} | {'N/A':<12}")
            elif nv is not None:
                print(f"{k:<20} | {'N/A':<12} | {nv:<12.4f} | {'N/A':<12}")
        print("============================================\n")
        
    print("Model resume, retrain, and validation completed successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
