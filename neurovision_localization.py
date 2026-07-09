#!/usr/bin/env python3
"""
================================================================================
neurovision_localization.py
NeuroVision AI :: Model-Driven Spatial Localization via Channel Ablation
================================================================================

Provides TRUE model-driven brain localization by running the trained Phase 5B
XGBoost model (PHASE5B_TEMPORAL_XGBOOST.joblib) and measuring each 10-20
channel's causal influence on the seizure prediction through leave-one-out
channel ablation.

Why ablation (and not SHAP / feature_importances_)?
  The model's 484 features are CROSS-CHANNEL AGGREGATES
  (e.g. ``mean_mean`` = mean across channels of the per-window mean;
  ``variance_std`` = std across channels of variance; ``delta_power_mean`` =
  mean across channels of delta power). Channel identity is averaged away
  BEFORE the model sees any feature, so there is no per-channel feature block
  to attribute. The only correct model-driven method is therefore to perturb
  the raw signal at the channel level (zero one channel), re-extract the exact
  484-feature contract, re-predict, and measure the seizure-probability drop.

Efficiency:
  Because the 96 base features aggregate across channels, per-channel feature
  vectors are computed ONCE; each ablation pass only re-aggregates the remaining
  18 channels (no re-computation of entropy / wavelet / spectral features), so
  the full 19-channel ablation runs in milliseconds-to-low-seconds.

The feature extractor reproduces the EXACT Phase 5B training contract:
  - 32 per-channel base statistics x {mean,std,max} = 96 base features
    (source: scripts_v4_new/build_shard_dataset_v4.py)
  - temporal variants: _lag1, _lag3, _rolling_mean_5, _stability_5
    (source: scripts/train_phase5b_temporal_xgboost_v2.py)
  - 4 positional features (relative_position_in_edf, normalized_window_index,
    elapsed_time_fraction, remaining_time_fraction)
  Window = 4.0 s, stride = 2.0 s (matches v4 production builder).
================================================================================
"""

from __future__ import annotations

import logging
import math
import os
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

log = logging.getLogger("neurovision_localization")

# ----------------------------------------------------------------------------- 
# Constants — MUST match the Phase 5B training pipeline exactly
# -----------------------------------------------------------------------------
WINDOW_LENGTH_SEC: float = 4.0
STRIDE_SEC: float = 2.0
FREQ_BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 45.0),
}
WAVELET_NAME = "db4"
WAVELET_LEVEL = 5
MIN_WAVELET_SAMPLES = 2 ** WAVELET_LEVEL

# 32 base per-channel statistics, in the EXACT training order.
BASE_FEATURES: List[str] = [
    "mean", "std", "variance", "rms", "max", "min", "ptp",
    "line_length", "zero_crossings", "iqr", "mad",
    "sample_entropy", "perm_entropy", "spectral_entropy",
    "higuchi_fd", "petrosian_fd",
    "wavelet_energy_0", "wavelet_energy_1", "wavelet_energy_2",
    "wavelet_energy_3", "wavelet_energy_4", "wavelet_energy_5",
    "delta_power", "theta_power", "alpha_power", "beta_power", "gamma_power",
    "delta_relative", "theta_relative", "alpha_relative", "beta_relative", "gamma_relative",
]
AGGREGATIONS = ["mean", "std", "max"]
# Canonical 96 base feature names (BASE x AGG), matches PHASE5B_FEATURE_SIGNATURE.json[0:96]
BASE_96: List[str] = [f"{b}_{a}" for b in BASE_FEATURES for a in AGGREGATIONS]

