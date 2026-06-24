#!/usr/bin/env python3
"""
================================================================================
PHASE9_PATIENT_CALIBRATED_ENGINE.py
NeuroVision AI :: CHB-MIT EEG Seizure Detection :: Phase 9 Patient-Calibrated
Clinical Validation Engine
================================================================================

Phase 8 proved that a single global Stage-2 discriminator threshold
(disc_threshold = 0.50) cannot survive cross-patient domain drift: hyper-active
patient baselines vary wildly, producing 16,365 false alarm records and a
global FPR/h of ~10.0. Phase 9 introduces an inline Patient-Specific
Initialization Calibration Layer that derives a per-recording Adaptive
Decision Gate from the first 600 windows (~10 minutes) of each EDF recording,
then runs the full two-stage cascade against that file-specific gate instead
of a fixed global threshold.

ARCHITECTURAL NOTE ON FEATURE CONTRACT (UNCHANGED FROM PHASE 8)
-----------------------------------------------------------------
Stage 1 (base XGBoost) operates strictly on the 96 discovered base feature
columns -- there is no window-level lag/rolling expansion. The authoritative
inference column order is resolved via `base_model.feature_names_in_` when
present, falling back to a natural-integer sort (`natural_sort_key`) over the
96 base columns only if that attribute is absent.

Stage 2 (PHASE7B_FP_DISCRIMINATOR.pkl) operates on the 480-wide event-level
summary matrix produced by `build_event_feature_table()`:
`{base_feature}_{mean,std,q25,q50,q75}` across the 96 base features, scaled by
PHASE7B_DISCRIMINATOR_SCALER.pkl before inference. This contract is reused
verbatim from Phase 8 -- only the *decision threshold* fed into Stage 2 is now
adaptive per recording.

PATIENT-SPECIFIC INITIALIZATION CALIBRATION (THE CORE CHANGE)
-----------------------------------------------------------------
For every (patient, edf) recording group:
  1. Slice the first 600 windows (the initial ~10 minutes of recording,
     assumed non-seizure onset baseline) as the Calibration Window.
  2. Run Stage-1 inference, Back-Projection Z-Score normalization,
     smoothing, and event grouping on that slice alone.
  3. Run any harvested calibration candidate events through Stage-2 to get
     a raw discriminator confidence array.
  4. mu_base = mean(confidences), sigma_base = std(confidences). If no
     calibration events are harvested, mu_base = sigma_base = 0.0.
  5. file_disc_threshold = max(0.50, mu_base + 2.0 * sigma_base).
  6. Run full-recording cascade inference using file_disc_threshold as the
     Stage-2 acceptance gate (replacing CFG.DISC_THRESHOLD).

No placeholders, no TODOs, no truncated blocks.
================================================================================
"""

import sys
import json
import time
import warnings
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

import pyarrow.parquet as pq

from pandas.api.types import is_numeric_dtype

warnings.filterwarnings("ignore")


# ==============================================================================
# CONFIGURATION
# ==============================================================================

class Config:
    DATA_PATH = r"E:\Project\neurovision_ai\real_feature_dataset_v4_clean.parquet"
    PARQUET_PATH = DATA_PATH
    MODEL_PATH = r"E:\Project\neurovision_ai\PHASE5B_TEMPORAL_XGBOOST.joblib"
    DISCRIMINATOR_PATH = r"E:\Project\neurovision_ai\PHASE7B_FP_DISCRIMINATOR.pkl"
    DISCRIMINATOR_SCALER_PATH = r"E:\Project\neurovision_ai\PHASE7B_DISCRIMINATOR_SCALER.pkl"
    OUTPUT_DIR = Path(r"E:\Project\neurovision_ai\PHASE9_OUTPUTS")

    PATIENT_COL = "patient"
    LABEL_COL = "label"
    EDF_COL = "edf"
    WINDOW_DURATION_COL = "window_duration_sec"
    WINDOW_IDX_COL = "window_idx"
    WINDOW_INDEX_COL = "window_index"

    # All known structural metadata columns to exclude from the feature set.
    META_COLS = [
        "label", "patient", "edf", "window_uid", "window_index",
        "window_start_sec", "window_end_sec", "window_duration_sec",
        "stride_sec", "seizure_state", "window_idx",
    ]

    # Frozen cascade hyperparameters carried over from Phase 8. DISC_THRESHOLD
    # below is now only the *floor* of the adaptive per-file gate (see
    # compute_adaptive_disc_threshold) rather than a fixed global cutoff.
    MPP = 0.10
    DISC_THRESHOLD_FLOOR = 0.50
    SMOOTH_WINDOW = 5
    GAP_TOLERANCE = 2

    # Patient-Specific Initialization Calibration Layer parameters.
    CALIBRATION_WINDOW_COUNT = 600
    CALIBRATION_SIGMA_MULTIPLIER = 2.0

    EVENT_AGG_STATS = ["mean", "std", "q25", "q50", "q75"]

    DEFAULT_WINDOW_DURATION_SEC = 1.0

    CHUNK_SIZE = 50_000
    RANDOM_STATE = 42


