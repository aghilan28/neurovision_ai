#!/usr/bin/env python3
"""
================================================================================
PHASE8_CLINICAL_VALIDATION_ENGINE.py
NeuroVision AI :: CHB-MIT EEG Seizure Detection :: Phase 8 Forensic Clinical Audit
================================================================================

Exhaustive, end-to-end, unseen forensic medical audit engine. Runs the frozen
two-stage cascade (Phase 5B base XGBoost -> Phase 7B Stage-2 FP discriminator)
across every patient/edf recording in the dataset and produces four clinical
deliverables:

  A. PHASE8_CLINICAL_METRICS.csv      -- per patient/edf TP/FP/FN/Precision/
                                          Recall/F1/FPR-per-hour
  B. PHASE8_LATENCY_REPORT.csv        -- per-TP detection latency (windows)
  C. PHASE8_FALSE_ALARM_REPORT.csv    -- forensic dump of every rejected /
                                          surviving-but-FP event
  D. PHASE8_CLINICAL_VALIDATION.json  -- global executive summary

ARCHITECTURAL NOTE ON FEATURE CONTRACT
---------------------------------------
This engine deliberately reuses the Phase 7B feature-resolution and event-
aggregation primitives verbatim rather than re-deriving a flat f0..f483
lag/rolling expansion. The attached PHASE7B_FP_DISCRIMINATOR.pkl and
PHASE7B_DISCRIMINATOR_SCALER.pkl were trained on the
`<base_feature>_{mean,std,q25,q50,q75}` aggregation produced by
`build_event_feature_table()` over the 96 discovered base feature columns
(see Phase 7B Steps 2/5/6). Feeding it a different 484-column representation
would silently violate that contract and corrupt every downstream score.
The base XGBoost model's own native column order is resolved via
`feature_names_in_` (with a numeric f0->fN fallback only if that attribute is
absent) -- this is the fix that already cured the Phase 7 probability-
flatline regression, and is preserved unchanged here.

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
    OUTPUT_DIR = Path(r"E:\Project\neurovision_ai\PHASE8_OUTPUTS")

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

    # Frozen, audited-as-final cascade hyperparameters. Phase 8 performs no
    # tuning / sweeping -- it validates the cascade exactly as it will run in
    # production. mpp is fixed at the documented operational floor of 0.10;
    # disc_threshold/smooth_window/gap_tolerance mirror the Phase 7B grid.
    MPP = 0.10
    DISC_THRESHOLD = 0.50
    SMOOTH_WINDOW = 5
    GAP_TOLERANCE = 2

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
    positional ordering (f0, f1, f2, ... f483) rather than lexicographic
    ('f10' before 'f2') ordering, which would corrupt tree traversal paths."""
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
            "enforcing natural numerical sort fallback (f0 -> fN)")
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
    matrix into a single row of mean/std/q25/q50/q75 per base feature."""
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


# ==============================================================================
# STEP 2: TWO-STAGE CASCADE INFERENCE (FROZEN, NO TUNING)
# ==============================================================================

def cascade_inference(df_recording: pd.DataFrame, base_model, inference_columns,
                       feature_cols, discriminator, disc_scaler, agg_stats):
    """
    Runs the full frozen two-stage cascade on a single patient/edf recording
    and returns (raw_proba, smoothed_proba, candidate_events, surviving_events,
    rejected_events). Each event entry is a dict with start_idx/end_idx,
    max/mean proba, and the Stage-2 discriminator's seizure-probability score.
    """
    mpp = float(CFG.MPP)
    disc_threshold = float(CFG.DISC_THRESHOLD)
    smooth_window = int(float(CFG.SMOOTH_WINDOW))
    gap_tolerance = int(float(CFG.GAP_TOLERANCE))

    raw_proba = predict_base_probabilities(base_model, df_recording, inference_columns)

    # ---- Back-Projection Z-Score re-mapping ----
    p_mean = float(np.mean(raw_proba))
    p_std = float(max(np.std(raw_proba), 1e-6))
    z_scores = (raw_proba - p_mean) / p_std
    rescaled_proba = 1.0 / (1.0 + np.exp(-0.5 * z_scores))

    smoothed_proba = smooth_probabilities(rescaled_proba, smooth_window)

    # ---- Adaptive variance-aware gate, AND fixed operational floor (mpp) ----
    adaptive_gate = float(np.mean(smoothed_proba) + (1.5 * np.std(smoothed_proba)))
    flags = (smoothed_proba >= adaptive_gate) & (smoothed_proba >= mpp)

    candidate_events = group_windows_into_events(flags, gap_tolerance)

    surviving_events, rejected_events = [], []
    if not candidate_events:
        return rescaled_proba, smoothed_proba, [], [], []

    patient_id = df_recording[CFG.PATIENT_COL].iloc[0] if CFG.PATIENT_COL in df_recording else "unknown"
    edf_id = df_recording[CFG.EDF_COL].iloc[0] if CFG.EDF_COL in df_recording else "unknown"

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

    agg_table = build_event_feature_table(pseudo_events, feature_cols, agg_stats)
    agg_cols = [f"{c}_{s}" for c in feature_cols for s in agg_stats]
    X_event = agg_table[agg_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).astype(np.float32)
    X_event_scaled = disc_scaler.transform(X_event)

    disc_proba = discriminator.predict_proba(X_event_scaled)
    if disc_proba.ndim == 2 and disc_proba.shape[1] >= 2:
        disc_proba = disc_proba[:, 1]
    else:
        disc_proba = disc_proba.ravel()

    for idx, ev in enumerate(pseudo_events):
        ev["discriminator_seizure_proba"] = float(disc_proba[idx])
        ev["kept"] = bool(disc_proba[idx] >= disc_threshold)
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

def evaluate_recording(patient, edf, df_recording, gt_events, surviving_events, rejected_events, n_windows):
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

    # FPR/h -- duration per window from metadata if available, else 1.0s default.
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
    }

    # ---- Latency rows for every matched ground-truth event ----
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
        log(f"STEP 2: Running exhaustive forensic audit across {len(all_patients)} "
            f"patients / {df.groupby([CFG.PATIENT_COL, CFG.EDF_COL]).ngroups} recordings")

        metrics_rows = []
        latency_rows_all = []
        false_alarm_rows = []

        total_gt_seizures = 0
        total_matched_seizures = 0
        total_tp = total_fp = total_fn = 0
        total_recording_hours = 0.0
        all_latencies = []

        n_done = 0
        for (patient, edf), group in df.groupby([CFG.PATIENT_COL, CFG.EDF_COL], sort=False):
            group = group.reset_index(drop=True)
            n_windows = len(group)

            (raw_proba, smoothed_proba, candidate_events,
             surviving_events, rejected_events) = cascade_inference(
                group, base_model, inference_columns, feature_cols,
                discriminator, disc_scaler, CFG.EVENT_AGG_STATS
            )

            gt_events = extract_ground_truth_events(group)

            metrics_row, latency_rows, matched_gt = evaluate_recording(
                patient, edf, group, gt_events, surviving_events, rejected_events, n_windows
            )
            metrics_rows.append(metrics_row)
            latency_rows_all.extend(latency_rows)

            # ---- Report C: forensic false alarm dump ----
            # Includes (1) all Stage-2-rejected candidate events, and
            # (2) surviving events that nonetheless did not overlap any
            # ground-truth seizure (i.e. clinical false positives).
            kept_spans = [(ev["start_idx"], ev["end_idx"]) for ev in surviving_events]
            for ev in rejected_events:
                false_alarm_rows.append({
                    "patient": patient, "edf": edf,
                    "start_idx": ev["start_idx"], "end_idx": ev["end_idx"],
                    "n_windows": ev["n_windows"],
                    "mean_base_proba": ev["mean_proba"],
                    "max_base_proba": ev["max_proba"],
                    "discriminator_seizure_proba": ev["discriminator_seizure_proba"],
                    "rejection_source": "stage2_discriminator",
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
                log(f"STEP 2: Processed {n_done} recordings...")

        log(f"STEP 2: Forensic audit complete across {n_done} recordings")

        # ---- Report A: PHASE8_CLINICAL_METRICS.csv ----
        metrics_df = pd.DataFrame(metrics_rows)
        metrics_path = CFG.OUTPUT_DIR / "PHASE8_CLINICAL_METRICS.csv"
        metrics_df.to_csv(metrics_path, index=False)
        log(f"STEP 3: Wrote {metrics_path} ({len(metrics_df)} rows)")

        # ---- Report B: PHASE8_LATENCY_REPORT.csv ----
        latency_df = pd.DataFrame(latency_rows_all)
        latency_path = CFG.OUTPUT_DIR / "PHASE8_LATENCY_REPORT.csv"
        latency_df.to_csv(latency_path, index=False)
        log(f"STEP 4: Wrote {latency_path} ({len(latency_df)} rows)")

        # ---- Report C: PHASE8_FALSE_ALARM_REPORT.csv ----
        false_alarm_df = pd.DataFrame(false_alarm_rows)
        false_alarm_path = CFG.OUTPUT_DIR / "PHASE8_FALSE_ALARM_REPORT.csv"
        false_alarm_df.to_csv(false_alarm_path, index=False)
        log(f"STEP 5: Wrote {false_alarm_path} ({len(false_alarm_df)} rows)")

        # ---- Report D: PHASE8_CLINICAL_VALIDATION.json ----
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

        executive_summary = {
            "execution_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config": {
                "mpp": CFG.MPP,
                "disc_threshold": CFG.DISC_THRESHOLD,
                "smooth_window": CFG.SMOOTH_WINDOW,
                "gap_tolerance": CFG.GAP_TOLERANCE,
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
        }

        json_path = CFG.OUTPUT_DIR / "PHASE8_CLINICAL_VALIDATION.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(executive_summary, f, indent=2)
        log(f"STEP 6: Wrote {json_path}")

        elapsed = time.time() - t0
        log(f"PHASE 8 PIPELINE COMPLETE in {elapsed:.1f}s. "
            f"Global F1={overall_f1:.4f} | Sensitivity={overall_recall:.4f} | "
            f"FPR/h={global_fpr_per_hour:.4f}")

        with open(CFG.OUTPUT_DIR / "PHASE8_PIPELINE_LOG.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(LOG_LINES))

        return 0

    except Exception as e:
        log(f"FATAL ERROR: {type(e).__name__}: {e}")
        log(traceback.format_exc())
        CFG.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(CFG.OUTPUT_DIR / "PHASE8_PIPELINE_LOG.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(LOG_LINES))
        return 2


if __name__ == "__main__":
    sys.exit(main())