# 10-20 system + the definitive spatial lookup contract (matches neurovision_api.py)
EEG_CHANNELS: List[str] = [
    "Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2",
    "F7", "F8", "T3", "T4", "T5", "T6", "Fz", "Cz", "Pz",
]
LEAD_TO_ZONE_MAP = {
    "Fp1": "FRONTAL", "Fp2": "FRONTAL", "F3": "FRONTAL", "F4": "FRONTAL", "Fz": "FRONTAL",
    "F7": "L-TEMPORAL", "T3": "L-TEMPORAL", "T5": "L-TEMPORAL",
    "F8": "R-TEMPORAL", "T4": "R-TEMPORAL", "T6": "R-TEMPORAL",
    "C3": "CENTRAL", "C4": "CENTRAL", "Cz": "CENTRAL",
    "P3": "PARIETAL", "P4": "PARIETAL", "Pz": "PARIETAL",
    "O1": "PARIETAL", "O2": "PARIETAL", "Oz": "PARIETAL",
}

# Lazily-imported heavy dependencies (kept optional so the module imports even
# if antropy/pywt/scipy are absent — the caller then falls back gracefully).
_ant = None
_pywt = None
_welch = None
_trapezoid = None
_xgb_model = None
_model_loaded = False
_model_load_attempted = False
_MODEL_PATH = os.environ.get("NEUROVISION_XGB_PATH", "PHASE5B_TEMPORAL_XGBOOST.joblib")


def _ensure_feature_deps() -> bool:
    """Lazy-import the entropy / wavelet / spectral dependencies."""
    global _ant, _pywt, _welch, _trapezoid
    if _ant is not None:
        return True
    try:
        import antropy as ant
        import pywt
        from scipy.signal import welch
        from scipy.integrate import trapezoid
        _ant, _pywt, _welch, _trapezoid = ant, pywt, welch, trapezoid
        return True
    except Exception as e:
        log.warning("neurovision_localization: feature deps unavailable (%s); "
                    "model-driven localization disabled.", e)
        return False


def _load_model():
    """Load the Phase 5B XGBoost model exactly once (cached at module level)."""
    global _xgb_model, _model_loaded, _model_load_attempted
    if _model_loaded:
        return _xgb_model
    if _model_load_attempted:
        return _xgb_model
    _model_load_attempted = True
    try:
        import joblib
        if not os.path.exists(_MODEL_PATH):
            log.warning("neurovision_localization: model artifact '%s' not found.", _MODEL_PATH)
            return None
        _xgb_model = joblib.load(_MODEL_PATH)
        n = getattr(_xgb_model, "n_features_in_", None)
        if n is not None and int(n) != 484:
            log.warning("neurovision_localization: model expects %d features, expected 484.", n)
        log.info("neurovision_localization: Phase 5B XGBoost model loaded (%d features).",
                 n or 484)
        _model_loaded = True
        return _xgb_model
    except Exception as e:
        log.warning("neurovision_localization: could not load XGBoost model (%s).", e)
        return None


# =============================================================================
# Per-channel feature extraction (faithful to build_shard_dataset_v4.py)
# =============================================================================

def _compute_time_features(signal: np.ndarray) -> Dict[str, float]:
    s32 = signal.astype(np.float32)
    mean_val = float(np.mean(s32))
    std_val = float(np.std(s32))
    s64 = s32.astype(np.float64)
    pct = np.percentile(s64, [25, 75])
    return {
        "mean": mean_val,
        "std": std_val,
        "variance": float(std_val ** 2),
        "rms": float(np.sqrt(np.mean(s32 ** 2))),
        "max": float(np.max(s32)),
        "min": float(np.min(s32)),
        "ptp": float(np.ptp(s32)),
        "line_length": float(np.sum(np.abs(np.diff(s32)))),
        "zero_crossings": float(np.sum(np.diff(np.signbit(s32)) != 0)),
        "iqr": float(pct[1] - pct[0]),
        "mad": float(np.median(np.abs(s64 - np.median(s64)))),
    }


def _safe(func, data, *args, **kwargs) -> float:
    try:
        r = func(data, *args, **kwargs)
        if r is None or (isinstance(r, float) and (math.isnan(r) or math.isinf(r))):
            return 0.0
        return float(r)
    except Exception:
        return 0.0