CFG = Config()


# ==============================================================================
# LOGGING HELPER
# ==============================================================================

LOG_LINES = []


def log(msg: str):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    LOG_LINES.append(line)


# ==============================================================================
# STEP 0: SCHEMA DISCOVERY & TYPE-SAFE CHUNKED LOADING
# ==============================================================================

def natural_sort_key(name):
    """Parse raw numerical index weights from 'fN' strings to enforce a rigid
    positional ordering (f0, f1, f2, ... fN) rather than lexicographic
    ('f10' before 'f2') ordering, which would corrupt tree traversal paths.
    Used only as the fallback resolution path for the 96 base feature
    columns when the base model lacks a native feature_names_in_ attribute."""
    if isinstance(name, str) and name.startswith("f") and name[1:].isdigit():
        return (0, int(name[1:]))
    return (1, str(name))


def discover_schema(parquet_path: str):
    log(f"STEP 0: Discovering schema from {parquet_path}")
    pf = pq.ParquetFile(parquet_path)
    schema = pf.schema_arrow
    all_columns = [f.name for f in schema]

    meta_cols_present = [c for c in CFG.META_COLS if c in all_columns]
    candidate_feature_cols = [c for c in all_columns if c not in CFG.META_COLS]

    string_like_types = {"string", "large_string", "utf8", "large_utf8"}
    feature_cols = []
    for c in candidate_feature_cols:
        arrow_type = str(schema.field(c).type)
        if arrow_type in string_like_types:
            continue
        feature_cols.append(c)

    feature_cols_sorted = sorted(feature_cols, key=natural_sort_key)

    log(f"STEP 0: Total columns={len(all_columns)} | "
        f"meta_cols={meta_cols_present} | numeric_feature_cols={len(feature_cols)}")

    return {
        "all_columns": all_columns,
        "feature_cols": feature_cols,
        "feature_cols_sorted": feature_cols_sorted,
        "meta_cols": meta_cols_present,
        "num_row_groups": pf.num_row_groups,
        "total_rows": pf.metadata.num_rows,
    }


def load_full_dataset(parquet_path: str, feature_cols, meta_cols):
    log("STEP 0: Loading full dataset via type-safe chunked reader")
    columns_to_read = list(dict.fromkeys(feature_cols + meta_cols))
    pf = pq.ParquetFile(parquet_path)

    frames = []
    for batch in pf.iter_batches(batch_size=CFG.CHUNK_SIZE, columns=columns_to_read):
        frames.append(batch.to_pandas())

    df = pd.concat(frames, ignore_index=True)
    del frames

    for c in feature_cols:
        if not is_numeric_dtype(df[c]):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df[c] = df[c].fillna(0.0).astype(np.float32)

    if CFG.PATIENT_COL in df.columns:
        df[CFG.PATIENT_COL] = df[CFG.PATIENT_COL].astype(str)
    if CFG.EDF_COL in df.columns:
        df[CFG.EDF_COL] = df[CFG.EDF_COL].astype(str)
    if CFG.LABEL_COL in df.columns:
        df[CFG.LABEL_COL] = pd.to_numeric(df[CFG.LABEL_COL], errors="coerce").fillna(0).astype(np.int8)
    if CFG.WINDOW_DURATION_COL in df.columns:
        df[CFG.WINDOW_DURATION_COL] = pd.to_numeric(
            df[CFG.WINDOW_DURATION_COL], errors="coerce"
        ).fillna(CFG.DEFAULT_WINDOW_DURATION_SEC).astype(np.float32)
    if CFG.WINDOW_IDX_COL in df.columns:
        df[CFG.WINDOW_IDX_COL] = pd.to_numeric(df[CFG.WINDOW_IDX_COL], errors="coerce").fillna(-1).astype(np.int64)
    elif CFG.WINDOW_INDEX_COL in df.columns:
        df[CFG.WINDOW_INDEX_COL] = pd.to_numeric(df[CFG.WINDOW_INDEX_COL], errors="coerce").fillna(-1).astype(np.int64)

    log(f"STEP 0: Loaded dataframe shape={df.shape}")
    return df


# ==============================================================================
# STEP 1: BASE MODEL LOAD & FEATURE-ALIGNMENT RESOLUTION
# ==============================================================================

