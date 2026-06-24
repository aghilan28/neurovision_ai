#!/usr/bin/env python3
"""
================================================================================
neurovision_inference.py
NeuroVision AI :: CHB-MIT EEG Seizure Detection :: Production Inference Engine
================================================================================

Standalone, zero-research-framework execution engine extracted from the
Phase 10 Spatio-Temporal Accumulator validation pipeline.

Accepts a single parquet file path, runs the full multi-stage cascade
deterministically, and returns a structured JSON string payload.

Architecture:
  Stage 1  -- XGBoost base model (96 base EEG feature columns)
               Back-Projection Z-Score normalization + convolution smoothing
               Variance-aware adaptive gate flagging
  Calib    -- Patient-Specific Initialization Calibration Layer
               (first 600 windows → baseline discriminator → file_disc_threshold)
  Stage 2  -- FP Discriminator (480-wide event-level feature matrix)
               PHASE7B_FP_DISCRIMINATOR.pkl + PHASE7B_DISCRIMINATOR_SCALER.pkl
  Filter 1 -- Temporal Persistence Filter (≥ 5 continuous windows)
  Filter 2 -- Spatial Coherence Consolidation (merge events ≤ 5-window gap)

Output: deterministic JSON payload per the clinical alert contract.
================================================================================
"""

import re
import sys
import json
import time
import warnings
import traceback
import pickle
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

import numpy as np
import pandas as pd
import joblib
import pyarrow.parquet as pq
from pandas.api.types import is_numeric_dtype

warnings.filterwarnings("ignore")


# ==============================================================================
# CONSTANTS
# ==============================================================================

_META_COLS: List[str] = [
    "label",
    "patient",
    "edf",
    "window_uid",
    "window_index",
    "window_start_sec",
    "window_end_sec",
    "window_duration_sec",
    "stride_sec",
    "seizure_state",
    "window_idx",
]

_MPP: float                      = 0.10   
_DISC_THRESHOLD_FLOOR: float     = 0.50   
_SMOOTH_WINDOW: int              = 5      
_GAP_TOLERANCE: int              = 2      
_MIN_DURATION_WINDOWS: int       = 5      
_CONSOLIDATION_GAP_WINDOWS: int  = 5      
_CALIBRATION_WINDOW_COUNT: int   = 600    
_CALIBRATION_SIGMA_MULTIPLIER: float = 1.0  
_DEFAULT_WINDOW_DURATION_SEC: float  = 1.0
_EVENT_AGG_STATS: List[str] = ["mean", "std", "q25", "q50", "q75"]

_PATIENT_COL: str         = "patient"
_EDF_COL: str             = "edf"
_LABEL_COL: str           = "label"
_WINDOW_DURATION_COL: str = "window_duration_sec"
_WINDOW_IDX_COL: str      = "window_idx"
_WINDOW_INDEX_COL: str    = "window_index"


# ==============================================================================
# UTILITIES
# ==============================================================================

def _natural_sort_key(name: str) -> Tuple:
    if isinstance(name, str) and name.startswith("f") and name[1:].isdigit():
        return (0, int(name[1:]))
    return (1, str(name))


def _smooth_probabilities(proba: np.ndarray, smooth_window: int) -> np.ndarray:
    smooth_window = int(float(smooth_window))
    if smooth_window <= 1:
        return proba.copy()
    kernel = np.ones(smooth_window, dtype=np.float64) / smooth_window
    return np.convolve(proba, kernel, mode="same")


def _group_windows_into_events(
    flags: np.ndarray, gap_tolerance: int
) -> List[Tuple[int, int]]:
    gap_tolerance = int(float(gap_tolerance))
    n = len(flags)
    events: List[Tuple[int, int]] = []
    i = 0
    while i < n:
        if not flags[i]:
            i += 1
            continue
        start = i
        end   = i
        gap   = 0
        j     = i + 1
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


def _build_pseudo_events(
    candidate_events: List[Tuple[int, int]],
    smoothed_proba: np.ndarray,
    patient_id: str,
    edf_id: str,
) -> List[Dict[str, Any]]:
    pseudo_events: List[Dict[str, Any]] = []
    for (start, end) in candidate_events:
        pseudo_events.append(
            {
                "patient":    patient_id,
                "edf":        edf_id,
                "start_idx":  start,
                "end_idx":    end,
                "n_windows":  end - start + 1,
                "max_proba":  float(np.max(smoothed_proba[start : end + 1])),
                "mean_proba": float(np.mean(smoothed_proba[start : end + 1])),
            }
        )
    return pseudo_events


