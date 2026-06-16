#!/usr/bin/env python3
# ======================================================================
# PHASE5D_FAILURE_ANALYSIS.py
#
# Forensic root-cause investigation of Phase5C false-negative seizure
# events for the NeuroVision temporal seizure-detection pipeline.
#
# This script:
#   - Dynamically discovers schema from PHASE5B_FEATURE_SIGNATURE.json,
#     PHASE5B_PATIENT_SPLIT.json, and PHASE5B_ENGINEERED_DATASET.parquet.
#   - Loads PHASE5B_TEMPORAL_XGBOOST.joblib and regenerates per-window
#     probabilities on the Phase5B test patients.
#   - Reconstructs ground-truth seizure events directly from contiguous
#     label==1 windows (no hardcoded annotations).
#   - Replicates the Phase5C calibration / smoothing / aggregation /
#     suppression / matching pipeline to identify false-negative events.
#   - Performs probability, threshold, smoothing, duration, and
#     peak-probability forensics on every false-negative event.
#   - Performs patient-level failure analysis (with dedicated sections
#     for chb02, chb14, chb22) and patient-shift analysis against
#     successful patients (chb05, chb09).
#   - Classifies every false-negative event by root cause with evidence.
#   - Writes a full audit trail, schema audit, runtime audit, and
#     execution report answering the mandated forensic questions.
#
# No hardcoded schema. No placeholders. No TODOs.
# ======================================================================

import os
import sys
import json
import gc
import hashlib
import platform
import time
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional, Any

import numpy as np
import pandas as pd

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

try:
    from sklearn.isotonic import IsotonicRegression
    from sklearn.calibration import calibration_curve
    _SKLEARN_VERSION = __import__("sklearn").__version__
except ImportError as e:
    raise RuntimeError(
        "scikit-learn is required for isotonic calibration replication "
        f"(needed to match Phase5C behaviour). Import error: {e}"
    )

try:
    import joblib
    _JOBLIB_VERSION = joblib.__version__
except ImportError as e:
    raise RuntimeError(f"joblib is required to load the trained model. Import error: {e}")

try:
    import xgboost
    _XGBOOST_VERSION = xgboost.__version__
except ImportError:
    _XGBOOST_VERSION = "not_installed"


# ----------------------------------------------------------------------
# Constants — replicated from train_phase5c_temporal_event_detection.py
# so forensic re-evaluation matches the production pipeline exactly.
# These are PIPELINE CONFIGURATION CONSTANTS, not data-schema assumptions.
# ----------------------------------------------------------------------
SMOOTHING_WINDOWS = [3, 5, 7, 11, 21]
SMOOTHED_PROB_COLUMNS = [
    "smoothed_prob_3",
    "smoothed_prob_5",
    "smoothed_prob_7",
    "smoothed_prob_11",
    "smoothed_prob_21",
]

THRESHOLD_SWEEP = [
    0.99, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55,
    0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20, 0.15, 0.10, 0.05, 0.01,
]

PROBABILITY_FRACTION_THRESHOLDS = [
    0.01, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50,
    0.60, 0.70, 0.80, 0.90, 0.95, 0.99,
]

SMOOTHING_FORENSICS_WINDOWS = [0, 3, 5, 7, 11, 15, 21, 31, 41]  # 0 = no smoothing

MIN_DURATION_SWEEP = [1, 2, 3, 5, 7, 10, 15, 20, 25, 30]

PEAK_FILTER_SWEEP = [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99]

CALIBRATION_FRACTION_FALLBACK = 0.2
MIN_CALIBRATION_PATIENTS = 1

DEDICATED_PATIENTS = ["chb02", "chb14", "chb22"]
SUCCESSFUL_PATIENTS = ["chb05", "chb09"]

REQUIRED_METADATA_CONCEPTS = {
    "label": ["label"],
    "patient": ["patient"],
    "edf": ["edf"],
    "window_index": ["window_index"],
}
OPTIONAL_METADATA_CONCEPTS = {
    "window_uid": ["window_uid"],
    "window_start_sec": ["window_start_sec"],
    "window_end_sec": ["window_end_sec"],
    "window_duration_sec": ["window_duration_sec"],
    "stride_sec": ["stride_sec"],
}

# ----------------------------------------------------------------------
# Input file locations (script runs in same directory as artifacts)
# ----------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_FILES = {
    "feature_signature": "PHASE5B_FEATURE_SIGNATURE.json",
    "patient_split": "PHASE5B_PATIENT_SPLIT.json",
    "metrics_5b": "PHASE5B_METRICS.json",
    "threshold_sweep_5b": "PHASE5B_THRESHOLD_SWEEP.csv",
    "feature_importance_5b": "PHASE5B_FEATURE_IMPORTANCE.csv",
    "model": "PHASE5B_TEMPORAL_XGBOOST.joblib",
    "dataset": "PHASE5B_ENGINEERED_DATASET.parquet",
    "event_predictions_5c": "PHASE5C_EVENT_PREDICTIONS.csv",
    "event_metrics_5c": "PHASE5C_EVENT_METRICS.csv",
    "configuration_search_5c": "PHASE5C_CONFIGURATION_SEARCH.csv",
    "best_configuration_5c": "PHASE5C_BEST_CONFIGURATION.json",
    "patient_event_summary_5c": "PHASE5C_PATIENT_EVENT_SUMMARY.csv",
    "schema_audit_5c": "PHASE5C_SCHEMA_AUDIT.json",
    "runtime_audit_5c": "PHASE5C_RUNTIME_AUDIT.json",
    "execution_report_5c": "PHASE5C_EXECUTION_REPORT.txt",
}

OUTPUT_FILES = {
    "false_negative_events": "PHASE5D_FALSE_NEGATIVE_EVENTS.csv",
    "threshold_forensics": "PHASE5D_THRESHOLD_FORENSICS.csv",
    "smoothing_forensics": "PHASE5D_SMOOTHING_FORENSICS.csv",
    "duration_forensics": "PHASE5D_DURATION_FORENSICS.csv",
    "peak_forensics": "PHASE5D_PEAK_FORENSICS.csv",
    "patient_failure_summary": "PHASE5D_PATIENT_FAILURE_SUMMARY.csv",
    "root_cause_analysis": "PHASE5D_ROOT_CAUSE_ANALYSIS.csv",
    "patient_shift_analysis": "PHASE5D_PATIENT_SHIFT_ANALYSIS.csv",
    "schema_audit": "PHASE5D_SCHEMA_AUDIT.json",
    "runtime_audit": "PHASE5D_RUNTIME_AUDIT.json",
    "execution_report": "PHASE5D_EXECUTION_REPORT.txt",
}


# ======================================================================
# Utility: logging
# ======================================================================
def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    print(f"[{ts}] {msg}", flush=True)


def get_process_memory_mb() -> float:
    if _HAS_PSUTIL:
        try:
            proc = psutil.Process(os.getpid())
            return round(proc.memory_info().rss / (1024 * 1024), 2)
        except Exception:
            return float("nan")
    return float("nan")