def load_base_model_and_resolve_features(model_path: str, discovered_feature_cols, sorted_fallback_cols):
    log(f"STEP 1: Loading base model from {model_path}")
    base_model = joblib.load(model_path)

    native_features = getattr(base_model, "feature_names_in_", None)
    if native_features is not None:
        native_features = list(native_features)
        matched = [c for c in native_features if c in discovered_feature_cols]
        log(f"STEP 1: base_model.feature_names_in_ present ({len(native_features)} cols). "
            f"Matched against parquet: {len(matched)}/{len(native_features)}")
        if len(matched) != len(native_features):
            missing = sorted(set(native_features) - set(discovered_feature_cols))
            raise ValueError(
                f"Model expects {len(native_features)} features but only "
                f"{len(matched)} are present in the parquet schema. "
                f"Missing columns: {missing}"
            )
        inference_columns = native_features
    else:
        log("STEP 1: base_model has no feature_names_in_ attribute -- "
            "enforcing natural numerical sort fallback over the 96 base columns")
        inference_columns = sorted_fallback_cols
        log(f"STEP 1: First 5 aligned columns: {inference_columns[:5]}")
        log(f"STEP 1: Last 5 aligned columns: {inference_columns[-5:]}")

    return base_model, inference_columns


def predict_base_probabilities(base_model, df: pd.DataFrame, inference_columns):
    X_inference = df.reindex(columns=inference_columns)
    for c in inference_columns:
        if not is_numeric_dtype(X_inference[c]):
            X_inference[c] = pd.to_numeric(X_inference[c], errors="coerce")
    X_inference = X_inference.fillna(0.0).astype(np.float32)

    proba = base_model.predict_proba(X_inference.values)
    if proba.ndim == 2 and proba.shape[1] >= 2:
        pos_proba = proba[:, 1]
    else:
        pos_proba = proba.ravel()
    return pos_proba


# ==============================================================================
# SHARED EVENT-GROUPING / SMOOTHING UTILITIES
# ==============================================================================

def smooth_probabilities(proba: np.ndarray, smooth_window: int) -> np.ndarray:
    smooth_window = int(float(smooth_window))
    if smooth_window <= 1:
        return proba
    kernel = np.ones(smooth_window, dtype=np.float64) / smooth_window
    return np.convolve(proba, kernel, mode="same")


def group_windows_into_events(flags: np.ndarray, gap_tolerance: int):
    gap_tolerance = int(float(gap_tolerance))
    n = len(flags)
    events = []
    i = 0
    while i < n:
        if not flags[i]:
            i += 1
            continue
        start = i
        end = i
        gap = 0
        j = i + 1
        while j < n:
            if flags[j]:
                end = j
                gap = 0
            else:
                gap += 1
                if gap > gap_tolerance:
                    break
            j += 1
        events.append((start, end))
        i = end + gap_tolerance + 2
    return events


def build_event_feature_table(events, feature_cols, agg_stats):
    """Vectorized event-level aggregation: collapses each event's window
    matrix into a single row of mean/std/q25/q50/q75 per base feature.
    Column order/count must match PHASE7B_DISCRIMINATOR_SCALER.pkl exactly:
    {base_feature}_{mean,std,q25,q50,q75} for each of the 96 base features
    in `feature_cols` order, grouped by aggregation stat block."""
    if not events:
        agg_cols = [f"{c}_{s}" for c in feature_cols for s in agg_stats]
        return pd.DataFrame(columns=agg_cols + ["patient", "edf", "n_windows", "max_proba", "mean_proba"])

    dfs_to_concat = []
    for ev_idx, ev in enumerate(events):
        win_df = ev["feature_window_df"][feature_cols].copy()
        for col in feature_cols:
            if not is_numeric_dtype(win_df[col]):
                win_df[col] = pd.to_numeric(win_df[col], errors="coerce")
        win_df["_event_id"] = ev_idx
        dfs_to_concat.append(win_df)

    big_df = pd.concat(dfs_to_concat, ignore_index=True)
    grouped = big_df.groupby("_event_id")

    agg_mean = grouped.mean().astype(np.float32)
    agg_std = grouped.std(ddof=0).astype(np.float32)
    agg_q25 = grouped.quantile(0.25).astype(np.float32)
    agg_q50 = grouped.median().astype(np.float32)
    agg_q75 = grouped.quantile(0.75).astype(np.float32)

    agg_mean.columns = [f"{c}_mean" for c in agg_mean.columns]
    agg_std.columns = [f"{c}_std" for c in agg_std.columns]
    agg_q25.columns = [f"{c}_q25" for c in agg_q25.columns]
    agg_q50.columns = [f"{c}_q50" for c in agg_q50.columns]
    agg_q75.columns = [f"{c}_q75" for c in agg_q75.columns]

    features_df = pd.concat([agg_mean, agg_std, agg_q25, agg_q50, agg_q75], axis=1)
    features_df = features_df.reindex(range(len(events))).fillna(0.0)

    meta_rows = [{
        "patient": ev["patient"], "edf": ev["edf"], "n_windows": ev["n_windows"],
        "max_proba": ev["max_proba"], "mean_proba": ev["mean_proba"],
    } for ev in events]
    meta_df = pd.DataFrame(meta_rows)

    return pd.concat([meta_df, features_df], axis=1)