def _compute_entropy_features(signal: np.ndarray, sfreq: float) -> Dict[str, float]:
    s64 = signal.astype(np.float64)
    return {
        "sample_entropy": _safe(_ant.sample_entropy, s64),
        "perm_entropy": _safe(_ant.perm_entropy, s64, order=3, delay=1),
        "spectral_entropy": _safe(_ant.spectral_entropy, s64, sfreq, method="welch", normalize=True),
    }


def _compute_fractal_features(signal: np.ndarray) -> Dict[str, float]:
    s64 = signal.astype(np.float64)
    return {
        "higuchi_fd": _safe(_ant.higuchi_fd, s64),
        "petrosian_fd": _safe(_ant.petrosian_fd, s64),
    }


def _compute_wavelet_features(signal: np.ndarray) -> Dict[str, float]:
    feats: Dict[str, float] = {}
    n = len(signal)
    max_level = int(np.log2(n)) - 1 if n > 4 else 1
    actual_level = min(WAVELET_LEVEL, max_level)
    if actual_level < 1 or n < MIN_WAVELET_SAMPLES:
        for i in range(WAVELET_LEVEL + 1):
            feats[f"wavelet_energy_{i}"] = 0.0
        return feats
    try:
        coeffs = _pywt.wavedec(signal, WAVELET_NAME, level=actual_level)
        for i, coeff in enumerate(coeffs):
            energy = float(np.sum(np.asarray(coeff) ** 2))
            feats[f"wavelet_energy_{i}"] = 0.0 if math.isnan(energy) else energy
        for i in range(actual_level + 1, WAVELET_LEVEL + 1):
            feats[f"wavelet_energy_{i}"] = 0.0
    except Exception:
        for i in range(WAVELET_LEVEL + 1):
            feats[f"wavelet_energy_{i}"] = 0.0
    return feats


def _compute_spectral_features(signal: np.ndarray, sfreq: float) -> Dict[str, float]:
    s32 = signal.astype(np.float32)
    n = len(s32)
    window = np.hanning(n)
    sw = s32 * window
    nperseg = min(256, n // 2)
    if nperseg < 4:
        nperseg = n
    freqs, psd = _welch(sw, fs=sfreq, nperseg=nperseg, noverlap=None)
    feats: Dict[str, float] = {}
    band_powers: Dict[str, float] = {}
    total_power = 1e-12
    for band_name, (low, high) in FREQ_BANDS.items():
        mask = (freqs >= low) & (freqs < high)
        bp = float(_trapezoid(psd[mask], freqs[mask])) if np.any(mask) else 0.0
        band_powers[band_name] = bp
        feats[f"{band_name}_power"] = float(np.log1p(bp))
        total_power += bp
    for band_name in FREQ_BANDS:
        power = band_powers[band_name]
        feats[f"{band_name}_relative"] = float(np.clip(power / total_power, 0.0, 1.0)) if total_power > 1e-10 else 0.0
    return feats


def _extract_channel_features(signal: np.ndarray, sfreq: float) -> Dict[str, float]:
    """All 32 base statistics for one channel (faithful to v4 extractor)."""
    feats: Dict[str, float] = {}
    feats.update(_compute_time_features(signal))
    s64 = signal.astype(np.float64)
    feats.update(_compute_entropy_features(s64, sfreq))
    feats.update(_compute_fractal_features(s64))
    feats.update(_compute_wavelet_features(s64))
    feats.update(_compute_spectral_features(s64, sfreq))
    for b in BASE_FEATURES:
        feats.setdefault(b, 0.0)
    return feats


def _aggregate(channel_feats: List[Dict[str, float]]) -> List[float]:
    """Aggregate per-channel dicts into the 96 canonical base features (mean/std/max)."""
    out = []
    for bname in BASE_FEATURES:
        vals = [cf[bname] for cf in channel_feats if bname in cf]
        if vals:
            out.append(float(np.mean(vals)))
            out.append(float(np.std(vals)))
            out.append(float(np.max(vals)))
        else:
            out.extend([0.0, 0.0, 0.0])
    return out  # len 96, order == BASE_96


# =============================================================================
# Temporal feature engineering (faithful to train_phase5b_temporal_xgboost_v2.py)
# =============================================================================

def _build_temporal_matrix(base_windows: List[List[float]]) -> np.ndarray:
    """
    Given a sequence of 96-dim base windows (chronological), build the full
    484-dim feature matrix (n_windows x 484) matching the Phase 5B contract:
      [0:96]   base
      [96:192] _lag1   = shift(1)
      [192:288] _lag3  = shift(3)
      [288:384] _rolling_mean_5 = rolling(5, min_periods=1).mean()
      [384:480] _stability_5 = abs(base - rolling_mean_5)
      [480:484] positional
    """
    arr = np.asarray(base_windows, dtype=np.float64)  # (W, 96)
    W = arr.shape[0]
    out = np.zeros((W, 484), dtype=np.float64)

    # base
    out[:, 0:96] = arr
    # lag1
    if W > 1:
        out[1:, 96:192] = arr[:-1]
    # lag3
    if W > 3:
        out[3:, 192:288] = arr[:-3]
    # rolling_mean_5 (min_periods=1) + stability_5
    for w in range(W):
        lo = max(0, w - 4)
        win = arr[lo:w + 1]            # up to 5 rows, current inclusive
        rmean = win.mean(axis=0)
        out[w, 288:384] = rmean
        out[w, 384:480] = np.abs(arr[w] - rmean)
    # positional
    if W > 1:
        rel_pos = np.array([w / W for w in range(W)])
        nwi = np.array([w / (W - 1) for w in range(W)])
        etf = nwi
        rtf = 1.0 - nwi
    else:
        rel_pos = nwi = etf = rtf = np.array([0.0])
    out[:, 480] = rel_pos
    out[:, 481] = nwi
    out[:, 482] = etf
    out[:, 483] = rtf
    # sanitize
    out = np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)
    return out