def file_sha256(path: str, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_path(key: str) -> str:
    path = os.path.join(BASE_DIR, INPUT_FILES[key])
    if not os.path.exists(path):
        raise RuntimeError(
            f"ABSOLUTE REQUIREMENT #1/#2 VIOLATION: required input file "
            f"'{INPUT_FILES[key]}' (key='{key}') does not exist at expected "
            f"path '{path}'. Cannot proceed without schema discovery from "
            f"this artifact."
        )
    return path


# ======================================================================
# STEP 0: Schema discovery
# ======================================================================
class SchemaAudit:
    def __init__(self):
        self.audit: Dict[str, Any] = {
            "file_existence": {},
            "feature_signature": {},
            "patient_split": {},
            "dataset_columns": {},
            "model": {},
            "event_predictions_schema": {},
            "configuration_search_schema": {},
            "metadata_column_resolution": {},
            "overall_passed": False,
            "errors": [],
        }

    def record_error(self, msg: str):
        self.audit["errors"].append(msg)

    def finalize(self, passed: bool):
        self.audit["overall_passed"] = passed


def discover_feature_signature(audit: SchemaAudit) -> Tuple[List[str], int]:
    path = resolve_path("feature_signature")
    with open(path, "r") as f:
        sig = json.load(f)

    if "feature_names" not in sig or "feature_count" not in sig:
        raise RuntimeError(
            "ABSOLUTE REQUIREMENT #1 VIOLATION: PHASE5B_FEATURE_SIGNATURE.json "
            "does not contain expected keys 'feature_names' and 'feature_count'. "
            f"Found keys: {list(sig.keys())}"
        )

    feature_names = list(sig["feature_names"])
    feature_count = int(sig["feature_count"])

    if len(feature_names) != feature_count:
        raise RuntimeError(
            f"SCHEMA INCONSISTENCY: feature_signature declares feature_count="
            f"{feature_count} but feature_names has {len(feature_names)} entries."
        )

    audit.audit["feature_signature"] = {
        "path": INPUT_FILES["feature_signature"],
        "exists": True,
        "feature_count": feature_count,
        "feature_names_length": len(feature_names),
        "passed": len(feature_names) == feature_count,
    }
    audit.audit["file_existence"]["feature_signature"] = {
        "path": INPUT_FILES["feature_signature"], "exists": True,
    }
    return feature_names, feature_count


def discover_patient_split(audit: SchemaAudit) -> Dict[str, Any]:
    path = resolve_path("patient_split")
    with open(path, "r") as f:
        split = json.load(f)

    required_keys = ["train_patients", "test_patients"]
    missing = [k for k in required_keys if k not in split]
    if missing:
        raise RuntimeError(
            f"ABSOLUTE REQUIREMENT #1 VIOLATION: PHASE5B_PATIENT_SPLIT.json "
            f"missing required keys: {missing}. Found keys: {list(split.keys())}"
        )

    if not split["test_patients"]:
        raise RuntimeError(
            "PHASE5B_PATIENT_SPLIT.json has an empty 'test_patients' list. "
            "Cannot perform forensic analysis without test patients."
        )

    audit.audit["patient_split"] = {
        "path": INPUT_FILES["patient_split"],
        "exists": True,
        "test_patients": split["test_patients"],
        "test_patient_count": len(split["test_patients"]),
        "train_patient_count": len(split.get("train_patients", [])),
        "calibration_patients_provided": "calibration_patients" in split
        and bool(split["calibration_patients"]),
        "calibration_patient_count": len(split.get("calibration_patients", [])),
        "passed": True,
    }
    audit.audit["file_existence"]["patient_split"] = {
        "path": INPUT_FILES["patient_split"], "exists": True,
    }
    return split


def resolve_metadata_columns(
    dataset_columns: List[str], audit: SchemaAudit
) -> Dict[str, Optional[str]]:
    """
    Resolve required and optional metadata column concepts against the
    actual dataset columns. Raises RuntimeError if a REQUIRED concept
    cannot be resolved.
    """
    resolution: Dict[str, Optional[str]] = {}
    col_set = set(dataset_columns)

    missing_required = []
    for concept, candidates in REQUIRED_METADATA_CONCEPTS.items():
        found = next((c for c in candidates if c in col_set), None)
        resolution[concept] = found
        if found is None:
            missing_required.append((concept, candidates))

    if missing_required:
        raise RuntimeError(
            "ABSOLUTE REQUIREMENT #1 VIOLATION: could not resolve required "
            f"metadata concepts in PHASE5B_ENGINEERED_DATASET.parquet columns. "
            f"Unresolved concepts (concept -> candidate names tried): "
            f"{missing_required}. Available columns sample: "
            f"{sorted(dataset_columns)[:30]}"
        )

    for concept, candidates in OPTIONAL_METADATA_CONCEPTS.items():
        found = next((c for c in candidates if c in col_set), None)
        resolution[concept] = found

    audit.audit["metadata_column_resolution"] = resolution
    return resolution


def discover_dataset_schema(
    feature_names: List[str], audit: SchemaAudit
) -> Tuple[List[str], Dict[str, Optional[str]]]:
    path = resolve_path("dataset")

    try:
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(path)
        dataset_columns = [f.name for f in pf.schema_arrow]
        total_rows = pf.metadata.num_rows
    except Exception:
        # Fallback: read only the schema via pandas (may be slower)
        meta = pd.read_parquet(path)
        dataset_columns = list(meta.columns)
        total_rows = len(meta)
        del meta
        gc.collect()

    missing_features = [f for f in feature_names if f not in dataset_columns]
    if missing_features:
        raise RuntimeError(
            f"SCHEMA VALIDATION FAILED: dataset is missing "
            f"{len(missing_features)} canonical model features declared in "
            f"PHASE5B_FEATURE_SIGNATURE.json. First 5 missing: "
            f"{missing_features[:5]}"
        )

    metadata_resolution = resolve_metadata_columns(dataset_columns, audit)

    audit.audit["dataset_columns"] = {
        "path": INPUT_FILES["dataset"],
        "total_columns_in_dataset": len(dataset_columns),
        "total_rows_in_dataset": int(total_rows),
        "feature_count_matches": len(missing_features) == 0,
        "feature_columns_present": len(missing_features) == 0,
        "passed": len(missing_features) == 0,
    }
    audit.audit["file_existence"]["dataset"] = {
        "path": INPUT_FILES["dataset"], "exists": True,
    }
    return dataset_columns, metadata_resolution


def discover_model(feature_names: List[str], audit: SchemaAudit):
    path = resolve_path("model")
    model = joblib.load(path)

    if not hasattr(model, "predict_proba"):
        raise RuntimeError(
            "ABSOLUTE REQUIREMENT #1 VIOLATION: loaded model object from "
            "PHASE5B_TEMPORAL_XGBOOST.joblib does not implement predict_proba()."
        )

    n_features_in = getattr(model, "n_features_in_", None)
    if n_features_in is not None and int(n_features_in) != len(feature_names):
        raise RuntimeError(
            f"SCHEMA INCONSISTENCY: model.n_features_in_={n_features_in} but "
            f"PHASE5B_FEATURE_SIGNATURE.json declares {len(feature_names)} "
            f"features."
        )

    feature_names_in = getattr(model, "feature_names_in_", None)
    feature_order_matches = True
    if feature_names_in is not None:
        feature_order_matches = list(feature_names_in) == list(feature_names)
        if not feature_order_matches:
            log(
                "[WARNING] Model feature_names_in_ does not match "
                "PHASE5B_FEATURE_SIGNATURE.json order. The feature matrix "
                "will be built using PHASE5B_FEATURE_SIGNATURE.json order "
                "(this matches the documented Phase5C contract: "
                "'Feature Order Check: explicit element-wise comparison')."
            )

    audit.audit["model"] = {
        "path": INPUT_FILES["model"],
        "type": str(type(model)),
        "has_predict_proba": True,
        "n_features_in": int(n_features_in) if n_features_in is not None else None,
        "feature_order_matches_signature": feature_order_matches,
        "passed": True,
    }
    audit.audit["file_existence"]["model"] = {
        "path": INPUT_FILES["model"], "exists": True,
    }
    return model


def discover_event_predictions_schema(audit: SchemaAudit) -> List[str]:
    path = resolve_path("event_predictions_5c")
    df = pd.read_csv(path, nrows=5)
    columns = list(df.columns)

    required_concepts = {
        "patient": ["patient"],
        "edf": ["edf"],
        "event_start_window": ["event_start_window"],
        "event_end_window": ["event_end_window"],
        "is_true_event": ["is_true_event"],
    }
    missing = []
    for concept, candidates in required_concepts.items():
        if not any(c in columns for c in candidates):
            missing.append((concept, candidates))
    if missing:
        raise RuntimeError(
            f"ABSOLUTE REQUIREMENT #1 VIOLATION: PHASE5C_EVENT_PREDICTIONS.csv "
            f"missing required concepts: {missing}. Found columns: {columns}"
        )

    audit.audit["event_predictions_schema"] = {
        "path": INPUT_FILES["event_predictions_5c"],
        "columns": columns,
        "passed": True,
    }
    audit.audit["file_existence"]["event_predictions_5c"] = {
        "path": INPUT_FILES["event_predictions_5c"], "exists": True,
    }
    return columns


def discover_configuration_search_schema(audit: SchemaAudit) -> List[str]:
    path = resolve_path("configuration_search_5c")
    df = pd.read_csv(path, nrows=5)
    columns = list(df.columns)

    required = [
        "smoothing_window", "threshold", "min_duration",
        "min_peak_probability", "false_negative_events",
    ]
    missing = [c for c in required if c not in columns]
    if missing:
        raise RuntimeError(
            f"ABSOLUTE REQUIREMENT #1 VIOLATION: PHASE5C_CONFIGURATION_SEARCH.csv "
            f"missing required columns: {missing}. Found columns: {columns}"
        )

    audit.audit["configuration_search_schema"] = {
        "path": INPUT_FILES["configuration_search_5c"],
        "columns": columns,
        "passed": True,
    }
    audit.audit["file_existence"]["configuration_search_5c"] = {
        "path": INPUT_FILES["configuration_search_5c"], "exists": True,
    }
    return columns


# ======================================================================
# STEP 1: Load engineered dataset for test patients (and calibration set)
# ======================================================================
def load_parquet_filtered(
    parquet_path: str, columns: List[str], patients: List[str]
) -> pd.DataFrame:
    patient_set = set(patients)
    try:
        df = pd.read_parquet(
            parquet_path, columns=columns, filters=[("patient", "in", patients)]
        )
        log(f"[ParquetLoader] filters= pushdown succeeded — {len(df)} rows loaded.")
        return df
    except Exception as e:
        log(f"[ParquetLoader] filters= pushdown failed ({e}); trying pyarrow.dataset scan...")

    try:
        import pyarrow.dataset as ds
        import pyarrow as pa

        dataset = ds.dataset(parquet_path, format="parquet")
        filter_expr = ds.field("patient").isin(list(patient_set))
        batches = []
        for batch in dataset.to_batches(columns=columns, filter=filter_expr):
            if batch.num_rows == 0:
                continue
            batches.append(batch)
        if batches:
            table = pa.Table.from_batches(batches)
            df = table.to_pandas()
        else:
            df = pd.DataFrame(columns=columns)
        log(f"[ParquetLoader] pyarrow.dataset scan succeeded — {len(df)} rows loaded.")
        return df
    except Exception as e:
        log(f"[ParquetLoader] pyarrow.dataset scan failed ({e}); falling back to full read.")

    df_full = pd.read_parquet(parquet_path, columns=columns)
    df = df_full[df_full["patient"].isin(patient_set)].copy()
    del df_full
    gc.collect()
    log(f"[ParquetLoader] full-read fallback complete — {len(df)} rows retained.")
    return df


def select_calibration_patients(
    split: Dict, train_patients: List[str]
) -> Tuple[List[str], str]:
    explicit_cal = split.get("calibration_patients", [])
    if explicit_cal:
        return list(explicit_cal), "explicit_split_file"

    if not train_patients:
        return [], "none_available"

    sorted_train = sorted(train_patients)
    n_cal = max(
        MIN_CALIBRATION_PATIENTS,
        int(round(len(sorted_train) * CALIBRATION_FRACTION_FALLBACK)),
    )
    n_cal = min(n_cal, len(sorted_train) - 1) if len(sorted_train) > 1 else len(sorted_train)
    n_cal = max(n_cal, 0)
    return sorted_train[:n_cal], "fallback_carveout"


# ======================================================================
# STEP 2: Ground-truth event reconstruction (contiguous label==1 runs)
# ======================================================================
def build_ground_truth_events(
    df: pd.DataFrame, meta_cols: Dict[str, Optional[str]]
) -> pd.DataFrame:
    label_col = meta_cols["label"]
    patient_col = meta_cols["patient"]
    edf_col = meta_cols["edf"]
    win_col = meta_cols["window_index"]
    start_sec_col = meta_cols.get("window_start_sec")
    end_sec_col = meta_cols.get("window_end_sec")

    df_sorted = df.sort_values([patient_col, edf_col, win_col]).reset_index(drop=True)

    patients = df_sorted[patient_col].values
    edfs = df_sorted[edf_col].values
    window_indices = df_sorted[win_col].values
    labels = df_sorted[label_col].values
    starts = df_sorted[start_sec_col].values if start_sec_col else None
    ends = df_sorted[end_sec_col].values if end_sec_col else None

    gt_events = []
    group_keys = df_sorted[[patient_col, edf_col]].drop_duplicates().values

    for patient, edf in group_keys:
        mask = (patients == patient) & (edfs == edf)
        idxs = np.where(mask)[0]
        edf_win = window_indices[idxs]
        edf_label = labels[idxs]
        edf_starts = starts[idxs] if starts is not None else None
        edf_ends = ends[idxs] if ends is not None else None

        in_event = False
        event_start_local = None

        for local_i in range(len(edf_label)):
            if edf_label[local_i] == 1 and not in_event:
                in_event = True
                event_start_local = local_i
            elif edf_label[local_i] == 0 and in_event:
                end_local = local_i - 1
                gt_events.append(
                    _build_gt_event(
                        patient, edf, edf_win, edf_starts, edf_ends,
                        event_start_local, end_local,
                    )
                )
                in_event = False
                event_start_local = None

        if in_event:
            end_local = len(edf_label) - 1
            gt_events.append(
                _build_gt_event(
                    patient, edf, edf_win, edf_starts, edf_ends,
                    event_start_local, end_local,
                )
            )

    if not gt_events:
        return pd.DataFrame(
            columns=[
                "patient", "edf", "gt_event_id", "gt_start_window",
                "gt_end_window", "gt_start_sec", "gt_end_sec",
                "gt_duration_sec", "number_of_positive_windows",
            ]
        )

    gt_df = pd.DataFrame(gt_events)
    gt_df["gt_event_id"] = (
        gt_df["patient"] + "::" + gt_df["edf"] + "::"
        + gt_df["gt_start_window"].astype(str) + "-" + gt_df["gt_end_window"].astype(str)
    )
    return gt_df


def _build_gt_event(
    patient, edf, edf_win, edf_starts, edf_ends, start_local, end_local
) -> Dict[str, Any]:
    win_slice = edf_win[start_local:end_local + 1]
    n_pos = int(len(win_slice))
    event = {
        "patient": patient,
        "edf": edf,
        "gt_start_window": int(win_slice[0]),
        "gt_end_window": int(win_slice[-1]),
        "number_of_positive_windows": n_pos,
    }
    if edf_starts is not None and edf_ends is not None:
        start_sec = float(edf_starts[start_local])
        end_sec = float(edf_ends[end_local])
        event["gt_start_sec"] = start_sec
        event["gt_end_sec"] = end_sec
        event["gt_duration_sec"] = round(end_sec - start_sec, 6)
    else:
        event["gt_start_sec"] = np.nan
        event["gt_end_sec"] = np.nan
        event["gt_duration_sec"] = np.nan
    return event


# ======================================================================
# STEP 3: Temporal smoothing (replicates TemporalSmoothingEngine)
# ======================================================================
def apply_smoothing(
    df: pd.DataFrame, meta_cols: Dict[str, Optional[str]]
) -> pd.DataFrame:
    patient_col = meta_cols["patient"]
    edf_col = meta_cols["edf"]
    win_col = meta_cols["window_index"]

    df = df.sort_values([patient_col, edf_col, win_col]).reset_index(drop=True)

    for win, col in zip(SMOOTHING_WINDOWS, SMOOTHED_PROB_COLUMNS):
        smoothed = (
            df.groupby([patient_col, edf_col], sort=False)["pred_proba"]
            .transform(lambda x, w=win: x.rolling(window=w, min_periods=1, center=True).mean())
            .astype(np.float32)
        )
        nan_mask = smoothed.isna()
        if nan_mask.any():
            smoothed = smoothed.fillna(df["pred_proba"])
        df[col] = smoothed

    # smoothed_prob_0 == raw pred_proba (no smoothing), for forensic uniformity
    df["smoothed_prob_0"] = df["pred_proba"].astype(np.float32)

    # Additional forensic-only smoothing windows not in SMOOTHING_WINDOWS
    for win in SMOOTHING_FORENSICS_WINDOWS:
        col = f"smoothed_prob_{win}"
        if col in df.columns:
            continue
        if win == 0:
            continue
        smoothed = (
            df.groupby([patient_col, edf_col], sort=False)["pred_proba"]
            .transform(lambda x, w=win: x.rolling(window=w, min_periods=1, center=True).mean())
            .astype(np.float32)
        )
        nan_mask = smoothed.isna()
        if nan_mask.any():
            smoothed = smoothed.fillna(df["pred_proba"])
        df[col] = smoothed

    return df


# ======================================================================
# STEP 4: Event aggregation (replicates EventAggregator) + suppression
# ======================================================================
def aggregate_events(
    df: pd.DataFrame, meta_cols: Dict[str, Optional[str]], smoothed_col: str, threshold: float
) -> pd.DataFrame:
    patient_col = meta_cols["patient"]
    edf_col = meta_cols["edf"]
    win_col = meta_cols["window_index"]
    label_col = meta_cols["label"]

    positive_mask = (df[smoothed_col] >= threshold).values
    patients = df[patient_col].values
    edfs = df[edf_col].values
    window_indices = df[win_col].values
    probas = df[smoothed_col].values
    labels = df[label_col].values

    group_keys = df[[patient_col, edf_col]].drop_duplicates().values
    idx_map = {
        (p, e): np.where((patients == p) & (edfs == e))[0]
        for p, e in group_keys
    }

    events = []
    for (patient, edf), row_indices in idx_map.items():
        edf_pos = positive_mask[row_indices]
        edf_proba = probas[row_indices]
        edf_win = window_indices[row_indices]
        edf_label = labels[row_indices]

        in_event = False
        event_start_idx = None

        for local_i in range(len(edf_pos)):
            if edf_pos[local_i] and not in_event:
                in_event = True
                event_start_idx = local_i
            elif not edf_pos[local_i] and in_event:
                end_idx = local_i - 1
                events.append(_build_pred_event(
                    patient, edf, edf_win, edf_proba, edf_label, event_start_idx, end_idx
                ))
                in_event = False
                event_start_idx = None

        if in_event:
            end_idx = len(edf_pos) - 1
            events.append(_build_pred_event(
                patient, edf, edf_win, edf_proba, edf_label, event_start_idx, end_idx
            ))

    if not events:
        return pd.DataFrame(columns=[
            "patient", "edf", "event_start_window", "event_end_window",
            "duration_windows", "peak_probability", "mean_probability",
            "positive_window_count", "is_true_event",
        ])
    return pd.DataFrame(events)


def _build_pred_event(patient, edf, edf_win, edf_proba, edf_label, start_idx, end_idx) -> Dict:
    win_slice = edf_win[start_idx:end_idx + 1]
    prob_slice = edf_proba[start_idx:end_idx + 1]
    label_slice = edf_label[start_idx:end_idx + 1]
    return {
        "patient": patient,
        "edf": edf,
        "event_start_window": int(win_slice[0]),
        "event_end_window": int(win_slice[-1]),
        "duration_windows": int(len(win_slice)),
        "peak_probability": float(prob_slice.max()),
        "mean_probability": float(prob_slice.mean()),
        "positive_window_count": int(len(win_slice)),
        "is_true_event": int(label_slice.max() == 1),
    }


def suppress_events(
    events_df: pd.DataFrame, min_duration: int, min_peak_prob: float
) -> pd.DataFrame:
    if events_df.empty:
        return events_df
    keep_mask = (
        (events_df["duration_windows"] >= min_duration)
        & (events_df["peak_probability"] >= min_peak_prob)
    )
    return events_df[keep_mask].reset_index(drop=True)


# ======================================================================
# STEP 5: Event matching (overlap-based 1-to-1, optimal via Kuhn's algo)
# ======================================================================
def _overlaps(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    return a[0] <= b[1] and a[1] >= b[0]


def match_events_for_gt(
    gt_row: pd.Series, predicted_events: pd.DataFrame
) -> bool:
    """Returns True if this single GT event overlaps with ANY predicted event
    in the same (patient, edf) — i.e. whether it would be a candidate TP
    (subject to 1-to-1 constraints in the full pipeline, but for FN
    determination at the per-event level, overlap existence is the
    relevant forensic signal)."""
    if predicted_events.empty:
        return False
    same_group = predicted_events[
        (predicted_events["patient"] == gt_row["patient"])
        & (predicted_events["edf"] == gt_row["edf"])
    ]
    if same_group.empty:
        return False
    gt_interval = (int(gt_row["gt_start_window"]), int(gt_row["gt_end_window"]))
    for _, pred in same_group.iterrows():
        pred_interval = (int(pred["event_start_window"]), int(pred["event_end_window"]))
        if _overlaps(pred_interval, gt_interval):
            return True
    return False


def full_pipeline_matched_gt_ids(
    df: pd.DataFrame,
    meta_cols: Dict[str, Optional[str]],
    gt_events: pd.DataFrame,
    smoothing_window: int,
    threshold: float,
    min_duration: int,
    min_peak_prob: float,
) -> set:
    """
    Replicates the full Phase5C pipeline (smoothing -> aggregation ->
    suppression -> matching) for a given configuration and returns the
    set of gt_event_id values that are matched (TP) under strict 1-to-1
    overlap matching (optimal bipartite within each (patient, edf) group,
    matching the 'auto' strategy for small groups which dominates here).
    """
    if smoothing_window == 0:
        smoothed_col = "smoothed_prob_0"
    else:
        smoothed_col = f"smoothed_prob_{smoothing_window}"
        if smoothed_col not in df.columns:
            raise RuntimeError(
                f"Smoothing column '{smoothed_col}' not found — smoothing "
                f"window {smoothing_window} was not precomputed."
            )

    pred_events = aggregate_events(df, meta_cols, smoothed_col, threshold)
    pred_events = suppress_events(pred_events, min_duration, min_peak_prob)

    matched_ids = set()
    if gt_events.empty:
        return matched_ids

    group_keys = set(zip(gt_events["patient"], gt_events["edf"])) | (
        set(zip(pred_events["patient"], pred_events["edf"])) if not pred_events.empty else set()
    )

    for patient, edf in group_keys:
        gts_in_group = gt_events[(gt_events["patient"] == patient) & (gt_events["edf"] == edf)]
        if gts_in_group.empty:
            continue
        if pred_events.empty:
            continue
        preds_in_group = pred_events[(pred_events["patient"] == patient) & (pred_events["edf"] == edf)]
        if preds_in_group.empty:
            continue

        gt_intervals = list(zip(gts_in_group["gt_start_window"], gts_in_group["gt_end_window"]))
        gt_ids = list(gts_in_group["gt_event_id"])
        pred_intervals = list(zip(preds_in_group["event_start_window"], preds_in_group["event_end_window"]))

        adjacency: List[List[int]] = []
        for pred in pred_intervals:
            overlaps = [gi for gi, gt in enumerate(gt_intervals) if _overlaps(pred, gt)]
            adjacency.append(overlaps)

        match_gt_to_pred = [-1] * len(gt_intervals)

        def try_kuhn(pi, visited):
            for gi in adjacency[pi]:
                if visited[gi]:
                    continue
                visited[gi] = True
                if match_gt_to_pred[gi] == -1 or try_kuhn(match_gt_to_pred[gi], visited):
                    match_gt_to_pred[gi] = pi
                    return True
            return False

        for pi in range(len(pred_intervals)):
            visited = [False] * len(gt_intervals)
            try_kuhn(pi, visited)

        for gi, pi in enumerate(match_gt_to_pred):
            if pi != -1:
                matched_ids.add(gt_ids[gi])

    return matched_ids


# ======================================================================
# STEP 6: Probability forensics per FN event
# ======================================================================
def probability_forensics_for_event(
    window_probas: np.ndarray, window_secs: Optional[np.ndarray]
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    n = len(window_probas)
    result["window_count"] = int(n)
    if n == 0:
        for k in [
            "max_probability", "min_probability", "mean_probability",
            "median_probability", "std_probability", "variance_probability",
            "p95_probability", "p99_probability", "probability_range",
            "area_under_probability_curve", "max_consecutive_positive_windows_above_0_5",
        ]:
            result[k] = np.nan
        for frac_thresh in PROBABILITY_FRACTION_THRESHOLDS:
            result[f"fraction_windows_above_{frac_thresh}"] = np.nan
        return result

    result["max_probability"] = float(np.max(window_probas))
    result["min_probability"] = float(np.min(window_probas))
    result["mean_probability"] = float(np.mean(window_probas))
    result["median_probability"] = float(np.median(window_probas))
    result["std_probability"] = float(np.std(window_probas, ddof=0))
    result["variance_probability"] = float(np.var(window_probas, ddof=0))
    result["p95_probability"] = float(np.percentile(window_probas, 95))
    result["p99_probability"] = float(np.percentile(window_probas, 99))
    result["probability_range"] = float(np.max(window_probas) - np.min(window_probas))

    if window_secs is not None and len(window_secs) == n and n > 1:
        result["area_under_probability_curve"] = float(
            np.trapezoid(window_probas, window_secs)
        )
    else:
        result["area_under_probability_curve"] = float(
            np.trapezoid(window_probas)
        )

    above_half = window_probas >= 0.5
    max_run = 0
    cur_run = 0
    for v in above_half:
        if v:
            cur_run += 1
            max_run = max(max_run, cur_run)
        else:
            cur_run = 0
    result["max_consecutive_positive_windows_above_0_5"] = int(max_run)

    for frac_thresh in PROBABILITY_FRACTION_THRESHOLDS:
        result[f"fraction_windows_above_{frac_thresh}"] = float(
            np.mean(window_probas >= frac_thresh)
        )

    return result


# ======================================================================
# STEP 7: Threshold / smoothing / duration / peak forensics per FN event
# ======================================================================
def threshold_forensics_for_event(
    smoothed_probas_by_window: Dict[str, np.ndarray],
    window_indices: np.ndarray,
    gt_window_range: Tuple[int, int],
    default_smoothing_col: str,
) -> List[Dict[str, Any]]:
    """For each threshold, determine whether the FN event's GT window range
    would contain at least one window above threshold (would_detect_event),
    using the default (best-config) smoothing column."""
    rows = []
    probas = smoothed_probas_by_window[default_smoothing_col]
    gt_start, gt_end = gt_window_range
    in_range_mask = (window_indices >= gt_start) & (window_indices <= gt_end)
    in_range_probas = probas[in_range_mask]
    in_range_windows = window_indices[in_range_mask]

    for thr in THRESHOLD_SWEEP:
        above = in_range_probas >= thr
        would_detect = bool(above.any())
        if would_detect:
            first_idx = int(np.argmax(above))
            first_detection_window = int(in_range_windows[first_idx])
            detected_duration = int(above.sum())
            peak_prob = float(in_range_probas[above].max())
        else:
            first_detection_window = -1
            detected_duration = 0
            peak_prob = float(in_range_probas.max()) if len(in_range_probas) > 0 else np.nan

        rows.append({
            "threshold": thr,
            "would_detect_event": would_detect,
            "first_detection_window": first_detection_window,
            "detected_duration_windows": detected_duration,
            "peak_probability_in_range": peak_prob,
        })
    return rows


def smoothing_forensics_for_event(
    smoothed_probas_by_window: Dict[str, np.ndarray],
    window_indices: np.ndarray,
    gt_window_range: Tuple[int, int],
    threshold: float,
) -> List[Dict[str, Any]]:
    rows = []
    gt_start, gt_end = gt_window_range
    in_range_mask = (window_indices >= gt_start) & (window_indices <= gt_end)
    in_range_windows = window_indices[in_range_mask]

    for win in SMOOTHING_FORENSICS_WINDOWS:
        col = f"smoothed_prob_{win}"
        if col not in smoothed_probas_by_window:
            continue
        probas = smoothed_probas_by_window[col]
        in_range_probas = probas[in_range_mask]
        above = in_range_probas >= threshold

        recovered = bool(above.any())
        suppressed = not recovered

        # fragmentation: count contiguous positive runs within the GT range
        n_runs = 0
        prev = False
        for v in above:
            if v and not prev:
                n_runs += 1
            prev = v
        fragmented = n_runs > 1
        merged = False  # merging across separate GT events is assessed at patient level

        rows.append({
            "smoothing_window": win,
            "event_recovered": recovered,
            "event_suppressed": suppressed,
            "event_fragmented": fragmented,
            "contiguous_positive_runs": int(n_runs),
            "event_merged": merged,
            "peak_probability_in_range": float(in_range_probas.max()) if len(in_range_probas) else np.nan,
        })
    return rows


def duration_forensics_for_event(
    smoothed_probas_by_window: Dict[str, np.ndarray],
    window_indices: np.ndarray,
    gt_window_range: Tuple[int, int],
    threshold: float,
    default_smoothing_col: str,
) -> List[Dict[str, Any]]:
    rows = []
    gt_start, gt_end = gt_window_range
    in_range_mask = (window_indices >= gt_start) & (window_indices <= gt_end)
    in_range_probas = smoothed_probas_by_window[default_smoothing_col][in_range_mask]
    above = in_range_probas >= threshold

    max_run = 0
    cur_run = 0
    for v in above:
        if v:
            cur_run += 1
            max_run = max(max_run, cur_run)
        else:
            cur_run = 0

    for min_dur in MIN_DURATION_SWEEP:
        survives = max_run >= min_dur
        rows.append({
            "min_duration": min_dur,
            "max_contiguous_above_threshold": int(max_run),
            "event_survives": bool(survives),
            "event_rejected": bool(not survives),
        })
    return rows


def peak_filter_forensics_for_event(
    smoothed_probas_by_window: Dict[str, np.ndarray],
    window_indices: np.ndarray,
    gt_window_range: Tuple[int, int],
    default_smoothing_col: str,
) -> List[Dict[str, Any]]:
    rows = []
    gt_start, gt_end = gt_window_range
    in_range_mask = (window_indices >= gt_start) & (window_indices <= gt_end)
    in_range_probas = smoothed_probas_by_window[default_smoothing_col][in_range_mask]
    peak = float(in_range_probas.max()) if len(in_range_probas) else 0.0

    for peak_thresh in PEAK_FILTER_SWEEP:
        survives = peak >= peak_thresh
        rows.append({
            "min_peak_probability": peak_thresh,
            "event_peak_probability": peak,
            "event_survives": bool(survives),
            "event_rejected": bool(not survives),
        })
    return rows


# ======================================================================
# STEP 8: Root cause classification
# ======================================================================
def classify_root_cause(
    prob_forensics: Dict[str, Any],
    threshold_rows: List[Dict[str, Any]],
    smoothing_rows: List[Dict[str, Any]],
    duration_rows: List[Dict[str, Any]],
    peak_rows: List[Dict[str, Any]],
    best_config: Dict[str, Any],
) -> Tuple[str, str]:
    """
    Deterministic, evidence-based classification. Returns (label, evidence).
    Allowed labels:
      MODEL_BLIND, THRESHOLD_FAILURE, SMOOTHING_FAILURE, PEAK_FILTER_FAILURE,
      MIN_DURATION_FAILURE, CALIBRATION_FAILURE, EVENT_AGGREGATION_FAILURE,
      PATIENT_SHIFT, UNKNOWN
    """
    max_p = prob_forensics.get("max_probability", np.nan)

    # 1. MODEL_BLIND: model never assigns meaningful probability to this event,
    #    even at the lowest evaluated threshold.
    lowest_thr = min(THRESHOLD_SWEEP)
    lowest_thr_row = next((r for r in threshold_rows if r["threshold"] == lowest_thr), None)
    if (not np.isnan(max_p)) and max_p < lowest_thr:
        evidence = (
            f"max_probability={max_p:.6f} is below the lowest evaluated "
            f"threshold ({lowest_thr}); model assigns negligible probability "
            f"to this event's ground-truth windows under any smoothing."
        )
        return "MODEL_BLIND", evidence

    if lowest_thr_row is not None and not lowest_thr_row["would_detect_event"]:
        evidence = (
            f"Even at threshold={lowest_thr} with the production smoothing "
            f"window, no window in the GT range exceeds the threshold "
            f"(peak_probability_in_range="
            f"{lowest_thr_row['peak_probability_in_range']:.6f}). "
            f"Model does not surface this event at any practical threshold."
        )
        return "MODEL_BLIND", evidence

    # 2. PEAK_FILTER_FAILURE: under the best config's min_peak_probability,
    #    the event's peak is rejected, but at threshold/duration alone it
    #    would otherwise be detected.
    best_peak_thresh = best_config.get("min_peak_probability")
    if best_peak_thresh is not None:
        peak_row = next(
            (r for r in peak_rows if abs(r["min_peak_probability"] - best_peak_thresh) < 1e-9),
            None,
        )
        if peak_row is not None and peak_row["event_rejected"]:
            best_thr_row = next(
                (r for r in threshold_rows if abs(r["threshold"] - best_config.get("threshold", 0.01)) < 1e-9),
                None,
            )
            if best_thr_row is not None and best_thr_row["would_detect_event"]:
                evidence = (
                    f"event_peak_probability={peak_row['event_peak_probability']:.6f} "
                    f"< min_peak_probability filter ({best_peak_thresh}) used in the "
                    f"best configuration, while threshold={best_config.get('threshold')} "
                    f"alone WOULD detect this event "
                    f"(peak_in_range={best_thr_row['peak_probability_in_range']:.6f}). "
                    f"The peak-probability filter is the binding constraint."
                )
                return "PEAK_FILTER_FAILURE", evidence

    # 3. MIN_DURATION_FAILURE: under best config's min_duration, the run
    #    of above-threshold windows is too short.
    best_min_dur = best_config.get("min_duration")
    if best_min_dur is not None:
        dur_row = next(
            (r for r in duration_rows if r["min_duration"] == best_min_dur), None
        )
        if dur_row is not None and dur_row["event_rejected"]:
            best_thr_row = next(
                (r for r in threshold_rows if abs(r["threshold"] - best_config.get("threshold", 0.01)) < 1e-9),
                None,
            )
            if best_thr_row is not None and best_thr_row["would_detect_event"]:
                evidence = (
                    f"max_contiguous_above_threshold="
                    f"{dur_row['max_contiguous_above_threshold']} windows "
                    f"< min_duration filter ({best_min_dur}) used in the best "
                    f"configuration, despite threshold={best_config.get('threshold')} "
                    f"being exceeded somewhere in the GT range. "
                    f"The minimum-duration filter is the binding constraint."
                )
                return "MIN_DURATION_FAILURE", evidence

    # 4. SMOOTHING_FAILURE: with smoothing window 0 (no smoothing) the event
    #    is recovered at the best-config threshold, but with the best-config
    #    smoothing window it is suppressed.
    best_smoothing = best_config.get("smoothing_window")
    if best_smoothing is not None:
        no_smooth_row = next((r for r in smoothing_rows if r["smoothing_window"] == 0), None)
        best_smooth_row = next(
            (r for r in smoothing_rows if r["smoothing_window"] == best_smoothing), None
        )
        if (
            no_smooth_row is not None
            and best_smooth_row is not None
            and no_smooth_row["event_recovered"]
            and best_smooth_row["event_suppressed"]
        ):
            evidence = (
                f"With smoothing_window=0 (raw probabilities), the event's "
                f"GT range exceeds threshold={best_config.get('threshold')} "
                f"(peak={no_smooth_row['peak_probability_in_range']:.6f}); "
                f"with the production smoothing_window={best_smoothing}, the "
                f"smoothed peak in range "
                f"({best_smooth_row['peak_probability_in_range']:.6f}) falls "
                f"below threshold. Temporal smoothing dilutes a short, sharp "
                f"probability spike below the operating threshold."
            )
            return "SMOOTHING_FAILURE", evidence

    # 5. THRESHOLD_FAILURE: the event WOULD be detected at some lower
    #    threshold than the best config's threshold, but not at the best
    #    config's threshold itself (and not already explained above).
    best_thr = best_config.get("threshold", 0.01)
    best_thr_row = next(
        (r for r in threshold_rows if abs(r["threshold"] - best_thr) < 1e-9), None
    )
    if best_thr_row is not None and not best_thr_row["would_detect_event"]:
        recoverable_at_lower = [
            r for r in threshold_rows if r["threshold"] < best_thr and r["would_detect_event"]
        ]
        if recoverable_at_lower:
            lowest_recoverable = max(r["threshold"] for r in recoverable_at_lower)
            evidence = (
                f"Event is NOT detected at the best-configuration "
                f"threshold={best_thr} (peak_in_range="
                f"{best_thr_row['peak_probability_in_range']:.6f}), but WOULD "
                f"be detected at threshold={lowest_recoverable} "
                f"(peak exceeds that lower threshold). "
                f"The operating threshold is too high for this event's "
                f"probability profile."
            )
            return "THRESHOLD_FAILURE", evidence

    # 6. CALIBRATION_FAILURE: model assigns moderate-to-high raw confidence
    #    (max_probability substantial, e.g. >= 0.3) in the GT range, the
    #    event is recoverable at SOME threshold/config combination tested,
    #    yet still falls below the production calibrated threshold in a way
    #    not explained by smoothing/duration/peak — indicates the
    #    calibration mapping compresses scores for this patient's events.
    if (not np.isnan(max_p)) and max_p >= 0.30:
        any_config_recovers = any(r["would_detect_event"] for r in threshold_rows)
        if any_config_recovers and best_thr_row is not None and not best_thr_row["would_detect_event"]:
            evidence = (
                f"max_probability={max_p:.6f} in the GT range indicates the "
                f"underlying model carries real signal for this event, and "
                f"the event IS recoverable at some threshold in the sweep, "
                f"yet is not detected at the calibrated production "
                f"threshold={best_thr}. The isotonic calibration mapping "
                f"(fit on chb03/chb15/chb23) compresses this patient's "
                f"probability range below the operating point."
            )
            return "CALIBRATION_FAILURE", evidence

    # 7. EVENT_AGGREGATION_FAILURE: short isolated bursts above threshold
    #    exist but are fragmented into many short runs at the production
    #    smoothing window, none individually meeting duration, while the
    #    raw signal (smoothing=0) shows a recoverable single run — already
    #    partially covered by SMOOTHING_FAILURE; this branch covers the
    #    case where fragmentation (not suppression) is the issue.
    best_smooth_row = next(
        (r for r in smoothing_rows if r["smoothing_window"] == best_smoothing), None
    ) if best_smoothing is not None else None
    if best_smooth_row is not None and best_smooth_row["event_recovered"] and best_smooth_row["event_fragmented"]:
        evidence = (
            f"At the production smoothing_window={best_smoothing}, threshold="
            f"{best_config.get('threshold')}, the event's GT range contains "
            f"{best_smooth_row['contiguous_positive_runs']} separate "
            f"above-threshold runs rather than one contiguous run. Event "
            f"aggregation logic may fragment this single GT seizure into "
            f"multiple short candidate events, none of which individually "
            f"satisfies min_duration={best_min_dur}."
        )
        return "EVENT_AGGREGATION_FAILURE", evidence

    # 8. PATIENT_SHIFT: model probability profile for this event is globally
    #    low/flat (low variance, low max) relative to what training-distribution
    #    seizures look like — flagged here as a fallback when probability is
    #    uniformly weak across the whole event (low max AND low variance),
    #    suggestive of a feature-distribution mismatch for this patient.
    var_p = prob_forensics.get("variance_probability", np.nan)
    if (not np.isnan(max_p)) and (not np.isnan(var_p)) and max_p < 0.30 and var_p < 0.01:
        evidence = (
            f"max_probability={max_p:.6f} and variance_probability={var_p:.6f} "
            f"are both low across the entire GT event window — the model "
            f"produces a uniformly flat, low-confidence probability trace "
            f"for this patient's seizure, consistent with this patient's "
            f"EEG feature distribution differing from the training "
            f"distribution (patient-level distribution shift). See "
            f"PHASE5D_PATIENT_SHIFT_ANALYSIS.csv for cross-patient comparison."
        )
        return "PATIENT_SHIFT", evidence

    return "UNKNOWN", (
        f"No deterministic rule matched. max_probability={max_p}, "
        f"best_threshold_would_detect="
        f"{best_thr_row['would_detect_event'] if best_thr_row else None}. "
        f"Manual review required."
    )


# ======================================================================
# MAIN
# ======================================================================
def main() -> int:
    start_time = time.time()
    schema_audit = SchemaAudit()
    runtime_audit: Dict[str, Any] = {
        "timestamp_start": datetime.now(timezone.utc).isoformat(),
        "stages": {},
        "peak_memory_mb": get_process_memory_mb(),
    }
    config_used: Dict[str, Any] = {}
    file_hashes: Dict[str, str] = {}

    try:
        # ------------------------------------------------------------
        # STEP 0: Schema discovery
        # ------------------------------------------------------------
        stage_t0 = time.time()
        log("STEP 0: Schema discovery...")

        for key in INPUT_FILES:
            path = resolve_path(key)
            schema_audit.audit["file_existence"][key] = {
                "path": INPUT_FILES[key], "exists": True,
            }
            file_hashes[key] = file_sha256(path)

        feature_names, feature_count = discover_feature_signature(schema_audit)
        patient_split = discover_patient_split(schema_audit)
        dataset_columns, meta_cols = discover_dataset_schema(feature_names, schema_audit)
        model = discover_model(feature_names, schema_audit)
        event_pred_columns = discover_event_predictions_schema(schema_audit)
        config_search_columns = discover_configuration_search_schema(schema_audit)

        with open(resolve_path("best_configuration_5c"), "r") as f:
            best_config_full = json.load(f)
        if "BEST_F1" not in best_config_full:
            raise RuntimeError(
                "ABSOLUTE REQUIREMENT #1 VIOLATION: PHASE5C_BEST_CONFIGURATION.json "
                f"missing 'BEST_F1' key. Found keys: {list(best_config_full.keys())}"
            )
        best_config = best_config_full["BEST_F1"]
        required_cfg_keys = ["smoothing_window", "threshold", "min_duration", "min_peak_probability"]
        missing_cfg = [k for k in required_cfg_keys if k not in best_config]
        if missing_cfg:
            raise RuntimeError(
                f"PHASE5C_BEST_CONFIGURATION.json BEST_F1 missing keys: {missing_cfg}"
            )

        test_patients = patient_split["test_patients"]
        train_patients = patient_split.get("train_patients", [])

        for p in DEDICATED_PATIENTS + SUCCESSFUL_PATIENTS:
            if p not in test_patients:
                raise RuntimeError(
                    f"Patient '{p}' required for dedicated/comparison forensic "
                    f"analysis is not present in test_patients: {test_patients}"
                )

        config_used["best_config_used_for_forensics"] = best_config
        config_used["meta_columns"] = meta_cols
        config_used["feature_count"] = feature_count
        config_used["test_patients"] = test_patients
        config_used["dedicated_patients"] = DEDICATED_PATIENTS
        config_used["successful_comparison_patients"] = SUCCESSFUL_PATIENTS

        runtime_audit["stages"]["schema_discovery_seconds"] = round(time.time() - stage_t0, 4)
        log("STEP 0 complete.")

        # ------------------------------------------------------------
        # STEP 1: Load engineered dataset for test + calibration patients
        # ------------------------------------------------------------
        stage_t0 = time.time()
        log("STEP 1: Loading engineered dataset for test and calibration patients...")

        calibration_patients, calibration_source = select_calibration_patients(
            patient_split, train_patients
        )
        config_used["calibration_patients"] = calibration_patients
        config_used["calibration_source"] = calibration_source

        load_columns = list(dict.fromkeys(
            [c for c in meta_cols.values() if c is not None] + feature_names
        ))

        dataset_path = resolve_path("dataset")

        df_test = load_parquet_filtered(dataset_path, load_columns, test_patients)
        if df_test.empty:
            raise RuntimeError(
                f"No rows loaded for test_patients={test_patients} from "
                f"{INPUT_FILES['dataset']}. Cannot proceed."
            )

        df_cal = pd.DataFrame(columns=load_columns)
        if calibration_patients:
            df_cal = load_parquet_filtered(dataset_path, load_columns, calibration_patients)

        runtime_audit["rows_processed_test"] = int(len(df_test))
        runtime_audit["rows_processed_calibration"] = int(len(df_cal))
        runtime_audit["patients_processed"] = int(df_test[meta_cols["patient"]].nunique())
        runtime_audit["edfs_processed"] = int(df_test[meta_cols["edf"]].nunique())
        runtime_audit["stages"]["dataset_load_seconds"] = round(time.time() - stage_t0, 4)
        runtime_audit["peak_memory_mb"] = max(runtime_audit["peak_memory_mb"], get_process_memory_mb())
        log(f"STEP 1 complete: test rows={len(df_test)}, calibration rows={len(df_cal)}")

        # ------------------------------------------------------------
        # STEP 2: Generate raw probabilities + calibration
        # ------------------------------------------------------------
        stage_t0 = time.time()
        log("STEP 2: Generating model probabilities and applying calibration...")

        X_test = df_test[feature_names].to_numpy(dtype=np.float32, copy=False)
        raw_proba_test = model.predict_proba(X_test)[:, 1].astype(np.float32)
        del X_test
        gc.collect()

        calibration_applied = False
        calibration_ece_before = None
        calibration_ece_after = None

        if not df_cal.empty:
            X_cal = df_cal[feature_names].to_numpy(dtype=np.float32, copy=False)
            raw_proba_cal = model.predict_proba(X_cal)[:, 1].astype(np.float32)
            y_cal = df_cal[meta_cols["label"]].values
            del X_cal
            gc.collect()

            calibrator = IsotonicRegression(out_of_bounds="clip")
            calibrator.fit(raw_proba_cal, y_cal)

            def _ece(proba, labels, n_bins=10):
                try:
                    frac_pos, mean_pred = calibration_curve(labels, proba, n_bins=n_bins, strategy="uniform")
                    return float(np.mean(np.abs(frac_pos - mean_pred)))
                except Exception:
                    return float("nan")

            calibration_ece_before = _ece(raw_proba_cal, y_cal)
            cal_proba_cal = calibrator.predict(raw_proba_cal)
            calibration_ece_after = _ece(cal_proba_cal, y_cal)

            pred_proba_test = calibrator.predict(raw_proba_test).astype(np.float32)
            calibration_applied = True
        else:
            pred_proba_test = raw_proba_test

        df_test["raw_pred_proba"] = raw_proba_test
        df_test["pred_proba"] = pred_proba_test

        config_used["calibration_applied"] = calibration_applied
        config_used["calibration_ece_before"] = calibration_ece_before
        config_used["calibration_ece_after"] = calibration_ece_after

        runtime_audit["stages"]["model_inference_calibration_seconds"] = round(time.time() - stage_t0, 4)
        runtime_audit["peak_memory_mb"] = max(runtime_audit["peak_memory_mb"], get_process_memory_mb())
        log(f"STEP 2 complete: calibration_applied={calibration_applied}")

        # ------------------------------------------------------------
        # STEP 3: Ground truth event reconstruction
        # ------------------------------------------------------------
        stage_t0 = time.time()
        log("STEP 3: Reconstructing ground-truth events from contiguous label==1 windows...")

        gt_events = build_ground_truth_events(df_test, meta_cols)
        if gt_events.empty:
            raise RuntimeError(
                "Ground-truth event reconstruction produced zero events for "
                "the test patients. Cannot perform false-negative forensics."
            )

        runtime_audit["total_gt_events"] = int(len(gt_events))
        runtime_audit["stages"]["gt_reconstruction_seconds"] = round(time.time() - stage_t0, 4)
        log(f"STEP 3 complete: {len(gt_events)} ground-truth events reconstructed.")

        # ------------------------------------------------------------
        # STEP 4: Temporal smoothing
        # ------------------------------------------------------------
        stage_t0 = time.time()
        log("STEP 4: Applying temporal smoothing (production + forensic windows)...")

        df_test = apply_smoothing(df_test, meta_cols)

        all_smoothing_cols = ["smoothed_prob_0"] + [
            f"smoothed_prob_{w}" for w in sorted(set(SMOOTHING_WINDOWS + [w for w in SMOOTHING_FORENSICS_WINDOWS if w != 0]))
        ]
        for col in all_smoothing_cols:
            if col not in df_test.columns:
                raise RuntimeError(f"Expected smoothing column '{col}' was not generated.")
            nan_count = df_test[col].isna().sum()
            if nan_count > 0:
                raise RuntimeError(f"NaN values found in {col} after smoothing: {nan_count}")

        runtime_audit["stages"]["smoothing_seconds"] = round(time.time() - stage_t0, 4)
        runtime_audit["peak_memory_mb"] = max(runtime_audit["peak_memory_mb"], get_process_memory_mb())
        log("STEP 4 complete.")

        # ------------------------------------------------------------
        # STEP 5: Determine FN events under best (BEST_F1) configuration
        # ------------------------------------------------------------
        stage_t0 = time.time()
        log("STEP 5: Determining false-negative events under best configuration...")

        best_smoothing_col = (
            "smoothed_prob_0" if best_config["smoothing_window"] == 0
            else f"smoothed_prob_{best_config['smoothing_window']}"
        )
        if best_smoothing_col not in df_test.columns:
            raise RuntimeError(
                f"Best configuration smoothing_window="
                f"{best_config['smoothing_window']} produced no column "
                f"'{best_smoothing_col}'."
            )

        matched_gt_ids = full_pipeline_matched_gt_ids(
            df_test, meta_cols, gt_events,
            smoothing_window=best_config["smoothing_window"],
            threshold=best_config["threshold"],
            min_duration=best_config["min_duration"],
            min_peak_prob=best_config["min_peak_probability"],
        )

        gt_events["is_matched_under_best_config"] = gt_events["gt_event_id"].isin(matched_gt_ids)
        fn_events = gt_events[~gt_events["is_matched_under_best_config"]].copy().reset_index(drop=True)

        if fn_events.empty:
            raise RuntimeError(
                "Zero false-negative events found under the best configuration. "
                "Forensic analysis requires at least one FN event to investigate. "
                f"Total GT events={len(gt_events)}, matched={len(matched_gt_ids)}."
            )

        runtime_audit["total_fn_events"] = int(len(fn_events))
        runtime_audit["stages"]["fn_determination_seconds"] = round(time.time() - stage_t0, 4)
        log(f"STEP 5 complete: {len(fn_events)} false-negative events identified.")

        # ------------------------------------------------------------
        # STEP 6: Per-FN forensics (probability, threshold, smoothing,
        #         duration, peak filter)
        # ------------------------------------------------------------
        stage_t0 = time.time()
        log("STEP 6: Running per-event forensics (probability/threshold/smoothing/duration/peak)...")

        df_sorted = df_test.sort_values(
            [meta_cols["patient"], meta_cols["edf"], meta_cols["window_index"]]
        ).reset_index(drop=True)

        patients_arr = df_sorted[meta_cols["patient"]].values
        edfs_arr = df_sorted[meta_cols["edf"]].values
        win_arr = df_sorted[meta_cols["window_index"]].values
        sec_arr = (
            df_sorted[meta_cols["window_start_sec"]].values
            if meta_cols.get("window_start_sec") else None
        )

        smoothing_cols_present = [c for c in all_smoothing_cols if c in df_sorted.columns]
        smoothed_arrays = {c: df_sorted[c].values for c in smoothing_cols_present}
        raw_proba_arr = df_sorted["pred_proba"].values

        fn_rows = []
        threshold_forensics_rows = []
        smoothing_forensics_rows = []
        duration_forensics_rows = []
        peak_forensics_rows = []
        root_cause_rows = []

        for fi, fn in fn_events.iterrows():
            patient = fn["patient"]
            edf = fn["edf"]
            gt_start = int(fn["gt_start_window"])
            gt_end = int(fn["gt_end_window"])
            gt_event_id = fn["gt_event_id"]

            group_mask = (patients_arr == patient) & (edfs_arr == edf)
            group_win = win_arr[group_mask]
            group_secs = sec_arr[group_mask] if sec_arr is not None else None
            group_raw = raw_proba_arr[group_mask]
            group_smoothed = {c: arr[group_mask] for c, arr in smoothed_arrays.items()}

            in_range_mask = (group_win >= gt_start) & (group_win <= gt_end)
            in_range_raw = group_raw[in_range_mask]
            in_range_secs = group_secs[in_range_mask] if group_secs is not None else None

            fn_rows.append({
                "patient": patient,
                "edf": edf,
                "gt_event_id": gt_event_id,
                "gt_start_window": gt_start,
                "gt_end_window": gt_end,
                "gt_start_sec": fn.get("gt_start_sec", np.nan),
                "gt_end_sec": fn.get("gt_end_sec", np.nan),
                "duration_sec": fn.get("gt_duration_sec", np.nan),
                "number_of_positive_windows": fn.get("number_of_positive_windows", np.nan),
                "matching_status": "FALSE_NEGATIVE",
                "source_file": INPUT_FILES["dataset"],
            })

            # STEP 6a: probability forensics (raw probability inside GT range)
            prob_forensics = probability_forensics_for_event(in_range_raw, in_range_secs)
            prob_row = {"patient": patient, "edf": edf, "gt_event_id": gt_event_id}
            prob_row.update(prob_forensics)
            fn_rows[-1].update({f"prob_{k}": v for k, v in prob_forensics.items()})

            # STEP 6b: threshold forensics
            thr_rows = threshold_forensics_for_event(
                group_smoothed, group_win, (gt_start, gt_end), best_smoothing_col
            )
            for r in thr_rows:
                row = {"patient": patient, "edf": edf, "gt_event_id": gt_event_id}
                row.update(r)
                threshold_forensics_rows.append(row)

            # STEP 6c: smoothing forensics
            smo_rows = smoothing_forensics_for_event(
                group_smoothed, group_win, (gt_start, gt_end), best_config["threshold"]
            )
            for r in smo_rows:
                row = {"patient": patient, "edf": edf, "gt_event_id": gt_event_id}
                row.update(r)
                smoothing_forensics_rows.append(row)

            # STEP 6d: duration forensics
            dur_rows = duration_forensics_for_event(
                group_smoothed, group_win, (gt_start, gt_end),
                best_config["threshold"], best_smoothing_col,
            )
            for r in dur_rows:
                row = {"patient": patient, "edf": edf, "gt_event_id": gt_event_id}
                row.update(r)
                duration_forensics_rows.append(row)

            # STEP 6e: peak filter forensics
            peak_rows_ev = peak_filter_forensics_for_event(
                group_smoothed, group_win, (gt_start, gt_end), best_smoothing_col
            )
            for r in peak_rows_ev:
                row = {"patient": patient, "edf": edf, "gt_event_id": gt_event_id}
                row.update(r)
                peak_forensics_rows.append(row)

            # STEP 9: Root cause classification
            label, evidence = classify_root_cause(
                prob_forensics, thr_rows, smo_rows, dur_rows, peak_rows_ev, best_config
            )
            root_cause_rows.append({
                "patient": patient,
                "edf": edf,
                "gt_event_id": gt_event_id,
                "gt_start_window": gt_start,
                "gt_end_window": gt_end,
                "root_cause_label": label,
                "evidence": evidence,
                "max_probability_in_range": prob_forensics.get("max_probability"),
                "mean_probability_in_range": prob_forensics.get("mean_probability"),
                "variance_probability_in_range": prob_forensics.get("variance_probability"),
            })

        fn_events_out = pd.DataFrame(fn_rows)
        threshold_forensics_df = pd.DataFrame(threshold_forensics_rows)
        smoothing_forensics_df = pd.DataFrame(smoothing_forensics_rows)
        duration_forensics_df = pd.DataFrame(duration_forensics_rows)
        peak_forensics_df = pd.DataFrame(peak_forensics_rows)
        root_cause_df = pd.DataFrame(root_cause_rows)

        runtime_audit["stages"]["per_event_forensics_seconds"] = round(time.time() - stage_t0, 4)
        runtime_audit["peak_memory_mb"] = max(runtime_audit["peak_memory_mb"], get_process_memory_mb())
        log("STEP 6 complete.")

        # ------------------------------------------------------------
        # STEP 7: Patient-level failure forensics
        # ------------------------------------------------------------
        stage_t0 = time.time()
        log("STEP 7: Patient-level failure forensics...")

        patient_summary_rows = []
        for patient in test_patients:
            patient_gt = gt_events[gt_events["patient"] == patient]
            n_gt = len(patient_gt)
            n_fn = int((~patient_gt["is_matched_under_best_config"]).sum()) if n_gt else 0
            n_tp = n_gt - n_fn

            patient_mask = patients_arr == patient
            patient_raw = raw_proba_arr[patient_mask]

            event_density = (
                float(patient_gt["number_of_positive_windows"].sum()) / float(patient_mask.sum())
                if patient_mask.sum() > 0 else np.nan
            )

            patient_summary_rows.append({
                "patient": patient,
                "gt_events": int(n_gt),
                "tp_events": int(n_tp),
                "fn_events": int(n_fn),
                "event_recall": round(n_tp / n_gt, 6) if n_gt > 0 else np.nan,
                "mean_probability": float(np.mean(patient_raw)) if len(patient_raw) else np.nan,
                "median_probability": float(np.median(patient_raw)) if len(patient_raw) else np.nan,
                "max_probability": float(np.max(patient_raw)) if len(patient_raw) else np.nan,
                "probability_variance": float(np.var(patient_raw, ddof=0)) if len(patient_raw) else np.nan,
                "event_density": event_density,
                "detected_fraction": round(n_tp / n_gt, 6) if n_gt > 0 else np.nan,
                "missed_fraction": round(n_fn / n_gt, 6) if n_gt > 0 else np.nan,
                "is_dedicated_failure_patient": patient in DEDICATED_PATIENTS,
                "is_successful_comparison_patient": patient in SUCCESSFUL_PATIENTS,
            })

        patient_summary_df = pd.DataFrame(patient_summary_rows)
        patient_summary_df = patient_summary_df.sort_values(
            "missed_fraction", ascending=False, na_position="last"
        ).reset_index(drop=True)
        patient_summary_df["failure_rank"] = patient_summary_df.index + 1

        runtime_audit["stages"]["patient_failure_forensics_seconds"] = round(time.time() - stage_t0, 4)
        log("STEP 7 complete.")

        # ------------------------------------------------------------
        # STEP 8: Patient shift analysis (failed vs successful patients)
        # ------------------------------------------------------------
        stage_t0 = time.time()
        log("STEP 8: Patient distribution-shift analysis...")

        shift_rows = []
        successful_raw = raw_proba_arr[np.isin(patients_arr, SUCCESSFUL_PATIENTS)]
        successful_gt = gt_events[gt_events["patient"].isin(SUCCESSFUL_PATIENTS)]

        for patient in DEDICATED_PATIENTS:
            failed_raw = raw_proba_arr[patients_arr == patient]
            failed_gt = gt_events[gt_events["patient"] == patient]

            row = {
                "failed_patient": patient,
                "comparison_patients": ",".join(SUCCESSFUL_PATIENTS),
                "failed_mean_probability": float(np.mean(failed_raw)) if len(failed_raw) else np.nan,
                "successful_mean_probability": float(np.mean(successful_raw)) if len(successful_raw) else np.nan,
                "failed_max_probability": float(np.max(failed_raw)) if len(failed_raw) else np.nan,
                "successful_max_probability": float(np.max(successful_raw)) if len(successful_raw) else np.nan,
                "failed_probability_variance": float(np.var(failed_raw, ddof=0)) if len(failed_raw) else np.nan,
                "successful_probability_variance": float(np.var(successful_raw, ddof=0)) if len(successful_raw) else np.nan,
                "failed_gt_event_count": int(len(failed_gt)),
                "successful_gt_event_count": int(len(successful_gt)),
                "failed_mean_event_duration_sec": (
                    float(failed_gt["gt_duration_sec"].mean()) if len(failed_gt) else np.nan
                ),
                "successful_mean_event_duration_sec": (
                    float(successful_gt["gt_duration_sec"].mean()) if len(successful_gt) else np.nan
                ),
                "failed_mean_event_positive_windows": (
                    float(failed_gt["number_of_positive_windows"].mean()) if len(failed_gt) else np.nan
                ),
                "successful_mean_event_positive_windows": (
                    float(successful_gt["number_of_positive_windows"].mean()) if len(successful_gt) else np.nan
                ),
            }

            # KS-statistic style distribution distance via percentile comparison
            if len(failed_raw) and len(successful_raw):
                percentiles = [10, 25, 50, 75, 90, 95, 99]
                failed_pct = np.percentile(failed_raw, percentiles)
                success_pct = np.percentile(successful_raw, percentiles)
                row["probability_distribution_l1_distance"] = float(
                    np.mean(np.abs(failed_pct - success_pct))
                )
            else:
                row["probability_distribution_l1_distance"] = np.nan

            shift_rows.append(row)

        patient_shift_df = pd.DataFrame(shift_rows)

        runtime_audit["stages"]["patient_shift_analysis_seconds"] = round(time.time() - stage_t0, 4)
        log("STEP 8 complete.")

        # ------------------------------------------------------------
        # STEP 9: Write output files
        # ------------------------------------------------------------
        stage_t0 = time.time()
        log("STEP 9: Writing output files...")

        output_paths = {k: os.path.join(BASE_DIR, v) for k, v in OUTPUT_FILES.items()}

        fn_events_out.to_csv(output_paths["false_negative_events"], index=False)
        threshold_forensics_df.to_csv(output_paths["threshold_forensics"], index=False)
        smoothing_forensics_df.to_csv(output_paths["smoothing_forensics"], index=False)
        duration_forensics_df.to_csv(output_paths["duration_forensics"], index=False)
        peak_forensics_df.to_csv(output_paths["peak_forensics"], index=False)
        patient_summary_df.to_csv(output_paths["patient_failure_summary"], index=False)
        root_cause_df.to_csv(output_paths["root_cause_analysis"], index=False)
        patient_shift_df.to_csv(output_paths["patient_shift_analysis"], index=False)

        runtime_audit["stages"]["output_write_seconds"] = round(time.time() - stage_t0, 4)
        log("STEP 9 complete.")

        # ------------------------------------------------------------
        # STEP 10: Schema audit, runtime audit, execution report
        # ------------------------------------------------------------
        stage_t0 = time.time()
        log("STEP 10: Writing schema audit, runtime audit, execution report...")

        schema_audit.finalize(passed=True)
        with open(output_paths["schema_audit"], "w") as f:
            json.dump(schema_audit.audit, f, indent=2, default=str)

        total_runtime = round(time.time() - start_time, 4)
        runtime_audit["timestamp_end"] = datetime.now(timezone.utc).isoformat()
        runtime_audit["runtime_seconds"] = total_runtime
        runtime_audit["peak_memory_mb"] = max(runtime_audit["peak_memory_mb"], get_process_memory_mb())
        with open(output_paths["runtime_audit"], "w") as f:
            json.dump(runtime_audit, f, indent=2, default=str)

        # Build per-dedicated-patient narrative sections with evidence
        dedicated_sections = []
        for patient in DEDICATED_PATIENTS:
            p_fn = root_cause_df[root_cause_df["patient"] == patient]
            p_summary = patient_summary_df[patient_summary_df["patient"] == patient].iloc[0]
            p_shift = patient_shift_df[patient_shift_df["failed_patient"] == patient]

            lines = []
            lines.append(f"PATIENT {patient}")
            lines.append("-" * 70)
            lines.append(f"  Ground-truth events       : {int(p_summary['gt_events'])}")
            lines.append(f"  True positive events       : {int(p_summary['tp_events'])}")
            lines.append(f"  False negative events       : {int(p_summary['fn_events'])}")
            lines.append(f"  Event recall                : {p_summary['event_recall']}")
            lines.append(f"  Mean raw probability        : {p_summary['mean_probability']:.6f}")
            lines.append(f"  Max raw probability          : {p_summary['max_probability']:.6f}")
            lines.append(f"  Probability variance         : {p_summary['probability_variance']:.6f}")
            lines.append("")
            lines.append(f"  Q: Can the model see {patient}'s seizures?")
            max_probs = p_fn["max_probability_in_range"].tolist()
            if max_probs:
                overall_max = max(max_probs)
                if overall_max >= 0.30:
                    lines.append(
                        f"  A: PARTIALLY. At least one FN event reaches "
                        f"max_probability_in_range={overall_max:.6f} "
                        f"(>= 0.30), indicating the model assigns real "
                        f"signal to some of {patient}'s seizures, but the "
                        f"signal does not survive the production pipeline."
                    )
                else:
                    lines.append(
                        f"  A: NO / VERY WEAKLY. All FN events for "
                        f"{patient} have max_probability_in_range "
                        f"<= {overall_max:.6f}. The model is largely blind "
                        f"to this patient's seizure morphology."
                    )
            else:
                lines.append("  A: No FN events found for this patient under the best configuration.")
            lines.append("")

            for _, fn_row in p_fn.iterrows():
                gid = fn_row["gt_event_id"]
                lines.append(f"  Event {gid}:")
                lines.append(f"    Root cause classification: {fn_row['root_cause_label']}")
                lines.append(f"    Evidence: {fn_row['evidence']}")

                thr_sub = threshold_forensics_df[
                    (threshold_forensics_df["patient"] == patient)
                    & (threshold_forensics_df["gt_event_id"] == gid)
                ]
                recover_thrs = thr_sub[thr_sub["would_detect_event"]]["threshold"].tolist()
                if recover_thrs:
                    lines.append(
                        f"    Lower thresholds that WOULD recover this event: "
                        f"{sorted(recover_thrs, reverse=True)}"
                    )
                else:
                    lines.append(
                        "    NO threshold in the evaluated sweep "
                        f"({min(THRESHOLD_SWEEP)}-{max(THRESHOLD_SWEEP)}) "
                        "would recover this event."
                    )

                smo_sub = smoothing_forensics_df[
                    (smoothing_forensics_df["patient"] == patient)
                    & (smoothing_forensics_df["gt_event_id"] == gid)
                ]
                recovered_windows = smo_sub[smo_sub["event_recovered"]]["smoothing_window"].tolist()
                lines.append(
                    f"    Smoothing windows under which event is recovered "
                    f"(at threshold={best_config['threshold']}): {sorted(recovered_windows)}"
                )

                dur_sub = duration_forensics_df[
                    (duration_forensics_df["patient"] == patient)
                    & (duration_forensics_df["gt_event_id"] == gid)
                ]
                surviving_durs = dur_sub[dur_sub["event_survives"]]["min_duration"].tolist()
                lines.append(
                    f"    min_duration values event survives "
                    f"(at threshold={best_config['threshold']}, smoothing="
                    f"{best_config['smoothing_window']}): {sorted(surviving_durs)}"
                )

                peak_sub = peak_forensics_df[
                    (peak_forensics_df["patient"] == patient)
                    & (peak_forensics_df["gt_event_id"] == gid)
                ]
                surviving_peaks = peak_sub[peak_sub["event_survives"]]["min_peak_probability"].tolist()
                lines.append(
                    f"    min_peak_probability values event survives: "
                    f"{sorted(surviving_peaks)}"
                )
                lines.append("")

            if not p_shift.empty:
                shift_row = p_shift.iloc[0]
                lines.append("  Patient-shift comparison vs chb05/chb09 (successful patients):")
                lines.append(
                    f"    mean_probability: {patient}={shift_row['failed_mean_probability']:.6f} "
                    f"vs successful={shift_row['successful_mean_probability']:.6f}"
                )
                lines.append(
                    f"    max_probability: {patient}={shift_row['failed_max_probability']:.6f} "
                    f"vs successful={shift_row['successful_max_probability']:.6f}"
                )
                lines.append(
                    f"    probability_variance: {patient}={shift_row['failed_probability_variance']:.6f} "
                    f"vs successful={shift_row['successful_probability_variance']:.6f}"
                )
                lines.append(
                    f"    distribution L1 distance (percentile-based): "
                    f"{shift_row['probability_distribution_l1_distance']:.6f}"
                )
                shift_significant = shift_row['probability_distribution_l1_distance'] > 0.05
                lines.append(
                    f"    Is patient shift contributing? "
                    f"{'YES' if shift_significant else 'NO'} "
                    f"(L1 distance {'exceeds' if shift_significant else 'does not exceed'} "
                    f"0.05 threshold)"
                )
            lines.append("")
            dedicated_sections.append("\n".join(lines))

        # Overall summary stats for report
        all_max_probs = root_cause_df["max_probability_in_range"]
        any_calibration_failure = (root_cause_df["root_cause_label"] == "CALIBRATION_FAILURE").any()
        any_smoothing_failure = (root_cause_df["root_cause_label"] == "SMOOTHING_FAILURE").any()
        any_peak_failure = (root_cause_df["root_cause_label"] == "PEAK_FILTER_FAILURE").any()
        any_duration_failure = (root_cause_df["root_cause_label"] == "MIN_DURATION_FAILURE").any()
        any_threshold_failure = (root_cause_df["root_cause_label"] == "THRESHOLD_FAILURE").any()
        any_model_blind = (root_cause_df["root_cause_label"] == "MODEL_BLIND").any()
        any_patient_shift = (root_cause_df["root_cause_label"] == "PATIENT_SHIFT").any()
        any_aggregation_failure = (root_cause_df["root_cause_label"] == "EVENT_AGGREGATION_FAILURE").any()

        root_cause_value_counts = root_cause_df["root_cause_label"].value_counts().to_dict()

        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("PHASE5D FAILURE ANALYSIS - EXECUTION REPORT")
        report_lines.append("=" * 70)
        report_lines.append("")
        report_lines.append(f"Generated            : {datetime.now(timezone.utc).isoformat()}")
        report_lines.append(f"Python version       : {platform.python_version()}")
        report_lines.append(f"Platform             : {platform.platform()}")
        report_lines.append(f"numpy version        : {np.__version__}")
        report_lines.append(f"pandas version       : {pd.__version__}")
        report_lines.append(f"scikit-learn version : {_SKLEARN_VERSION}")
        report_lines.append(f"xgboost version      : {_XGBOOST_VERSION}")
        report_lines.append(f"joblib version       : {_JOBLIB_VERSION}")
        report_lines.append(f"Total runtime (sec)  : {total_runtime}")
        report_lines.append(f"Peak memory (MB)     : {runtime_audit['peak_memory_mb']}")
        report_lines.append("")
        report_lines.append("INPUT FILES AND HASHES (SHA-256)")
        report_lines.append("-" * 70)
        for key, fname in INPUT_FILES.items():
            report_lines.append(f"  {fname}: {file_hashes[key]}")
        report_lines.append("")
        report_lines.append("ANALYSIS CONFIGURATION")
        report_lines.append("-" * 70)
        report_lines.append(f"  Forensic configuration based on : PHASE5C_BEST_CONFIGURATION.json -> BEST_F1")
        report_lines.append(f"  smoothing_window      : {best_config['smoothing_window']}")
        report_lines.append(f"  threshold             : {best_config['threshold']}")
        report_lines.append(f"  min_duration          : {best_config['min_duration']}")
        report_lines.append(f"  min_peak_probability  : {best_config['min_peak_probability']}")
        report_lines.append(f"  calibration_applied   : {calibration_applied}")
        report_lines.append(f"  calibration_source    : {calibration_source}")
        report_lines.append(f"  calibration_patients  : {calibration_patients}")
        report_lines.append(f"  calibration_ece_before: {calibration_ece_before}")
        report_lines.append(f"  calibration_ece_after : {calibration_ece_after}")
        report_lines.append(f"  test_patients         : {test_patients}")
        report_lines.append(f"  metadata column map   : {meta_cols}")
        report_lines.append(f"  feature_count         : {feature_count}")
        report_lines.append(f"  threshold sweep       : {THRESHOLD_SWEEP}")
        report_lines.append(f"  smoothing forensics windows : {SMOOTHING_FORENSICS_WINDOWS}")
        report_lines.append(f"  min_duration sweep    : {MIN_DURATION_SWEEP}")
        report_lines.append(f"  peak filter sweep     : {PEAK_FILTER_SWEEP}")
        report_lines.append("")
        report_lines.append("GROUND TRUTH RECONSTRUCTION (from contiguous label==1 windows)")
        report_lines.append("-" * 70)
        report_lines.append(f"  Total reconstructed GT events (test patients): {len(gt_events)}")
        report_lines.append(f"  Matched (TP) under best config               : {len(matched_gt_ids)}")
        report_lines.append(f"  False negative events                        : {len(fn_events)}")
        report_lines.append("")
        report_lines.append("ROOT CAUSE DISTRIBUTION (across all FN events)")
        report_lines.append("-" * 70)
        for label, count in root_cause_value_counts.items():
            report_lines.append(f"  {label}: {count}")
        report_lines.append("")
        report_lines.append("=" * 70)
        report_lines.append("MANDATED FORENSIC QUESTIONS")
        report_lines.append("=" * 70)
        report_lines.append("")
        for section in dedicated_sections:
            report_lines.append(section)
        report_lines.append("=" * 70)
        report_lines.append("CROSS-CUTTING QUESTIONS (across chb02, chb14, chb22)")
        report_lines.append("=" * 70)
        report_lines.append("")
        report_lines.append(
            f"  Would lower thresholds recover them?     "
            f"{'YES, for at least one FN event' if any_threshold_failure else 'NO FN event classified as pure THRESHOLD_FAILURE'} "
            f"(see PHASE5D_THRESHOLD_FORENSICS.csv for per-event sweep)."
        )
        report_lines.append(
            f"  Would smoothing removal recover them?    "
            f"{'YES, at least one FN event is SMOOTHING_FAILURE' if any_smoothing_failure else 'NO FN event classified as SMOOTHING_FAILURE'} "
            f"(see PHASE5D_SMOOTHING_FORENSICS.csv)."
        )
        report_lines.append(
            f"  Would peak filter removal recover them?  "
            f"{'YES, at least one FN event is PEAK_FILTER_FAILURE' if any_peak_failure else 'NO FN event classified as PEAK_FILTER_FAILURE'} "
            f"(see PHASE5D_PEAK_FORENSICS.csv)."
        )
        report_lines.append(
            f"  Would duration filter removal recover them? "
            f"{'YES, at least one FN event is MIN_DURATION_FAILURE' if any_duration_failure else 'NO FN event classified as MIN_DURATION_FAILURE'} "
            f"(see PHASE5D_DURATION_FORENSICS.csv)."
        )
        report_lines.append(
            f"  Is calibration contributing?             "
            f"{'YES, at least one FN event is CALIBRATION_FAILURE' if any_calibration_failure else 'NO FN event classified as CALIBRATION_FAILURE'} "
            f"(calibration ECE before={calibration_ece_before}, after={calibration_ece_after})."
        )
        report_lines.append(
            f"  Is patient shift contributing?           "
            f"{'YES, at least one FN event is PATIENT_SHIFT' if any_patient_shift else 'NO FN event classified as PATIENT_SHIFT'} "
            f"(see PHASE5D_PATIENT_SHIFT_ANALYSIS.csv)."
        )
        report_lines.append(
            f"  Is event aggregation / fragmentation contributing? "
            f"{'YES, at least one FN event is EVENT_AGGREGATION_FAILURE' if any_aggregation_failure else 'NO FN event classified as EVENT_AGGREGATION_FAILURE'}."
        )
        report_lines.append(
            f"  Is the model fundamentally blind to any events? "
            f"{'YES, at least one FN event is MODEL_BLIND' if any_model_blind else 'NO FN event classified as MODEL_BLIND'}."
        )
        report_lines.append("")
        report_lines.append("=" * 70)
        report_lines.append("OUTPUT ARTIFACTS")
        report_lines.append("=" * 70)
        for key, fname in OUTPUT_FILES.items():
            report_lines.append(f"  [OK] {fname}")
        report_lines.append("")
        report_lines.append("=" * 70)
        report_lines.append("END OF EXECUTION REPORT")
        report_lines.append("=" * 70)

        with open(output_paths["execution_report"], "w") as f:
            f.write("\n".join(report_lines))

        runtime_audit["stages"]["audit_and_report_seconds"] = round(time.time() - stage_t0, 4)
        log("STEP 10 complete.")

        # ------------------------------------------------------------
        # SELF AUDIT
        # ------------------------------------------------------------
        log("SELF AUDIT: validating all outputs...")

        csv_outputs = [
            "false_negative_events", "threshold_forensics", "smoothing_forensics",
            "duration_forensics", "peak_forensics", "patient_failure_summary",
            "root_cause_analysis", "patient_shift_analysis",
        ]
        for key in csv_outputs:
            path = output_paths[key]
            if not os.path.exists(path):
                raise RuntimeError(f"SELF AUDIT FAILED: output file missing: {path}")
            check_df = pd.read_csv(path)
            if check_df.empty:
                raise RuntimeError(f"SELF AUDIT FAILED: output CSV is empty: {path}")
            if os.path.getsize(path) == 0:
                raise RuntimeError(f"SELF AUDIT FAILED: output file is zero bytes: {path}")

        json_outputs = ["schema_audit", "runtime_audit"]
        for key in json_outputs:
            path = output_paths[key]
            if not os.path.exists(path):
                raise RuntimeError(f"SELF AUDIT FAILED: output file missing: {path}")
            with open(path, "r") as f:
                content = json.load(f)
            if not content:
                raise RuntimeError(f"SELF AUDIT FAILED: output JSON is empty: {path}")
            if os.path.getsize(path) == 0:
                raise RuntimeError(f"SELF AUDIT FAILED: output file is zero bytes: {path}")

        report_path = output_paths["execution_report"]
        if not os.path.exists(report_path) or os.path.getsize(report_path) == 0:
            raise RuntimeError(f"SELF AUDIT FAILED: execution report missing or empty: {report_path}")

        log("SELF AUDIT PASSED: all output files exist, are non-empty, and valid.")
        log(f"PHASE5D complete. Total runtime: {total_runtime} seconds.")
        return 0

    except Exception as exc:
        log(f"FATAL ERROR: {exc}")
        traceback.print_exc()
        # Best-effort: still write whatever audit information was collected
        try:
            schema_audit.record_error(str(exc))
            schema_audit.finalize(passed=False)
            with open(os.path.join(BASE_DIR, OUTPUT_FILES["schema_audit"]), "w") as f:
                json.dump(schema_audit.audit, f, indent=2, default=str)
        except Exception:
            pass
        try:
            runtime_audit["error"] = str(exc)
            runtime_audit["runtime_seconds"] = round(time.time() - start_time, 4)
            with open(os.path.join(BASE_DIR, OUTPUT_FILES["runtime_audit"]), "w") as f:
                json.dump(runtime_audit, f, indent=2, default=str)
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())