def build_pseudo_events(df_recording, candidate_events, smoothed_proba, feature_cols, patient_id, edf_id):
    """Materializes raw (start_idx, end_idx) tuples from group_windows_into_events
    into the full pseudo-event dict structure consumed by build_event_feature_table
    and the Stage-2 discriminator path."""
    pseudo_events = []
    for (start, end) in candidate_events:
        window_slice = df_recording.iloc[start:end + 1]
        pseudo_events.append({
            "patient": patient_id, "edf": edf_id,
            "start_idx": start, "end_idx": end,
            "n_windows": end - start + 1,
            "max_proba": float(np.max(smoothed_proba[start:end + 1])),
            "mean_proba": float(np.mean(smoothed_proba[start:end + 1])),
            "feature_window_df": window_slice[feature_cols],
        })
    return pseudo_events


def run_stage1_and_smoothing(df_recording: pd.DataFrame, base_model, inference_columns):
    """Runs Stage-1 base-model inference plus Back-Projection Z-Score
    normalization and convolution smoothing ONCE, over the entire recording.

    IMPORTANT: p_mean/p_std for the Z-score line must be computed from the
    full-file distribution, never from a truncated sub-slice. A 600-window
    calibration slice can be unusually flat (e.g. a quiet first 10 minutes),
    collapsing p_std toward the 1e-6 floor and inflating later-window Z-scores
    artificially. Both the calibration layer and the full-recording flagging
    pass must therefore read off this same full-file rescaled_proba /
    smoothed_proba array -- only the *event-grouping gate* differs between
    a calibration sub-window and the full file (see compute_adaptive_gate_and_flags)."""
    raw_proba = predict_base_probabilities(base_model, df_recording, inference_columns)

    p_mean = float(np.mean(raw_proba))
    p_std = float(max(np.std(raw_proba), 1e-6))
    z_scores = (raw_proba - p_mean) / p_std
    rescaled_proba = 1.0 / (1.0 + np.exp(-0.5 * z_scores))

    smoothed_proba = smooth_probabilities(rescaled_proba, int(float(CFG.SMOOTH_WINDOW)))

    return rescaled_proba, smoothed_proba


def compute_adaptive_gate_and_flags(smoothed_proba_window: np.ndarray):
    """Computes the local variance-aware adaptive gate and boolean flags for
    an arbitrary (already Z-score-rescaled and smoothed) probability window.
    This is intentionally LOCAL -- the gate threshold itself is allowed to
    differ between the 600-window calibration slice and the full recording,
    since each is being asked "what counts as elevated activity within this
    specific window of data". What must NOT differ is the underlying Z-score
    scaling that produced smoothed_proba_window in the first place -- that is
    always derived from the full-file p_mean/p_std (see run_stage1_and_smoothing)."""
    mpp = float(CFG.MPP)
    adaptive_gate = float(np.mean(smoothed_proba_window) + (1.5 * np.std(smoothed_proba_window)))
    flags = (smoothed_proba_window >= adaptive_gate) & (smoothed_proba_window >= mpp)
    return flags


def score_events_with_discriminator(pseudo_events, feature_cols, agg_stats, discriminator, disc_scaler):
    """Runs the Stage-2 discriminator over a list of pseudo-events and returns
    the raw seizure-probability confidence array (empty array if no events)."""
    if not pseudo_events:
        return np.array([], dtype=np.float64)

    agg_table = build_event_feature_table(pseudo_events, feature_cols, agg_stats)
    agg_cols = [f"{c}_{s}" for c in feature_cols for s in agg_stats]
    X_event = agg_table[agg_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).astype(np.float32)
    X_event_scaled = disc_scaler.transform(X_event)

    disc_proba = discriminator.predict_proba(X_event_scaled)
    if disc_proba.ndim == 2 and disc_proba.shape[1] >= 2:
        disc_proba = disc_proba[:, 1]
    else:
        disc_proba = disc_proba.ravel()
    return disc_proba


# ==============================================================================
# STEP 2A: PATIENT-SPECIFIC INITIALIZATION CALIBRATION LAYER (THE CORE CHANGE)
# ==============================================================================