def _predict_peak_probability(model, X484: np.ndarray) -> float:
    """Run Stage-1 XGBoost + the model's native probability, return peak over windows."""
    try:
        proba = model.predict_proba(X484)
    except Exception:
        # some sklearn-compatible models expose predict_proba differently
        try:
            proba = model.predict(X484)
        except Exception as e:
            log.warning("neurovision_localization: model predict failed: %s", e)
            return 0.0
    proba = np.asarray(proba)
    if proba.ndim == 2 and proba.shape[1] >= 2:
        proba = proba[:, 1]
    else:
        proba = proba.ravel()
    proba = proba.astype(np.float64)
    proba = np.nan_to_num(proba, nan=0.0, posinf=0.0, neginf=0.0)
    return float(np.max(proba))


# =============================================================================
# Public API
# =============================================================================

def is_available() -> bool:
    """True iff the XGBoost model AND the feature dependencies are loadable."""
    if not _ensure_feature_deps():
        return False
    return _load_model() is not None


def _select_window_indices(n_windows: int, cap: int = 80) -> np.ndarray:
    """Uniformly subsample to at most `cap` windows (keeps latency bounded for
    long recordings) while preserving chronological order."""
    if n_windows <= cap:
        return np.arange(n_windows)
    return np.linspace(0, n_windows - 1, cap).astype(int)