def _build_event_feature_table(
    df_recording: pd.DataFrame,
    events: List[Dict[str, Any]],
    feature_cols: List[str],
    agg_stats: List[str],
) -> pd.DataFrame:
    """Optimized feature compiler using centralized row indexing to prevent
    internal memory fragmentation bottlenecks."""
    agg_cols = [f"{c}_{s}" for c in feature_cols for s in agg_stats]

    if not events:
        return pd.DataFrame(
            columns=agg_cols + ["patient", "edf", "n_windows", "max_proba", "mean_proba"]
        )

    indices = []
    event_ids = []
    for ev_idx, ev in enumerate(events):
        start = int(ev["start_idx"])
        end = int(ev["end_idx"])
        r = list(range(start, end + 1))
        indices.extend(r)
        event_ids.extend([ev_idx] * len(r))

    # Single-pass batch slice to maintain data integrity
    big_df = df_recording.loc[indices, feature_cols].copy()
    for col in feature_cols:
        if not is_numeric_dtype(big_df[col]):
            big_df[col] = pd.to_numeric(big_df[col], errors="coerce")
    big_df["_event_id"] = event_ids

    grouped = big_df.groupby("_event_id")

    agg_mean = grouped.mean().astype(np.float32)
    agg_std  = grouped.std(ddof=0).astype(np.float32)
    agg_q25  = grouped.quantile(0.25).astype(np.float32)
    agg_q50  = grouped.median().astype(np.float32)
    agg_q75  = grouped.quantile(0.75).astype(np.float32)

    agg_mean.columns = [f"{c}_mean" for c in agg_mean.columns]
    agg_std.columns  = [f"{c}_std"  for c in agg_std.columns]
    agg_q25.columns  = [f"{c}_q25"  for c in agg_q25.columns]
    agg_q50.columns  = [f"{c}_q50"  for c in agg_q50.columns]
    agg_q75.columns  = [f"{c}_q75"  for c in agg_q75.columns]

    features_df = pd.concat(
        [agg_mean, agg_std, agg_q25, agg_q50, agg_q75], axis=1
    )
    features_df = features_df.reindex(range(len(events))).fillna(0.0)

    meta_rows = [
        {
            "patient":    ev["patient"],
            "edf":        ev["edf"],
            "n_windows":  ev["n_windows"],
            "max_proba":  ev["max_proba"],
            "mean_proba": ev["mean_proba"],
        }
        for ev in events
    ]
    meta_df = pd.DataFrame(meta_rows)
    return pd.concat([meta_df, features_df], axis=1)


def _score_events_with_discriminator(
    df_recording: pd.DataFrame,
    pseudo_events: List[Dict[str, Any]],
    feature_cols: List[str],
    agg_stats: List[str],
    discriminator: Any,
    disc_scaler: Any,
) -> np.ndarray:
    if not pseudo_events:
        return np.array([], dtype=np.float64)

    agg_table = _build_event_feature_table(df_recording, pseudo_events, feature_cols, agg_stats)
    agg_cols  = [f"{c}_{s}" for c in feature_cols for s in agg_stats]
    X_event   = (
        agg_table[agg_cols]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0.0)
        .astype(np.float32)
    )
    X_event_scaled = disc_scaler.transform(X_event)

    disc_proba = discriminator.predict_proba(X_event_scaled)
    if disc_proba.ndim == 2 and disc_proba.shape[1] >= 2:
        return disc_proba[:, 1]
    return disc_proba.ravel()


def _compute_adaptive_gate_and_flags(
    smoothed_proba_window: np.ndarray,
) -> np.ndarray:
    mpp           = float(_MPP)
    adaptive_gate = float(
        np.mean(smoothed_proba_window) + (1.5 * np.std(smoothed_proba_window))
    )
    return (smoothed_proba_window >= adaptive_gate) & (smoothed_proba_window >= mpp)