def compute_adaptive_disc_threshold(df_recording: pd.DataFrame, smoothed_proba_full: np.ndarray,
                                     feature_cols, discriminator, disc_scaler, agg_stats,
                                     patient_id, edf_id):
    """
    Isolates the first CFG.CALIBRATION_WINDOW_COUNT windows of a recording
    (the initial ~10 minutes, assumed non-seizure baseline) to derive a
    file-specific Adaptive Decision Gate:

        file_disc_threshold = max(DISC_THRESHOLD_FLOOR,
                                   mu_base + CALIBRATION_SIGMA_MULTIPLIER * sigma_base)

    CRITICAL: this slices `smoothed_proba_full` -- the already Z-score-
    rescaled and smoothed signal computed from the FULL recording in
    run_stage1_and_smoothing() -- rather than re-running Stage-1 on the
    truncated 600-window slice in isolation. Re-deriving p_mean/p_std from
    only 600 windows is a sample-bias trap: a quiet first 10 minutes collapses
    p_std toward the 1e-6 floor and inflates Z-scores artificially, producing
    a calibration baseline that doesn't reflect the file's true noise floor.
    The event-grouping *gate* (compute_adaptive_gate_and_flags) is still
    computed locally over just this slice -- only the underlying Z-score
    scaling is shared/global.

    If no candidate events are harvested during calibration (e.g. very short
    recordings, or a quiet first 10 minutes with no flagged activity at all),
    mu_base and sigma_base fall back gracefully to 0.0, and the threshold
    collapses to the DISC_THRESHOLD_FLOOR.
    """
    n_windows_total = len(df_recording)
    calib_n = min(CFG.CALIBRATION_WINDOW_COUNT, n_windows_total)
    calib_slice = df_recording.iloc[:calib_n].reset_index(drop=True)
    calib_smoothed_proba = smoothed_proba_full[:calib_n]

    mu_base = 0.0
    sigma_base = 0.0
    n_calibration_events = 0

    if calib_n > 0:
        calib_flags = compute_adaptive_gate_and_flags(calib_smoothed_proba)
        calib_candidate_events = group_windows_into_events(calib_flags, int(float(CFG.GAP_TOLERANCE)))

        if calib_candidate_events:
            calib_pseudo_events = build_pseudo_events(
                calib_slice, calib_candidate_events, calib_smoothed_proba,
                feature_cols, patient_id, edf_id
            )
            calib_disc_proba = score_events_with_discriminator(
                calib_pseudo_events, feature_cols, agg_stats, discriminator, disc_scaler
            )
            if calib_disc_proba.size > 0:
                mu_base = float(np.mean(calib_disc_proba))
                sigma_base = float(np.std(calib_disc_proba))
                n_calibration_events = int(calib_disc_proba.size)

    file_disc_threshold = max(
        float(CFG.DISC_THRESHOLD_FLOOR),
        mu_base + (float(CFG.CALIBRATION_SIGMA_MULTIPLIER) * sigma_base)
    )

    calibration_summary = {
        "patient": patient_id, "edf": edf_id,
        "calibration_windows_used": calib_n,
        "n_calibration_events": n_calibration_events,
        "mu_base": mu_base, "sigma_base": sigma_base,
        "file_disc_threshold": file_disc_threshold,
    }

    return file_disc_threshold, calibration_summary


# ==============================================================================
# STEP 2B: TWO-STAGE CASCADE INFERENCE WITH PATIENT-CALIBRATED GATE
# ==============================================================================

def cascade_inference(df_recording: pd.DataFrame, rescaled_proba: np.ndarray, smoothed_proba: np.ndarray,
                       feature_cols, discriminator, disc_scaler, agg_stats,
                       file_disc_threshold: float):
    """
    Runs Stage-2 grouping/discrimination on a single patient/edf recording
    using `file_disc_threshold` (derived per-file by the calibration layer)
    as the Stage-2 acceptance gate, in place of a fixed global threshold.

    `rescaled_proba`/`smoothed_proba` are the full-file Z-score-scaled signal
    already computed once in run_stage1_and_smoothing() -- this function does
    NOT re-run Stage-1, so the calibration pass and this full-file pass are
    guaranteed to share identical Z-score scaling, differing only in which
    slice of the signal each evaluates and which local gate each applies.

    Returns (raw_proba, smoothed_proba, candidate_events, surviving_events,
    rejected_events).
    """
    gap_tolerance = int(float(CFG.GAP_TOLERANCE))

    flags = compute_adaptive_gate_and_flags(smoothed_proba)
    candidate_events = group_windows_into_events(flags, gap_tolerance)

    surviving_events, rejected_events = [], []
    if not candidate_events:
        return rescaled_proba, smoothed_proba, [], [], []

    patient_id = df_recording[CFG.PATIENT_COL].iloc[0] if CFG.PATIENT_COL in df_recording else "unknown"
    edf_id = df_recording[CFG.EDF_COL].iloc[0] if CFG.EDF_COL in df_recording else "unknown"

    pseudo_events = build_pseudo_events(
        df_recording, candidate_events, smoothed_proba, feature_cols, patient_id, edf_id
    )

    disc_proba = score_events_with_discriminator(
        pseudo_events, feature_cols, agg_stats, discriminator, disc_scaler
    )

    for idx, ev in enumerate(pseudo_events):
        ev["discriminator_seizure_proba"] = float(disc_proba[idx])
        ev["kept"] = bool(disc_proba[idx] >= file_disc_threshold)
        if ev["kept"]:
            surviving_events.append(ev)
        else:
            rejected_events.append(ev)

    return rescaled_proba, smoothed_proba, candidate_events, surviving_events, rejected_events


# ==============================================================================
# GROUND-TRUTH SEIZURE SEGMENTATION
# ==============================================================================

def extract_ground_truth_events(df_recording: pd.DataFrame):
    labels = df_recording[CFG.LABEL_COL].values
    n = len(labels)
    gt_events = []
    i = 0
    while i < n:
        if labels[i] == 1:
            start = i
            while i < n and labels[i] == 1:
                i += 1
            gt_events.append((start, i - 1))
        else:
            i += 1
    return gt_events


