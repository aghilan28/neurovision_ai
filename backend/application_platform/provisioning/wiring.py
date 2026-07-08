"""Wiring helpers for pretrained model integration.

These allow the existing workflow/inference paths to branch correctly
when a pretrained artifact is in use.

CRITICAL: For pretrained models we bypass:
- FeatureEngineeringService (different feature space)
- ModelExecutionEngine reconstruction

Instead we use:
  SignalProcessingService -> raw window -> _window_features (training-time fn)
  -> CHBMitInferenceEngine.predict_proba
"""

from __future__ import annotations

import numpy as np
from typing import Any, Optional, Tuple

from backend.real_model_training.data import _window_features, FEATURE_NAMES
from .pretrained import is_pretrained_context, PretrainedModelContext


def get_window_features_from_processed(
    processed_asset: Any,
    window_seconds: float = 4.0,
    sfreq_fallback: float = 256.0,
) -> Tuple[np.ndarray, float]:
    """Extract a representative window from processed signal and compute training-time features.

    Returns (feature_row, sfreq)
    This is the EXACT path used at training time for the CHB-MIT artifact.
    """
    import numpy as np

    # processed_asset expected to have .data or similar; adapt to platform conventions
    data = None
    sfreq = sfreq_fallback

    # Common shapes in this codebase:
    # - asset.data : np.ndarray (channels, samples)
    # - asset.signal or asset.processed_signal
    # - asset.metadata.sampling_frequency

    if hasattr(processed_asset, "data") and processed_asset.data is not None:
        data = np.asarray(processed_asset.data, dtype=np.float64)
    elif hasattr(processed_asset, "signal") and processed_asset.signal is not None:
        data = np.asarray(processed_asset.signal, dtype=np.float64)
    elif hasattr(processed_asset, "processed_signal"):
        data = np.asarray(processed_asset.processed_signal, dtype=np.float64)
    else:
        # Try to find array attribute
        for attr in ("array", "values", "eeg", "raw"):
            if hasattr(processed_asset, attr):
                candidate = getattr(processed_asset, attr)
                if isinstance(candidate, np.ndarray):
                    data = candidate.astype(np.float64)
                    break

    if data is None or data.size == 0:
        raise ValueError("Could not extract numeric data from processed asset")

    # Sampling frequency
    if hasattr(processed_asset, "metadata") and hasattr(processed_asset.metadata, "sampling_frequency"):
        sfreq = float(processed_asset.metadata.sampling_frequency) or sfreq
    elif hasattr(processed_asset, "sampling_frequency"):
        sfreq = float(processed_asset.sampling_frequency) or sfreq
    elif hasattr(processed_asset, "sfreq"):
        sfreq = float(processed_asset.sfreq) or sfreq

    # Pick a central window (4s)
    n_samples = data.shape[1] if data.ndim == 2 else len(data)
    win_len = int(round(window_seconds * sfreq))
    if win_len > n_samples:
        win_len = n_samples

    start = max(0, (n_samples - win_len) // 2)
    if data.ndim == 2:
        window = data[:, start : start + win_len]
    else:
        window = data[start : start + win_len].reshape(1, -1)

    # Compute EXACT training-time features
    feats = _window_features(window, sfreq)
    return np.asarray(feats, dtype=np.float64), float(sfreq)


def predict_with_pretrained(
    model_context: Any,
    processed_asset: Any,
    *,
    window_seconds: float = 4.0,
) -> dict:
    """Run inference using pretrained CHBMIT artifact + training-time features.

    Returns a dict mimicking a minimal prediction result:
    {
      "predicted_class": int,
      "predicted_label": str,
      "probabilities": list[float],
      "confidence": float,
      "source": "chbmit_pretrained"
    }
    """
    if not is_pretrained_context(model_context):
        raise ValueError("predict_with_pretrained called on non-pretrained context")

    ctx: PretrainedModelContext = model_context  # type: ignore

    row, sfreq = get_window_features_from_processed(
        processed_asset, window_seconds=window_seconds
    )

    # Must be exactly the same shape the model was trained on
    expected = ctx.model_record.n_features
    if row.shape[0] != expected:
        # This would indicate a feature mismatch (Bug 2) — do not silently pad
        raise ValueError(
            f"Feature dimension mismatch: got {row.shape[0]}, expected {expected}. "
            "This means the wiring did not use _window_features correctly."
        )

    proba = ctx.predict_proba(row)
    proba = np.asarray(proba, dtype=np.float64).ravel()

    if abs(float(proba.sum()) - 1.0) > 1e-5:
        # renormalize as safety (should not happen)
        proba = proba / proba.sum()

    pred_class = int(np.argmax(proba))
    labels = ["background", "seizure"]
    label = labels[pred_class] if pred_class < len(labels) else str(pred_class)

    return {
        "predicted_class": pred_class,
        "predicted_label": label,
        "probabilities": proba.tolist(),
        "confidence": float(proba[pred_class]),
        "source": "chbmit_pretrained_phase9",
        "sfreq": sfreq,
        "n_features": int(row.shape[0]),
    }


def make_prediction_record_from_pretrained_result(result: dict, model_id: str) -> dict:
    """Turn the raw result into a shape compatible with existing PredictionRecord expectations."""
    return {
        "predicted_class": result["predicted_class"],
        "predicted_label": result["predicted_label"],
        "probabilities": result["probabilities"],
        "confidence": result["confidence"],
        "model_id": model_id,
        "source": result.get("source", "chbmit_pretrained"),
    }


__all__ = [
    "get_window_features_from_processed",
    "predict_with_pretrained",
    "make_prediction_record_from_pretrained_result",
    "is_pretrained_context",
]