def compute_model_driven_localization(
    data_matrix: np.ndarray,
    channel_names: List[str],
    sfreq: float,
) -> Optional[Dict[str, object]]:
    """
    Run the trained XGBoost model and attribute the dominant seizure region via
    leave-one-out channel ablation.

    Args:
        data_matrix: (n_channels x n_samples) float array, Volts (MNE convention).
        channel_names: ordered channel labels matching data_matrix rows (10-20).
        sfreq: sampling rate in Hz.

    Returns dict with:
        dominant_lead, dominant_zone, peak_seizure_probability,
        channel_contributions (dict lead -> ablation drop), localization_method,
        n_windows. Returns None if the model / deps are unavailable or input is
        too short for a single window.
    """
    if not _ensure_feature_deps():
        return None
    model = _load_model()
    if model is None:
        return None
    if data_matrix is None or data_matrix.size == 0 or len(channel_names) == 0:
        return None

    data = np.asarray(data_matrix, dtype=np.float64)
    n_ch, n_samples = data.shape
    win_len = int(round(WINDOW_LENGTH_SEC * sfreq))
    stride = int(round(STRIDE_SEC * sfreq))
    if n_samples < win_len or win_len < MIN_WAVELET_SAMPLES:
        log.info("neurovision_localization: recording too short (%d samples < %d); "
                 "skipping ablation.", n_samples, win_len)
        return None

    # ---- build window index list (capped for latency) ----
    starts = list(range(0, n_samples - win_len + 1, stride))
    sel = _select_window_indices(len(starts))
    starts = [starts[i] for i in sel]
    if not starts:
        return None

    t0 = time.perf_counter()
    # ---- STEP 1: per-channel per-window base features, computed ONCE ----
    # per_channel[w][c] = dict of 32 base features
    per_channel: List[List[Dict[str, float]]] = []
    for s in starts:
        window = data[:, s:s + win_len]
        ch_feats = []
        for c in range(n_ch):
            try:
                ch_feats.append(_extract_channel_features(window[c, :], sfreq))
            except Exception:
                # zeroed feature vector so aggregation still works
                ch_feats.append({b: 0.0 for b in BASE_FEATURES})
        per_channel.append(ch_feats)

    # ---- STEP 2: baseline aggregation (all channels) ----
    def aggregate_rows(exclude: int) -> List[List[float]]:
        rows = []
        for w in range(len(starts)):
            chans = [per_channel[w][c] for c in range(n_ch) if c != exclude]
            rows.append(_aggregate(chans))
        return rows

    baseline_windows = aggregate_rows(exclude=-1)  # all channels
    X_base = _build_temporal_matrix(baseline_windows)
    baseline_peak = _predict_peak_probability(model, X_base)

    # ---- STEP 3: channel ablation (re-aggregate only; no entropy recompute) ----
    contributions: Dict[str, float] = {}
    ablated_peaks: Dict[str, float] = {}
    for c, name in enumerate(channel_names):
        if name not in LEAD_TO_ZONE_MAP:
            continue
        ablated_windows = aggregate_rows(exclude=c)
        X_abl = _build_temporal_matrix(ablated_windows)
        abl_peak = _predict_peak_probability(model, X_abl)
        ablated_peaks[name] = abl_peak
        # contribution = how much removing this channel REDUCES the seizure prob
        contributions[name] = max(0.0, baseline_peak - abl_peak)

    if not contributions:
        return None

    # dominant = channel whose absence most reduced the model's seizure output
    dominant_lead = max(contributions, key=contributions.get)
    dominant_drop = contributions[dominant_lead]
    dominant_zone = LEAD_TO_ZONE_MAP.get(dominant_lead, "DIFFUSE")

    # The gate affects confidence/risk tier, NOT the localization itself.
    # Always report the actual top contributing channel from ablation so the
    # API can expose the model's strongest attribution even when overall
    # seizure probability is low. The caller uses `below_gate` to set the
    # risk tier / evidence strength.
    GATE = 0.5012
    below_gate = bool(baseline_peak < GATE or dominant_drop < 1e-4)

    elapsed = time.perf_counter() - t0
    log.info(
        "neurovision_localization: ablation done in %.2fs | baseline_peak=%.4f "
        "dominant=%s(%s) drop=%.4f below_gate=%s windows=%d",
        elapsed, baseline_peak, dominant_lead, dominant_zone,
        dominant_drop, below_gate, len(starts),
    )

    return {
        "dominant_lead": dominant_lead,
        "dominant_zone": dominant_zone,
        "peak_seizure_probability": round(baseline_peak, 6),
        "channel_contributions": {k: round(v, 6) for k, v in contributions.items()},
        "localization_method": "xgboost_channel_ablation",
        "n_windows": len(starts),
        "baseline_peak": round(baseline_peak, 6),
        "below_gate": below_gate,
    }