def overlaps(a, b):
    return a[0] <= b[1] and b[0] <= a[1]


# ==============================================================================
# STEP 3: PER-RECORDING METRIC EVALUATION (Report A + per-recording latency/FA)
# ==============================================================================

def evaluate_recording(patient, edf, df_recording, gt_events, surviving_events, rejected_events,
                        n_windows, file_disc_threshold, mu_base, sigma_base, n_calibration_events):
    kept_spans = [(ev["start_idx"], ev["end_idx"]) for ev in surviving_events]

    matched_gt = set()
    matched_pred_idx = set()
    for p_idx, pred in enumerate(kept_spans):
        for g_idx, gt in enumerate(gt_events):
            if overlaps(pred, gt):
                matched_gt.add(g_idx)
                matched_pred_idx.add(p_idx)

    tp = len(matched_pred_idx)
    fp = len(kept_spans) - tp
    fn = len(gt_events) - len(matched_gt)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    if CFG.WINDOW_DURATION_COL in df_recording.columns:
        mean_window_sec = float(df_recording[CFG.WINDOW_DURATION_COL].mean())
        if not np.isfinite(mean_window_sec) or mean_window_sec <= 0:
            mean_window_sec = CFG.DEFAULT_WINDOW_DURATION_SEC
    else:
        mean_window_sec = CFG.DEFAULT_WINDOW_DURATION_SEC

    total_hours = (n_windows * mean_window_sec) / 3600.0
    fpr_per_hour = fp / total_hours if total_hours > 0 else 0.0

    metrics_row = {
        "patient": patient, "edf": edf,
        "n_windows": n_windows,
        "n_ground_truth_seizures": len(gt_events),
        "n_candidate_events": len(surviving_events) + len(rejected_events),
        "n_surviving_events": len(surviving_events),
        "n_rejected_events": len(rejected_events),
        "TP": tp, "FP": fp, "FN": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "window_duration_sec_used": mean_window_sec,
        "recording_hours": total_hours,
        "fpr_per_hour": fpr_per_hour,
        "file_disc_threshold": file_disc_threshold,
        "calibration_mu_base": mu_base,
        "calibration_sigma_base": sigma_base,
        "n_calibration_events": n_calibration_events,
    }

    latency_rows = []
    for g_idx, gt in enumerate(gt_events):
        if g_idx not in matched_gt:
            continue
        gt_start_idx = gt[0]
        flagged_starts = [pred[0] for p_idx, pred in enumerate(kept_spans) if overlaps(pred, gt)]
        earliest_flag_idx = min(flagged_starts)
        latency = earliest_flag_idx - gt_start_idx
        latency_rows.append({
            "patient": patient, "edf": edf,
            "ground_truth_start_idx": gt_start_idx,
            "ground_truth_end_idx": gt[1],
            "flagged_start_idx": earliest_flag_idx,
            "latency_windows": int(latency),
            "latency_seconds": float(latency * mean_window_sec),
            "detection_type": "early_detection_benefit" if latency < 0 else (
                "instantaneous" if latency == 0 else "clinical_notification_delay"
            ),
        })

    return metrics_row, latency_rows, matched_gt


# ==============================================================================
# MAIN ORCHESTRATION
# ==============================================================================