def _apply_temporal_persistence_filter(
    pseudo_events: List[Dict[str, Any]],
    smoothed_proba: np.ndarray,
    min_duration_windows: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    min_duration_windows = int(float(min_duration_windows))
    duration_passed:   List[Dict[str, Any]] = []
    duration_rejected: List[Dict[str, Any]] = []

    for ev in pseudo_events:
        span = int(ev["end_idx"]) - int(ev["start_idx"]) + 1
        ev_copy = dict(ev)
        ev_copy["duration_span_windows"] = span
        if span < min_duration_windows:
            start_idx = int(ev["start_idx"])
            end_idx   = int(ev["end_idx"])
            smoothed_proba[start_idx : end_idx + 1] = 0.0
            ev_copy["duration_filter_decision"] = "rejected_transient_artifact"
            duration_rejected.append(ev_copy)
        else:
            ev_copy["duration_filter_decision"] = "passed_persistence_threshold"
            duration_passed.append(ev_copy)

    return duration_passed, duration_rejected


def _consolidate_adjacent_events(
    events: List[Dict[str, Any]],
    consolidation_gap_windows: int,
) -> List[Dict[str, Any]]:
    consolidation_gap_windows = int(float(consolidation_gap_windows))

    if not events:
        return []

    sorted_events = sorted(events, key=lambda ev: int(ev["start_idx"]))
    consolidated: List[Dict[str, Any]] = []

    current = dict(sorted_events[0])
    current["_member_mean_probas"] = [current["mean_proba"]]
    current["_member_max_probas"]  = [current["max_proba"]]
    current["_merged_from_count"]  = 1

    for ev in sorted_events[1:]:
        ev_start = int(ev["start_idx"])
        cur_end  = int(current["end_idx"])
        gap      = ev_start - cur_end - 1

        if gap <= consolidation_gap_windows:
            current["end_idx"]   = max(int(current["end_idx"]), int(ev["end_idx"]))
            current["n_windows"] = int(current["end_idx"]) - int(current["start_idx"]) + 1
            current["_member_mean_probas"].append(ev["mean_proba"])
            current["_member_max_probas"].append(ev["max_proba"])
            current["_merged_from_count"] += 1
            if ev.get("discriminator_seizure_proba", 0.0) > current.get(
                "discriminator_seizure_proba", 0.0
            ):
                current["discriminator_seizure_proba"] = ev["discriminator_seizure_proba"]
            current["duration_span_windows"] = current["n_windows"]
        else:
            current["mean_proba"]        = float(np.mean(current["_member_mean_probas"]))
            current["max_proba"]         = float(np.max(current["_member_max_probas"]))
            current["merged_from_count"] = current.pop("_merged_from_count")
            del current["_member_mean_probas"]
            del current["_member_max_probas"]
            consolidated.append(current)

            current = dict(ev)
            current["_member_mean_probas"] = [current["mean_proba"]]
            current["_member_max_probas"]  = [current["max_proba"]]
            current["_merged_from_count"]  = 1

    current["mean_proba"]        = float(np.mean(current["_member_mean_probas"]))
    current["max_proba"]         = float(np.max(current["_member_max_probas"]))
    current["merged_from_count"] = current.pop("_merged_from_count")
    del current["_member_mean_probas"]
    del current["_member_max_probas"]
    consolidated.append(current)

    return consolidated


# ==============================================================================
# ENGINE CORE
# ==============================================================================

class NeuroVisionEngine:

    def __init__(
        self,
        base_model_path: str,
        discriminator_path: str,
        discriminator_scaler_path: str,
    ) -> None:
        self._base_model   = self._load_artifact(str(base_model_path))
        self._discriminator = self._load_artifact(str(discriminator_path))
        self._disc_scaler   = self._load_artifact(str(discriminator_scaler_path))

    def process_file(self, parquet_path: str) -> str:
        t0 = time.time()
        try:
            result = self._run_cascade(parquet_path, t0)
        except Exception as exc:
            result = {
                "status": "ERROR",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback": traceback.format_exc(),
            }
        return json.dumps(result, indent=2, ensure_ascii=False)

    def _run_cascade(self, parquet_path: str, t0: float) -> Dict[str, Any]:
        feature_cols, meta_cols_present = self._discover_schema(parquet_path)
        df = self._load_recording(parquet_path, feature_cols, meta_cols_present)

        patient_id = str(df[_PATIENT_COL].iloc[0]) if _PATIENT_COL in df.columns else "unknown"
        edf_id = str(df[_EDF_COL].iloc[0]) if _EDF_COL in df.columns else "unknown"
        n_windows = len(df)

        inference_columns = self._resolve_inference_columns(feature_cols)

        rescaled_proba, smoothed_proba = self._run_stage1_and_smoothing(df, inference_columns)

        file_disc_threshold, calib_summary = self._compute_adaptive_disc_threshold(
            df, smoothed_proba.copy(), feature_cols, patient_id, edf_id
        )

        smoothed_proba_final, surviving_events = self._cascade_phase10(
            df, rescaled_proba, smoothed_proba, feature_cols, file_disc_threshold, patient_id, edf_id
        )

        if _WINDOW_DURATION_COL in df.columns:
            mean_window_sec = float(df[_WINDOW_DURATION_COL].mean())
            if not np.isfinite(mean_window_sec) or mean_window_sec <= 0.0:
                mean_window_sec = _DEFAULT_WINDOW_DURATION_SEC
        else:
            mean_window_sec = _DEFAULT_WINDOW_DURATION_SEC

        elapsed = time.time() - t0

        clinical_alerts: List[Dict[str, Any]] = []
        for alert_id, ev in enumerate(surviving_events, start=1):
            start_w = int(ev["start_idx"])
            end_w   = int(ev["end_idx"])
            duration_sec = float((end_w - start_w + 1) * mean_window_sec)
            peak_proba   = float(ev.get("max_proba", 0.0))
            disc_conf    = float(ev.get("discriminator_seizure_proba", 0.0))

            clinical_alerts.append(
                {
                    "alert_id":                  alert_id,
                    "start_window_index":         start_w,
                    "end_window_index":           end_w,
                    "duration_seconds":           round(duration_sec, 4),
                    "peak_seizure_probability":   round(peak_proba, 4),
                    "discriminator_confidence":   round(disc_conf, 4),
                }
            )

        payload: Dict[str, Any] = {
            "status": "SUCCESS",
            "metadata": {
                "patient_id":               patient_id,
                "file_source":              edf_id,
                "total_windows_processed":  n_windows,
                "execution_time_seconds":   round(elapsed, 4),
            },
            "calibration_profile": {
                "baseline_mu":            round(calib_summary["mu_base"], 6),
                "baseline_sigma":         round(calib_summary["sigma_base"], 6),
                "computed_decision_gate": round(file_disc_threshold, 6),
            },
            "clinical_alerts_detected": clinical_alerts,
        }
        return payload

    def _discover_schema(self, parquet_path: str) -> Tuple[List[str], List[str]]:
        pf = pq.ParquetFile(parquet_path)
        schema_arrow = pf.schema_arrow
        all_columns  = [f.name for f in schema_arrow]

        meta_cols_present = [c for c in _META_COLS if c in all_columns]
        candidate_cols    = [c for c in all_columns if c not in _META_COLS]

        string_like_types = {"string", "large_string", "utf8", "large_utf8"}
        feature_cols: List[str] = []
        for c in candidate_cols:
            arrow_type = str(schema_arrow.field(c).type)
            if arrow_type in string_like_types:
                continue
            feature_cols.append(c)

        return feature_cols, meta_cols_present

    def _load_recording(
        self,
        parquet_path: str,
        feature_cols: List[str],
        meta_cols_present: List[str],
    ) -> pd.DataFrame:
        """Reads the entire parquet recording, applying global float32 casting
        on the base feature columns and string coercion for identifier cols."""
        path = Path(parquet_path)
        print(f"[neurovision_inference] Initializing chunked streaming for: {path.name}", file=sys.stderr)
        
        columns_to_read = list(dict.fromkeys(feature_cols + meta_cols_present))
        pf = pq.ParquetFile(parquet_path)

        frames: List[pd.DataFrame] = []
        for batch in pf.iter_batches(batch_size=50_000, columns=columns_to_read):
            df_chunk = batch.to_pandas()
            
            # Coerce data types strictly inside the chunk to optimize memory
            cols_to_cast_str = [c for c in meta_cols_present if c in df_chunk.columns]
            if cols_to_cast_str:
                df_chunk[cols_to_cast_str] = df_chunk[cols_to_cast_str].astype(str)
                
            cols_to_cast_float = [c for c in feature_cols if c in df_chunk.columns]
            if cols_to_cast_float:
                df_chunk[cols_to_cast_float] = df_chunk[cols_to_cast_float].fillna(0.0).astype(np.float32)
                
            frames.append(df_chunk)
            
        df = pd.concat(frames, ignore_index=True)
        del frames
        print(f"[neurovision_inference] Data loaded successfully. Shape: {df.shape}", file=sys.stderr)

        # Numeric coercion for label and timing metadata.
        if _LABEL_COL in df.columns:
            df[_LABEL_COL] = (
                pd.to_numeric(df[_LABEL_COL], errors="coerce").fillna(0).astype(np.int8)
            )
        if _WINDOW_DURATION_COL in df.columns:
            df[_WINDOW_DURATION_COL] = (
                pd.to_numeric(df[_WINDOW_DURATION_COL], errors="coerce")
                .fillna(_DEFAULT_WINDOW_DURATION_SEC)
                .astype(np.float32)
            )
        if _WINDOW_IDX_COL in df.columns:
            df[_WINDOW_IDX_COL] = (
                pd.to_numeric(df[_WINDOW_IDX_COL], errors="coerce")
                .fillna(-1)
                .astype(np.int64)
            )
        elif _WINDOW_INDEX_COL in df.columns:
            df[_WINDOW_INDEX_COL] = (
                pd.to_numeric(df[_WINDOW_INDEX_COL], errors="coerce")
                .fillna(-1)
                .astype(np.int64)
            )

        return df.reset_index(drop=True)

    def _resolve_inference_columns(self, discovered_feature_cols: List[str]) -> List[str]:
        native_features = getattr(self._base_model, "feature_names_in_", None)
        if native_features is not None:
            native_features = list(native_features)
            matched = [c for c in native_features if c in discovered_feature_cols]
            if len(matched) != len(native_features):
                missing = sorted(set(native_features) - set(discovered_feature_cols))
                raise ValueError(
                    f"Base model expects {len(native_features)} features but only {len(matched)} present. Missing: {missing}"
                )
            return native_features
        return sorted(discovered_feature_cols, key=_natural_sort_key)

    def _run_stage1_and_smoothing(
        self,
        df: pd.DataFrame,
        inference_columns: List[str],
    ) -> Tuple[np.ndarray, np.ndarray]:
        X_inference = df.reindex(columns=inference_columns)
        for c in inference_columns:
            if not is_numeric_dtype(X_inference[c]):
                X_inference[c] = pd.to_numeric(X_inference[c], errors="coerce")
        X_inference = X_inference.fillna(0.0).astype(np.float32)

        raw_proba = self._base_model.predict_proba(X_inference.values)
        if raw_proba.ndim == 2 and raw_proba.shape[1] >= 2:
            raw_proba = raw_proba[:, 1]
        else:
            raw_proba = raw_proba.ravel()

        p_mean = float(np.mean(raw_proba))
        p_std  = float(max(np.std(raw_proba), 1e-6))
        z_scores       = (raw_proba - p_mean) / p_std
        rescaled_proba = 1.0 / (1.0 + np.exp(-0.5 * z_scores))
        smoothed_proba = _smooth_probabilities(rescaled_proba, int(float(_SMOOTH_WINDOW)))

        return rescaled_proba, smoothed_proba

    def _compute_adaptive_disc_threshold(
        self,
        df: pd.DataFrame,
        smoothed_proba_full: np.ndarray,
        feature_cols: List[str],
        patient_id: str,
        edf_id: str,
    ) -> Tuple[float, Dict[str, Any]]:
        n_total  = len(df)
        calib_n  = min(_CALIBRATION_WINDOW_COUNT, n_total)
        calib_df = df.iloc[:calib_n].reset_index(drop=True)
        calib_sp = smoothed_proba_full[:calib_n]

        mu_base             = 0.0
        sigma_base          = 0.0
        n_calibration_events = 0

        if calib_n > 0:
            calib_flags  = _compute_adaptive_gate_and_flags(calib_sp)
            calib_events = _group_windows_into_events(calib_flags, int(float(_GAP_TOLERANCE)))

            if calib_events:
                calib_pseudo = _build_pseudo_events(calib_events, calib_sp, patient_id, edf_id)
                calib_disc_proba = _score_events_with_discriminator(
                    calib_df, calib_pseudo, feature_cols, _EVENT_AGG_STATS,
                    self._discriminator, self._disc_scaler,
                )
                if calib_disc_proba.size > 0:
                    mu_base               = float(np.mean(calib_disc_proba))
                    sigma_base            = float(np.std(calib_disc_proba))
                    n_calibration_events  = int(calib_disc_proba.size)

        file_disc_threshold = max(
            float(_DISC_THRESHOLD_FLOOR),
            mu_base + (float(_CALIBRATION_SIGMA_MULTIPLIER) * sigma_base),
        )

        calibration_summary = {
            "patient":                   patient_id,
            "edf":                       edf_id,
            "calibration_windows_used":  calib_n,
            "n_calibration_events":      n_calibration_events,
            "mu_base":                   mu_base,
            "sigma_base":                sigma_base,
            "file_disc_threshold":       file_disc_threshold,
        }
        return file_disc_threshold, calibration_summary

    def _cascade_phase10(
        self,
        df: pd.DataFrame,
        rescaled_proba: np.ndarray,
        smoothed_proba: np.ndarray,
        feature_cols: List[str],
        file_disc_threshold: float,
        patient_id: str,
        edf_id: str,
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        gap_tolerance = int(float(_GAP_TOLERANCE))

        flags            = _compute_adaptive_gate_and_flags(smoothed_proba)
        candidate_events = _group_windows_into_events(flags, gap_tolerance)

        if not candidate_events:
            return smoothed_proba, []

        pseudo_events = _build_pseudo_events(candidate_events, smoothed_proba, patient_id, edf_id)
        disc_proba = _score_events_with_discriminator(
            df, pseudo_events, feature_cols, _EVENT_AGG_STATS,
            self._discriminator, self._disc_scaler,
        )

        stage2_accepted: List[Dict[str, Any]] = []
        for idx, ev in enumerate(pseudo_events):
            ev["discriminator_seizure_proba"] = float(disc_proba[idx])
            if disc_proba[idx] >= file_disc_threshold:
                stage2_accepted.append(ev)

        duration_passed, _duration_rejected = _apply_temporal_persistence_filter(
            stage2_accepted, smoothed_proba, _MIN_DURATION_WINDOWS
        )

        surviving_events = _consolidate_adjacent_events(duration_passed, _CONSOLIDATION_GAP_WINDOWS)
        return smoothed_proba, surviving_events

    @staticmethod
    def _load_artifact(path: str) -> Any:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")
        try:
            return joblib.load(str(p))
        except Exception:
            with open(str(p), "rb") as fh:
                return pickle.load(fh)


# ==============================================================================
# CLI HANDLER
# ==============================================================================

def _build_cli_parser():
    import argparse
    parser = argparse.ArgumentParser(
        prog="neurovision_inference",
        description="NeuroVision AI – Phase 10 Production Inference Engine.",
    )
    parser.add_argument("parquet_path", metavar="PARQUET_FILE")
    parser.add_argument("--base-model", required=True, metavar="PATH")
    parser.add_argument("--discriminator", required=True, metavar="PATH")
    parser.add_argument("--scaler", required=True, metavar="PATH")
    parser.add_argument("--output", metavar="PATH", default=None)
    return parser


def main() -> int:
    parser = _build_cli_parser()
    args   = parser.parse_args()

    engine = NeuroVisionEngine(
        base_model_path=args.base_model,
        discriminator_path=args.discriminator,
        discriminator_scaler_path=args.scaler,
    )

    json_payload = engine.process_file(args.parquet_path)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_payload, encoding="utf-8")
        print(f"[neurovision_inference] Payload written to {out_path}", file=sys.stderr)
    else:
        print(json_payload)

    try:
        status = json.loads(json_payload).get("status", "ERROR")
    except Exception:
        status = "ERROR"

    return 0 if status == "SUCCESS" else 1


if __name__ == "__main__":
    sys.exit(main())
