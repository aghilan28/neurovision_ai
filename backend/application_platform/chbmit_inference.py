"""CHB-MIT pre-trained model inference.

Loads the pre-built CHB-MIT model (trained on real PhysioNet seizure data)
and runs inference on uploaded EEG files. The model was trained on 10-second
windows from CHB-MIT chb01 with 28 spectral features.

This module provides a standalone inference function that can be called
alongside the existing provisioning model to provide a second opinion
from a clinically-trained model.
"""

from __future__ import annotations

import json
import os
from typing import Optional

import numpy as np

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chbmit_model.json")
_MODEL_CACHE: Optional[dict] = None


def _load_model() -> dict:
    """Load the pre-trained CHB-MIT model from disk (cached)."""
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    # Try multiple paths
    paths = [
        _MODEL_PATH,
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "chbmit_model.json"),
        "/app/data/chbmit_model.json",
        "data/chbmit_model.json",
    ]

    for path in paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            with open(abs_path) as f:
                _MODEL_CACHE = json.load(f)
            return _MODEL_CACHE

    return None


def chbmit_available() -> bool:
    """Check if the CHB-MIT model is available."""
    return _load_model() is not None


def compute_eeg_features(data: np.ndarray, sfreq: float) -> Optional[dict]:
    """Compute the 28 spectral features from an EEG segment.

    ``data`` is (n_channels, n_samples). Returns a feature dict matching
    the CHB-MIT model's feature names, or None if computation fails.
    """
    from scipy.signal import welch

    n_channels, n_samples = data.shape
    if n_samples < int(sfreq * 2):
        return None

    bands = {
        "delta": (0.5, 4), "theta": (4, 8), "alpha": (8, 13),
        "beta": (13, 30), "gamma": (30, 45),
    }

    ch_band_powers = {b: [] for b in bands}
    ch_entropy, ch_rms, ch_line_length = [], [], []

    for ch in range(min(n_channels, 23)):
        x = data[ch]
        if np.std(x) < 1e-10:
            continue

        nperseg = min(len(x), int(sfreq * 2))
        try:
            freqs, psd = welch(x, fs=sfreq, nperseg=nperseg)
        except Exception:
            continue

        for band_name, (lo, hi) in bands.items():
            mask = (freqs >= lo) & (freqs < hi)
            bp = float(np.trapz(psd[mask], freqs[mask])) if mask.any() else 0.0
            ch_band_powers[band_name].append(bp)

        psd_pos = psd[psd > 0]
        if len(psd_pos) > 1:
            pn = psd_pos / psd_pos.sum()
            entropy = float(-np.sum(pn * np.log(pn + 1e-12)) / np.log(len(pn)))
        else:
            entropy = 0.0
        ch_entropy.append(entropy)
        ch_rms.append(float(np.sqrt(np.mean(x ** 2))))
        ch_line_length.append(float(np.sum(np.abs(np.diff(x))) / len(x)))

    if not ch_entropy:
        return None

    features = {}
    for band_name in bands:
        vals = ch_band_powers[band_name]
        features[f"{band_name}_mean"] = float(np.mean(vals)) if vals else 0.0
        features[f"{band_name}_std"] = float(np.std(vals)) if vals else 0.0
        features[f"{band_name}_max"] = float(np.max(vals)) if vals else 0.0

    features["entropy_mean"] = float(np.mean(ch_entropy))
    features["entropy_std"] = float(np.std(ch_entropy))
    features["rms_mean"] = float(np.mean(ch_rms))
    features["rms_std"] = float(np.std(ch_rms))
    features["line_length_mean"] = float(np.mean(ch_line_length))
    features["line_length_std"] = float(np.std(ch_line_length))

    total = sum(features[f"{b}_mean"] for b in bands)
    for b in bands:
        features[f"{b}_ratio"] = features[f"{b}_mean"] / (total + 1e-12)

    features["delta_alpha_ratio"] = features["delta_mean"] / (features["alpha_mean"] + 1e-12)
    features["theta_beta_ratio"] = features["theta_mean"] / (features["beta_mean"] + 1e-12)

    return features


def predict_seizure(data: np.ndarray, sfreq: float) -> Optional[dict]:
    """Run CHB-MIT model inference on EEG data.

    ``data`` is (n_channels, n_samples). Returns a dict with seizure probability,
    risk level, and feature contributions, or None if inference fails.
    """
    model = _load_model()
    if model is None:
        return None

    features = compute_eeg_features(data, sfreq)
    if features is None:
        return None

    # Build feature vector in the correct order
    feature_names = model["feature_names"]
    row = np.array([features.get(fn, 0.0) for fn in feature_names], dtype=np.float64)

    # Normalize
    mean = np.array(model["mean"], dtype=np.float64)
    std = np.array(model["std"], dtype=np.float64)
    row_norm = np.nan_to_num((row - mean) / std, nan=0.0, posinf=0.0, neginf=0.0)

    # Predict
    W = np.array(model["W"], dtype=np.float64)
    b = np.array(model["b"], dtype=np.float64)

    z = row_norm @ W + b
    z = z - z.max()
    probs = np.exp(z) / (np.exp(z).sum() + 1e-12)

    seizure_prob = float(probs[1])
    non_seizure_prob = float(probs[0])

    # Feature contributions (simple weight-based)
    contributions = []
    weighted = row_norm * W[:, 1]  # contribution to seizure class
    top_indices = np.argsort(np.abs(weighted))[::-1][:5]
    for idx in top_indices:
        contrib = float(weighted[idx])
        contributions.append({
            "feature": feature_names[idx],
            "contribution": round(abs(contrib), 4),
            "direction": "supports_seizure" if contrib > 0 else "supports_normal",
            "raw_value": round(float(row[idx]), 6),
        })

    return {
        "seizure_probability": round(seizure_prob, 4),
        "non_seizure_probability": round(non_seizure_prob, 4),
        "model_source": model.get("source", "CHB-MIT"),
        "model_version": model.get("version", "unknown"),
        "model_accuracy": model.get("accuracy", 0),
        "model_sensitivity": model.get("sensitivity", 0),
        "model_specificity": model.get("specificity", 0),
        "n_training_windows": model.get("n_train", 0),
        "feature_contributions": contributions,
        "features_computed": len(feature_names),
    }


__all__ = ["chbmit_available", "predict_seizure", "compute_eeg_features"]