def main():
    t0 = time.time()
    CFG.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # ---- STEP 0: schema + full dataset ----
        schema_info = discover_schema(CFG.PARQUET_PATH)
        df = load_full_dataset(CFG.PARQUET_PATH, schema_info["feature_cols"], schema_info["meta_cols"])
        feature_cols = schema_info["feature_cols"]

        # ---- STEP 1: base model + feature alignment ----
        base_model, inference_columns = load_base_model_and_resolve_features(
            CFG.MODEL_PATH, feature_cols, schema_info["feature_cols_sorted"]
        )

        # ---- Load Stage-2 discriminator + scaler ----
        log(f"STEP 1b: Loading Stage-2 discriminator from {CFG.DISCRIMINATOR_PATH}")
        discriminator = joblib.load(CFG.DISCRIMINATOR_PATH)
        disc_scaler = joblib.load(CFG.DISCRIMINATOR_SCALER_PATH)

        all_patients = sorted(df[CFG.PATIENT_COL].unique().tolist())
        log(f"STEP 2: Running patient-calibrated cascade across {len(all_patients)} "
            f"patients / {df.groupby([CFG.PATIENT_COL, CFG.EDF_COL]).ngroups} recordings")

        metrics_rows = []
        latency_rows_all = []
        false_alarm_rows = []
        calibration_rows = []

        total_gt_seizures = 0
        total_matched_seizures = 0
        total_tp = total_fp = total_fn = 0
        total_recording_hours = 0.0
        all_latencies = []

        n_done = 0
        for (patient, edf), group in df.groupby([CFG.PATIENT_COL, CFG.EDF_COL], sort=False):
            group = group.reset_index(drop=True)
            n_windows = len(group)

            # ---- Single Stage-1 pass per recording (Z-score scaling must be
            # ---- derived from the full file, shared by calibration + full cascade) ----
            rescaled_proba, smoothed_proba = run_stage1_and_smoothing(
                group, base_model, inference_columns
            )

            # ---- STEP 2A: Patient-Specific Initialization Calibration ----
            file_disc_threshold, calib_summary = compute_adaptive_disc_threshold(
                group, smoothed_proba, feature_cols,
                discriminator, disc_scaler, CFG.EVENT_AGG_STATS,
                patient, edf
            )
            calibration_rows.append(calib_summary)

            # ---- STEP 2B: full-recording cascade against the adaptive gate ----
            (raw_proba, smoothed_proba, candidate_events,
             surviving_events, rejected_events) = cascade_inference(
                group, rescaled_proba, smoothed_proba, feature_cols,
                discriminator, disc_scaler, CFG.EVENT_AGG_STATS,
                file_disc_threshold
            )

            gt_events = extract_ground_truth_events(group)

            metrics_row, latency_rows, matched_gt = evaluate_recording(
                patient, edf, group, gt_events, surviving_events, rejected_events, n_windows,
                file_disc_threshold, calib_summary["mu_base"], calib_summary["sigma_base"],
                calib_summary["n_calibration_events"]
            )
            metrics_rows.append(metrics_row)
            latency_rows_all.extend(latency_rows)

            # ---- Report C: forensic false alarm dump ----
            for ev in rejected_events:
                false_alarm_rows.append({
                    "patient": patient, "edf": edf,
                    "start_idx": ev["start_idx"], "end_idx": ev["end_idx"],
                    "n_windows": ev["n_windows"],
                    "mean_base_proba": ev["mean_proba"],
                    "max_base_proba": ev["max_proba"],
                    "discriminator_seizure_proba": ev["discriminator_seizure_proba"],
                    "file_disc_threshold": file_disc_threshold,
                    "rejection_source": "stage2_discriminator_adaptive_gate",
                })
            for ev in surviving_events:
                span = (ev["start_idx"], ev["end_idx"])
                hit_any_gt = any(overlaps(span, gt) for gt in gt_events)
                if not hit_any_gt:
                    false_alarm_rows.append({
                        "patient": patient, "edf": edf,
                        "start_idx": ev["start_idx"], "end_idx": ev["end_idx"],
                        "n_windows": ev["n_windows"],
                        "mean_base_proba": ev["mean_proba"],
                        "max_base_proba": ev["max_proba"],
                        "discriminator_seizure_proba": ev["discriminator_seizure_proba"],
                        "file_disc_threshold": file_disc_threshold,
                        "rejection_source": "surviving_event_no_gt_overlap",
                    })

            # ---- Global executive accumulators ----
            total_gt_seizures += len(gt_events)
            total_matched_seizures += len(matched_gt)
            total_tp += metrics_row["TP"]
            total_fp += metrics_row["FP"]
            total_fn += metrics_row["FN"]
            total_recording_hours += metrics_row["recording_hours"]
            all_latencies.extend([r["latency_windows"] for r in latency_rows])

            n_done += 1
            if n_done % 25 == 0:
                log(f"STEP 2: Processed {n_done} recordings... "
                    f"(last file_disc_threshold={file_disc_threshold:.4f})")

        log(f"STEP 2: Patient-calibrated cascade complete across {n_done} recordings")

        # ---- Report A: PHASE9_CLINICAL_METRICS.csv ----
        metrics_df = pd.DataFrame(metrics_rows)
        metrics_path = CFG.OUTPUT_DIR / "PHASE9_CLINICAL_METRICS.csv"
        metrics_df.to_csv(metrics_path, index=False)
        log(f"STEP 3: Wrote {metrics_path} ({len(metrics_df)} rows)")

        # ---- Report B: PHASE9_LATENCY_REPORT.csv ----
        latency_df = pd.DataFrame(latency_rows_all)
        latency_path = CFG.OUTPUT_DIR / "PHASE9_LATENCY_REPORT.csv"
        latency_df.to_csv(latency_path, index=False)
        log(f"STEP 4: Wrote {latency_path} ({len(latency_df)} rows)")

        # ---- Report C: PHASE9_FALSE_ALARM_REPORT.csv ----
        false_alarm_df = pd.DataFrame(false_alarm_rows)
        false_alarm_path = CFG.OUTPUT_DIR / "PHASE9_FALSE_ALARM_REPORT.csv"
        false_alarm_df.to_csv(false_alarm_path, index=False)
        log(f"STEP 5: Wrote {false_alarm_path} ({len(false_alarm_df)} rows)")

        # ---- Bonus diagnostic artifact: per-file calibration ledger ----
        calibration_df = pd.DataFrame(calibration_rows)
        calibration_path = CFG.OUTPUT_DIR / "PHASE9_CALIBRATION_LEDGER.csv"
        calibration_df.to_csv(calibration_path, index=False)
        log(f"STEP 5b: Wrote {calibration_path} ({len(calibration_df)} rows)")

        # ---- Report D: PHASE9_CLINICAL_VALIDATION.json ----
        overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        overall_f1 = (2 * overall_precision * overall_recall / (overall_precision + overall_recall)
                       if (overall_precision + overall_recall) > 0 else 0.0)
        global_fpr_per_hour = total_fp / total_recording_hours if total_recording_hours > 0 else 0.0

        if all_latencies:
            lat_arr = np.array(all_latencies, dtype=np.float64)
            latency_stats = {
                "mean_latency_windows": float(np.mean(lat_arr)),
                "median_latency_windows": float(np.median(lat_arr)),
                "std_latency_windows": float(np.std(lat_arr)),
                "min_latency_windows": float(np.min(lat_arr)),
                "max_latency_windows": float(np.max(lat_arr)),
                "n_early_detections": int(np.sum(lat_arr < 0)),
                "n_delayed_detections": int(np.sum(lat_arr > 0)),
                "n_instantaneous_detections": int(np.sum(lat_arr == 0)),
            }
        else:
            latency_stats = {
                "mean_latency_windows": None, "median_latency_windows": None,
                "std_latency_windows": None, "min_latency_windows": None,
                "max_latency_windows": None, "n_early_detections": 0,
                "n_delayed_detections": 0, "n_instantaneous_detections": 0,
            }

        if not calibration_df.empty:
            calibration_stats = {
                "mean_file_disc_threshold": float(calibration_df["file_disc_threshold"].mean()),
                "median_file_disc_threshold": float(calibration_df["file_disc_threshold"].median()),
                "min_file_disc_threshold": float(calibration_df["file_disc_threshold"].min()),
                "max_file_disc_threshold": float(calibration_df["file_disc_threshold"].max()),
                "n_recordings_with_floor_threshold": int(
                    (calibration_df["file_disc_threshold"] <= CFG.DISC_THRESHOLD_FLOOR + 1e-9).sum()
                ),
                "n_recordings_with_raised_threshold": int(
                    (calibration_df["file_disc_threshold"] > CFG.DISC_THRESHOLD_FLOOR + 1e-9).sum()
                ),
                "n_recordings_with_zero_calibration_events": int(
                    (calibration_df["n_calibration_events"] == 0).sum()
                ),
            }
        else:
            calibration_stats = {}

        executive_summary = {
            "execution_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config": {
                "mpp": CFG.MPP,
                "disc_threshold_floor": CFG.DISC_THRESHOLD_FLOOR,
                "smooth_window": CFG.SMOOTH_WINDOW,
                "gap_tolerance": CFG.GAP_TOLERANCE,
                "calibration_window_count": CFG.CALIBRATION_WINDOW_COUNT,
                "calibration_sigma_multiplier": CFG.CALIBRATION_SIGMA_MULTIPLIER,
            },
            "dataset": {
                "total_recordings_audited": n_done,
                "total_patients_audited": len(all_patients),
                "total_windows_audited": int(metrics_df["n_windows"].sum()) if not metrics_df.empty else 0,
                "total_recording_hours": total_recording_hours,
            },
            "seizure_detection": {
                "total_ground_truth_seizures": total_gt_seizures,
                "total_seizures_successfully_intercepted": total_matched_seizures,
                "overall_sensitivity_recall": overall_recall,
                "overall_precision": overall_precision,
                "overall_event_f1": overall_f1,
                "total_TP": int(total_tp),
                "total_FP": int(total_fp),
                "total_FN": int(total_fn),
            },
            "false_alarm_burden": {
                "global_fpr_per_hour": global_fpr_per_hour,
                "total_false_alarm_records_logged": len(false_alarm_df),
            },
            "notification_latency": latency_stats,
            "patient_calibration_summary": calibration_stats,
        }

        json_path = CFG.OUTPUT_DIR / "PHASE9_CLINICAL_VALIDATION.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(executive_summary, f, indent=2)
        log(f"STEP 6: Wrote {json_path}")

        elapsed = time.time() - t0
        log(f"PHASE 9 PIPELINE COMPLETE in {elapsed:.1f}s. "
            f"Global F1={overall_f1:.4f} | Sensitivity={overall_recall:.4f} | "
            f"FPR/h={global_fpr_per_hour:.4f}")

        with open(CFG.OUTPUT_DIR / "PHASE9_PIPELINE_LOG.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(LOG_LINES))

        return 0

    except Exception as e:
        log(f"FATAL ERROR: {type(e).__name__}: {e}")
        log(traceback.format_exc())
        CFG.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(CFG.OUTPUT_DIR / "PHASE9_PIPELINE_LOG.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(LOG_LINES))
        return 2


if __name__ == "__main__":
    sys.exit(main())
