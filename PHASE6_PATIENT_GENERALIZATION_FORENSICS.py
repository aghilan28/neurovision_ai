#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE6_PATIENT_GENERALIZATION_FORENSICS.py
==========================================
Production-grade standalone script.

Mission: Determine WHY specific patients fail generalization
         despite all previous threshold/calibration/smoothing
         optimizations having been completed.

Primary targets  : CHB14, CHB22
Secondary target : CHB02
Reference (good) : CHB05, CHB09

All schema, splits, feature names, and counts are discovered
dynamically — nothing is hardcoded.

FIXES vs original:
  FIX-1 : IsotonicRegression called with 1D arrays (not reshaped to -1,1)
  FIX-2 : Patient split reads "val_patients" fallback when "calibration_patients" absent
  FIX-3 : Feature importance schema discovered dynamically (feature_name/gain/weight etc.)
  FIX-4 : Memory strategy — train rows are summarised per-feature (mean/std/percentiles)
           rather than kept in RAM; only calib+test patients loaded as full DataFrames
  FIX-5 : FN reconstruction mirrors Phase5C pipeline (smooth→threshold→duration→peak)
  FIX-6 : Train reference built from cached per-feature statistics, not raw concat
  FIX-7 : Feature shift runtime — documented; no code change required
  FIX-8 : Production settings loaded from Phase5E/Phase5C JSON artefacts first;
           constants used only as fallback
  FIX-9 : Exact feature name order validated against model.feature_names_in_ before
           any inference call
  FIX-10: Implemented true Algorithm-R reservoir sampling for training metrics (Unbiased)
  FIX-11: Replaced inner-loop pd.concat reallocations with an append-then-concat strategy
  FIX-12: Hardened Feature-order checking to FAIL the script instead of WARN on mismatch
  FIX-13: Added column existence check for "duration_windows" in Root Cause analysis.
"""

# ─────────────────────────────────────────────────────────────────────────────
# STDLIB
# ─────────────────────────────────────────────────────────────────────────────
import gc
import json
import math
import os
import platform
import sys
import time
import traceback
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# THIRD-PARTY  (checked at runtime with clear error messages)
# ─────────────────────────────────────────────────────────────────────────────
def _require(pkg, import_as=None):
    import importlib
    name = import_as or pkg
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError:
        print(f"[FATAL] Required package '{pkg}' is not installed. "
              f"Run: pip install {pkg}", file=sys.stderr)
        sys.exit(1)

np       = _require("numpy")
pd       = _require("pandas")
scipy    = _require("scipy")
joblib   = _require("joblib")
sklearn  = _require("scikit-learn", "sklearn")
xgb      = _require("xgboost")
pyarrow  = _require("pyarrow")

from scipy import stats
from scipy.stats import ks_2samp, wasserstein_distance
from sklearn.isotonic import IsotonicRegression

import tracemalloc

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS / PATHS  (all dynamic — nothing hardcoded about schema/patients)
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent

# Input artefacts
PARQUET_PATH      = SCRIPT_DIR / "PHASE5B_ENGINEERED_DATASET.parquet"
MODEL_PATH        = SCRIPT_DIR / "PHASE5B_TEMPORAL_XGBOOST.joblib"
FEAT_SIG_PATH     = SCRIPT_DIR / "PHASE5B_FEATURE_SIGNATURE.json"
SPLIT_PATH        = SCRIPT_DIR / "PHASE5B_PATIENT_SPLIT.json"
FEAT_IMP_PATH     = SCRIPT_DIR / "PHASE5B_FEATURE_IMPORTANCE.csv"

# Optional Phase5D / Phase5E artefacts (script supports absence)
P5D_FN_EVENTS_PATH    = SCRIPT_DIR / "PHASE5D_FALSE_NEGATIVE_EVENTS.csv"
P5D_ROOT_CAUSE_PATH   = SCRIPT_DIR / "PHASE5D_ROOT_CAUSE_ANALYSIS.csv"
P5D_FAIL_SUMMARY_PATH = SCRIPT_DIR / "PHASE5D_PATIENT_FAILURE_SUMMARY.csv"
P5D_SHIFT_PATH        = SCRIPT_DIR / "PHASE5D_PATIENT_SHIFT_ANALYSIS.csv"
P5C_EVENT_PRED_PATH   = SCRIPT_DIR / "PHASE5C_EVENT_PREDICTIONS.csv"
P5C_EVENT_MET_PATH    = SCRIPT_DIR / "PHASE5C_EVENT_METRICS.csv"
P5C_BEST_CFG_PATH     = SCRIPT_DIR / "PHASE5C_BEST_CONFIGURATION.json"
P5E_PROD_REC_PATH     = SCRIPT_DIR / "PHASE5E_PRODUCTION_RECOMMENDATION.json"

# Phase 6 output artefacts
OUT = {
    "schema_discovery"        : SCRIPT_DIR / "PHASE6_SCHEMA_DISCOVERY.json",
    "feature_sig_audit"       : SCRIPT_DIR / "PHASE6_FEATURE_SIGNATURE_AUDIT.json",
    "patient_split_audit"     : SCRIPT_DIR / "PHASE6_PATIENT_SPLIT_AUDIT.json",
    "memory_audit"            : SCRIPT_DIR / "PHASE6_MEMORY_AUDIT.json",
    "model_audit"             : SCRIPT_DIR / "PHASE6_MODEL_AUDIT.json",
    "calibration_audit"       : SCRIPT_DIR / "PHASE6_CALIBRATION_AUDIT.json",
    "fn_audit"                : SCRIPT_DIR / "PHASE6_FN_AUDIT.json",
    "input_validation"        : SCRIPT_DIR / "PHASE6_INPUT_VALIDATION.json",
    "patient_performance"     : SCRIPT_DIR / "PHASE6_PATIENT_PERFORMANCE.csv",
    "feature_shift"           : SCRIPT_DIR / "PHASE6_FEATURE_SHIFT_ANALYSIS.csv",
    "chb14_forensics"         : SCRIPT_DIR / "PHASE6_CHB14_FORENSICS.csv",
    "chb22_forensics"         : SCRIPT_DIR / "PHASE6_CHB22_FORENSICS.csv",
    "chb02_forensics"         : SCRIPT_DIR / "PHASE6_CHB02_FORENSICS.csv",
    "good_vs_bad"             : SCRIPT_DIR / "PHASE6_GOOD_VS_BAD_PATIENTS.csv",
    "importance_shift"        : SCRIPT_DIR / "PHASE6_IMPORTANCE_SHIFT_ANALYSIS.csv",
    "fn_signature"            : SCRIPT_DIR / "PHASE6_FN_SIGNATURE_ANALYSIS.csv",
    "confidence_analysis"     : SCRIPT_DIR / "PHASE6_CONFIDENCE_ANALYSIS.csv",
    "root_cause_summary"      : SCRIPT_DIR / "PHASE6_ROOT_CAUSE_SUMMARY.csv",
    "remediation_plan"        : SCRIPT_DIR / "PHASE6_REMEDIATION_PLAN.json",
    "execution_report"        : SCRIPT_DIR / "PHASE6_EXECUTION_REPORT.txt",
    "runtime_audit"           : SCRIPT_DIR / "PHASE6_RUNTIME_AUDIT.json",
    "self_audit"              : SCRIPT_DIR / "PHASE6_SELF_AUDIT.json",
    "prod_config_audit"       : SCRIPT_DIR / "PHASE6_PROD_CONFIG_AUDIT.json",
    "feature_order_audit"     : SCRIPT_DIR / "PHASE6_FEATURE_ORDER_AUDIT.json",
    "train_feature_stats"     : SCRIPT_DIR / "PHASE6_TRAIN_FEATURE_STATS.csv",
}

PRIMARY_FAIL_PATIENTS   = ["chb14", "chb22"]
SECONDARY_FAIL_PATIENTS = ["chb02"]
GOOD_PATIENTS           = ["chb05", "chb09"]
ALL_FAIL_PATIENTS       = PRIMARY_FAIL_PATIENTS + SECONDARY_FAIL_PATIENTS

# ─────────────────────────────────────────────────────────────────────────────
# FIX-8: Production config — load from Phase5E/Phase5C artefacts; fallback to
#         these constants only if both files are absent.
# ─────────────────────────────────────────────────────────────────────────────
_FALLBACK_SMOOTHING_WINDOW     = 21
_FALLBACK_THRESHOLD            = 0.01
_FALLBACK_MIN_DURATION         = 1
_FALLBACK_MIN_PEAK_PROBABILITY = 0.95

# Will be populated by step0b_load_prod_config()
PROD_SMOOTHING_WINDOW     : int   = _FALLBACK_SMOOTHING_WINDOW
PROD_THRESHOLD            : float = _FALLBACK_THRESHOLD
PROD_MIN_DURATION         : int   = _FALLBACK_MIN_DURATION
PROD_MIN_PEAK_PROBABILITY : float = _FALLBACK_MIN_PEAK_PROBABILITY

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL STATE
# ─────────────────────────────────────────────────────────────────────────────
_log_lines: list[str] = []
_t0 = time.time()
tracemalloc.start()

def _elapsed() -> float:
    return round(time.time() - _t0, 3)

def _peak_mb() -> float:
    _, peak = tracemalloc.get_traced_memory()
    return round(peak / 1024 / 1024, 2)

def log(msg: str, *, level: str = "INFO") -> None:
    ts   = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    _log_lines.append(line)

def section(title: str) -> None:
    sep = "=" * 70
    log(sep)
    log(title)
    log(sep)

def write_json(path: Path, obj, *, indent: int = 2) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=indent, default=str)

def write_csv(path: Path, df: pd.DataFrame) -> None:
    df.to_csv(path, index=False, encoding="utf-8")

def safe_read_csv(path: Path, required_cols: list[str] = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    df = pd.read_csv(path, encoding="utf-8")
    if df.empty:
        raise ValueError(f"CSV is empty: {path}")
    dupes = [c for c in df.columns if list(df.columns).count(c) > 1]
    if dupes:
        raise ValueError(f"Duplicate columns in {path.name}: {dupes}")
    if required_cols:
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(
                f"Missing columns {missing} in {path.name}. "
                f"Available: {list(df.columns)}"
            )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 0a  PRE-FLIGHT INPUT VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
def step0a_input_validation() -> dict:
    section("STEP 0a — INPUT VALIDATION")
    report = {}

    mandatory = {
        "parquet"          : PARQUET_PATH,
        "model"            : MODEL_PATH,
        "feature_signature": FEAT_SIG_PATH,
        "patient_split"    : SPLIT_PATH,
    }
    optional = {
        "feature_importance"         : FEAT_IMP_PATH,
        "phase5d_fn_events"          : P5D_FN_EVENTS_PATH,
        "phase5d_root_cause"         : P5D_ROOT_CAUSE_PATH,
        "phase5d_patient_failure"    : P5D_FAIL_SUMMARY_PATH,
        "phase5d_patient_shift"      : P5D_SHIFT_PATH,
        "phase5c_event_predictions"  : P5C_EVENT_PRED_PATH,
        "phase5c_event_metrics"      : P5C_EVENT_MET_PATH,
        "phase5c_best_configuration" : P5C_BEST_CFG_PATH,
        "phase5e_production_rec"     : P5E_PROD_REC_PATH,
    }

    for key, path in mandatory.items():
        exists = path.exists()
        size   = path.stat().st_size if exists else 0
        status = "PASS" if exists and size > 0 else "FAIL"
        report[key] = {"path": str(path), "exists": exists, "size_bytes": size, "status": status}
        log(f"  [{status}] {key}: {path.name} ({size:,} bytes)")
        if status == "FAIL":
            raise RuntimeError(f"Mandatory input missing or empty: {path}")

    for key, path in optional.items():
        exists = path.exists()
        size   = path.stat().st_size if exists else 0
        status = "PRESENT" if exists and size > 0 else "ABSENT"
        report[key] = {"path": str(path), "exists": exists, "size_bytes": size, "status": status}
        log(f"  [{status}] {key}: {path.name}")

    csv_validation = {}
    for key, path in optional.items():
        if path.suffix == ".csv" and path.exists():
            try:
                df = safe_read_csv(path)
                csv_validation[path.name] = {
                    "rows": len(df), "cols": len(df.columns),
                    "columns": list(df.columns), "status": "PASS"
                }
            except Exception as e:
                csv_validation[path.name] = {"status": "FAIL", "error": str(e)}

    report["csv_validation"] = csv_validation
    write_json(OUT["input_validation"], report)
    log("  → PHASE6_INPUT_VALIDATION.json written")
    return report


# ─────────────────────────────────────────────────────────────────────────────
# STEP 0b  FIX-8: LOAD PRODUCTION CONFIG FROM PHASE5E / PHASE5C ARTEFACTS
# ─────────────────────────────────────────────────────────────────────────────
def step0b_load_prod_config() -> dict:
    """
    FIX-8: Derive production settings from saved Phase5E/Phase5C artefacts.
    Falls back to module-level constants only when files are absent.
    Writes PHASE6_PROD_CONFIG_AUDIT.json.
    """
    global PROD_SMOOTHING_WINDOW, PROD_THRESHOLD, PROD_MIN_DURATION, PROD_MIN_PEAK_PROBABILITY
    section("STEP 0b — PRODUCTION CONFIG DISCOVERY (FIX-8)")

    source = "FALLBACK_CONSTANTS"
    raw    = {}

    # Priority 1: Phase5E recommendation
    if P5E_PROD_REC_PATH.exists():
        try:
            with open(P5E_PROD_REC_PATH, encoding="utf-8") as fh:
                raw = json.load(fh)
            source = "PHASE5E_PRODUCTION_RECOMMENDATION.json"
            log(f"  Loaded production config from {source}")
        except Exception as e:
            log(f"  [WARN] Could not parse Phase5E file: {e}", level="WARN")
            raw = {}

    # Priority 2: Phase5C best configuration (fallback)
    if not raw and P5C_BEST_CFG_PATH.exists():
        try:
            with open(P5C_BEST_CFG_PATH, encoding="utf-8") as fh:
                raw = json.load(fh)
            source = "PHASE5C_BEST_CONFIGURATION.json"
            log(f"  Loaded production config from {source}")
        except Exception as e:
            log(f"  [WARN] Could not parse Phase5C file: {e}", level="WARN")
            raw = {}

    # Key name candidates (different phases used different keys)
    def _get(d: dict, *keys, default):
        for k in keys:
            if k in d:
                return d[k]
        return default

    PROD_SMOOTHING_WINDOW     = int(_get(
        raw, "smoothing_window", "window_size", "smoothing",
        default=_FALLBACK_SMOOTHING_WINDOW
    ))
    PROD_THRESHOLD            = float(_get(
        raw, "threshold", "prob_threshold", "decision_threshold",
        default=_FALLBACK_THRESHOLD
    ))
    PROD_MIN_DURATION         = int(_get(
        raw, "min_duration", "min_duration_windows", "min_event_duration",
        default=_FALLBACK_MIN_DURATION
    ))
    PROD_MIN_PEAK_PROBABILITY = float(_get(
        raw, "min_peak_probability", "peak_threshold", "mpp",
        default=_FALLBACK_MIN_PEAK_PROBABILITY
    ))

    audit = {
        "source"                 : source,
        "smoothing_window"       : PROD_SMOOTHING_WINDOW,
        "threshold"              : PROD_THRESHOLD,
        "min_duration"           : PROD_MIN_DURATION,
        "min_peak_probability"   : PROD_MIN_PEAK_PROBABILITY,
        "raw_keys_found"         : list(raw.keys())[:20],
    }
    write_json(OUT["prod_config_audit"], audit)
    log(f"  smoothing_window={PROD_SMOOTHING_WINDOW} | threshold={PROD_THRESHOLD} | "
        f"min_duration={PROD_MIN_DURATION} | mpp={PROD_MIN_PEAK_PROBABILITY}")
    log("  → PHASE6_PROD_CONFIG_AUDIT.json written")
    return audit


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1  DYNAMIC SCHEMA DISCOVERY
# ─────────────────────────────────────────────────────────────────────────────
def step1_schema_discovery(feat_names: list[str]) -> dict:
    section("STEP 1 — SCHEMA DISCOVERY")

    import pyarrow.parquet as pq
    pf = pq.ParquetFile(PARQUET_PATH)
    schema = pf.schema_arrow

    all_columns = [schema.field(i).name for i in range(len(schema))]
    log(f"  Parquet columns: {len(all_columns)}")
    log(f"  Parquet rows   : {pf.metadata.num_rows:,}")

    CANDIDATE_MAP = {
        "patient"           : ["patient", "pat", "patient_id", "subject"],
        "edf"               : ["edf", "edf_file", "filename", "file", "edf_name"],
        "label"             : ["label", "seizure", "seizure_label", "class", "y",
                               "target", "is_seizure"],
        "window_index"      : ["window_index", "windowindex", "win_idx", "idx",
                               "window_number", "window_num"],
        "window_start_sec"  : ["window_start_sec", "start_sec", "start_s",
                               "window_start", "t_start"],
        "window_end_sec"    : ["window_end_sec", "end_sec", "end_s",
                               "window_end", "t_end"],
    }

    col_lower  = {c.lower(): c for c in all_columns}
    mapping    = {}
    candidates_considered = {}
    ambiguities = {}

    for role, candidates in CANDIDATE_MAP.items():
        matched = []
        for cand in candidates:
            if cand.lower() in col_lower:
                matched.append(col_lower[cand.lower()])
        candidates_considered[role] = matched
        if len(matched) == 1:
            mapping[role] = matched[0]
            log(f"  [{role}] → '{matched[0]}'")
        elif len(matched) > 1:
            exact = [m for m in matched if m == candidates[0]]
            if len(exact) == 1:
                mapping[role] = exact[0]
                log(f"  [{role}] → '{exact[0]}' (resolved from ambiguity {matched})")
            else:
                ambiguities[role] = matched
                log(f"  [WARN] Ambiguous column for '{role}': {matched}", level="WARN")
        else:
            log(f"  [WARN] No column found for role '{role}'", level="WARN")

    if ambiguities:
        raise RuntimeError(
            f"Ambiguous schema — cannot silently choose. "
            f"Ambiguities: {ambiguities}. "
            f"Update CANDIDATE_MAP with the exact column names."
        )

    features_present = [f for f in feat_names if f in all_columns]
    features_missing = [f for f in feat_names if f not in all_columns]

    discovery = {
        "parquet_path"          : str(PARQUET_PATH),
        "parquet_total_columns" : len(all_columns),
        "parquet_total_rows"    : pf.metadata.num_rows,
        "column_mapping"        : mapping,
        "candidates_considered" : candidates_considered,
        "ambiguities"           : ambiguities,
        "feature_names_present" : len(features_present),
        "feature_names_missing" : len(features_missing),
        "missing_feature_names" : features_missing[:20],
        "all_columns_sample"    : all_columns[:30],
    }
    write_json(OUT["schema_discovery"], discovery)
    log(f"  Features present in parquet: {len(features_present)}/{len(feat_names)}")
    if features_missing:
        log(f"  [WARN] Missing features: {features_missing[:5]} …", level="WARN")
    log("  → PHASE6_SCHEMA_DISCOVERY.json written")
    return discovery


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2  FEATURE SIGNATURE AUDIT
# ─────────────────────────────────────────────────────────────────────────────
def step2_feature_audit(model) -> tuple[list[str], dict]:
    section("STEP 2 — FEATURE SIGNATURE AUDIT")

    with open(FEAT_SIG_PATH, encoding="utf-8") as fh:
        sig = json.load(fh)

    sig_count = sig["feature_count"]
    sig_names = sig["feature_names"]

    model_count = (
        model.n_features_in_
        if hasattr(model, "n_features_in_")
        else len(sig_names)
    )

    inner = model
    for attr in ("estimator", "base_estimator", "calibrated_classifiers_", "_final_estimator"):
        try:
            obj = getattr(inner, attr, None)
            if obj is not None:
                if hasattr(obj, "n_features_in_"):
                    model_count = obj.n_features_in_
                    inner = obj
                    break
                if isinstance(obj, list) and obj:
                    sub = obj[0]
                    if hasattr(sub, "estimator") and hasattr(sub.estimator, "n_features_in_"):
                        model_count = sub.estimator.n_features_in_
                        break
        except Exception:
            pass

    count_match = (sig_count == model_count)
    log(f"  Signature feature count : {sig_count}")
    log(f"  Model n_features_in_    : {model_count}")
    log(f"  Count match             : {count_match}")

    audit = {
        "signature_count"  : sig_count,
        "model_count"      : model_count,
        "count_match"      : count_match,
        "first_10_features": sig_names[:10],
        "last_5_features"  : sig_names[-5:],
        "status"           : "PASS" if count_match else "WARN",
    }
    write_json(OUT["feature_sig_audit"], audit)
    log("  → PHASE6_FEATURE_SIGNATURE_AUDIT.json written")
    return sig_names, audit


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3  PATIENT SPLIT AUDIT
# ─────────────────────────────────────────────────────────────────────────────
def step3_patient_split_audit() -> dict:
    section("STEP 3 — PATIENT SPLIT AUDIT")

    with open(SPLIT_PATH, encoding="utf-8") as fh:
        split = json.load(fh)

    train = [p.lower() for p in split["train_patients"]]
    calib = [p.lower() for p in (
        split.get("calibration_patients") or split.get("val_patients") or []
    )]  
    test  = [p.lower() for p in split["test_patients"]]

    overlap_tc = set(train) & set(calib)
    overlap_tt = set(train) & set(test)
    overlap_ct = set(calib) & set(test)

    primary_in_test   = [p for p in PRIMARY_FAIL_PATIENTS   if p in test]
    secondary_in_test = [p for p in SECONDARY_FAIL_PATIENTS if p in test]
    good_in_test      = [p for p in GOOD_PATIENTS           if p in test]

    calib_key_used = (
        "calibration_patients" if "calibration_patients" in split
        else "val_patients"    if "val_patients" in split
        else "NONE"
    )

    audit = {
        "calib_key_used"      : calib_key_used,
        "train_patients"      : train,
        "calibration_patients": calib,
        "test_patients"       : test,
        "train_rows"          : split.get("train_rows"),
        "val_rows"            : split.get("val_rows"),
        "test_rows"           : split.get("test_rows"),
        "overlap_train_calib" : list(overlap_tc),
        "overlap_train_test"  : list(overlap_tt),
        "overlap_calib_test"  : list(overlap_ct),
        "primary_fail_in_test"  : primary_in_test,
        "secondary_fail_in_test": secondary_in_test,
        "good_patients_in_test" : good_in_test,
        "no_overlap"          : (not overlap_tc and not overlap_tt and not overlap_ct),
        "status"              : "PASS" if not (overlap_tc or overlap_tt or overlap_ct) else "FAIL",
    }
    log(f"  Train: {len(train)} | Calib ({calib_key_used}): {len(calib)} | Test: {len(test)}")
    log(f"  No-overlap: {audit['no_overlap']}")
    log(f"  Primary-fail in test : {primary_in_test}")
    log(f"  Good patients in test: {good_in_test}")

    write_json(OUT["patient_split_audit"], audit)
    log("  → PHASE6_PATIENT_SPLIT_AUDIT.json written")
    return audit


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4  MEMORY-SAFE DATA LOADING  (FIX-4, FIX-10, FIX-11)
# ─────────────────────────────────────────────────────────────────────────────
def step4_load_data(
    col_map        : dict,
    feat_names     : list[str],
    train_patients : list[str],
    calib_patients : list[str],
    test_patients  : list[str],
) -> tuple[dict, dict, pd.DataFrame]:
    """
    FIX-4: Memory strategy.
    FIX-10: True Algorithm-R Reservoir Sampling implementation to guarantee statistical equivalence.
    FIX-11: Chunked-list append approach to eliminate nested inner-loop pd.concat reallocations.
    """
    section("STEP 4 — MEMORY-SAFE DATA LOADING (FIX-4, FIX-10, FIX-11)")

    import pyarrow.parquet as pq
    pf = pq.ParquetFile(PARQUET_PATH)

    meta_cols   = list(col_map.values())
    needed_cols = list(dict.fromkeys(meta_cols + feat_names))

    pat_col    = col_map["patient"]
    label_col  = col_map["label"]

    full_load_patients = list(dict.fromkeys(calib_patients + test_patients))
    train_set          = set(train_patients)

    log(f"  Full-load patients (calib+test): {full_load_patients}")
    log(f"  Train patients (stats-only):     {train_patients}")

    # FIX-11: Temporary dict of lists to hold chunks instead of iterative inner-loop pd.concat reallocations
    patient_chunks: dict[str, list[pd.DataFrame]] = {pat: [] for pat in full_load_patients}
    
    # Per-feature tracker for true online Algorithm-R reservoir sampling
    train_reservoir_size = 10_000
    train_reservoir: dict[str, np.ndarray] = {
        feat: np.empty(train_reservoir_size, dtype=np.float64) for feat in feat_names
    }
    # Keep track of individual counts for streaming index evaluation
    train_reservoir_counts: dict[str, int] = {feat: 0 for feat in feat_names}
    train_label_counts = {"n": 0, "pos": 0}

    rng = np.random.default_rng(seed=42)
    memory_before = _peak_mb()

    for batch in pf.iter_batches(batch_size=200_000, columns=needed_cols):
        df_batch = batch.to_pandas()
        df_batch[pat_col] = df_batch[pat_col].str.lower().str.strip()

        # ── Full-load patients ────────────────────────────────────────────
        for pat in full_load_patients:
            sub = df_batch[df_batch[pat_col] == pat]
            if not sub.empty:
                patient_chunks[pat].append(sub)  # FIX-11: Appending to a lightweight array list

        # ── Train patients: True Algorithm-R Reservoir Sampling ───────────
        train_batch = df_batch[df_batch[pat_col].isin(train_set)]
        if not train_batch.empty:
            train_label_counts["n"]   += len(train_batch)
            train_label_counts["pos"] += int(train_batch[label_col].sum())
            
            for feat in feat_names:
                if feat not in train_batch.columns:
                    continue
                vals = train_batch[feat].dropna().values
                if len(vals) == 0:
                    continue
                
                # Streaming replacement logic (Algorithm R)
                current_count = train_reservoir_counts[feat]
                res_arr = train_reservoir[feat]
                
                for val in vals:
                    if current_count < train_reservoir_size:
                        res_arr[current_count] = val
                    else:
                        # Unbiased probability distribution evaluation over absolute count N
                        idx = rng.integers(0, current_count + 1)
                        if idx < train_reservoir_size:
                            res_arr[idx] = val
                    current_count += 1
                
                train_reservoir_counts[feat] = current_count

        del df_batch
        gc.collect()

    # Terminal Phase of FIX-11: Perform single terminal consolidation concat operation outside the loop
    patient_dfs: dict[str, pd.DataFrame] = {}
    for pat in full_load_patients:
        chunks = patient_chunks[pat]
        if chunks:
            patient_dfs[pat] = pd.concat(chunks, ignore_index=True)
        else:
            patient_dfs[pat] = pd.DataFrame(columns=needed_cols)

    memory_after = _peak_mb()

    # Build train feature stats DataFrame from true reservoir sample arrays
    log("  Computing train feature statistics from true Algorithm-R reservoir sample arrays …")
    stat_rows = []
    final_reservoir_map = {}
    
    for feat in feat_names:
        total_seen = train_reservoir_counts[feat]
        filled_size = min(total_seen, train_reservoir_size)
        vals = train_reservoir[feat][:filled_size]
        final_reservoir_map[feat] = vals
        
        if len(vals) == 0:
            stat_rows.append({
                "feature": feat, "n": 0,
                "mean": np.nan, "std": np.nan,
                "p1": np.nan, "p5": np.nan, "p25": np.nan,
                "p50": np.nan, "p75": np.nan, "p95": np.nan, "p99": np.nan,
                "min": np.nan, "max": np.nan,
            })
        else:
            stat_rows.append({
                "feature": feat, "n": len(vals),
                "mean"  : float(np.mean(vals)),
                "std"   : float(np.std(vals)),
                "p1"    : float(np.percentile(vals, 1)),
                "p5"    : float(np.percentile(vals, 5)),
                "p25"   : float(np.percentile(vals, 25)),
                "p50"   : float(np.percentile(vals, 50)),
                "p75"   : float(np.percentile(vals, 75)),
                "p95"   : float(np.percentile(vals, 95)),
                "p99"   : float(np.percentile(vals, 99)),
                "min"   : float(np.min(vals)),
                "max"   : float(np.max(vals)),
            })

    train_feat_stats = pd.DataFrame(stat_rows)
    write_csv(OUT["train_feature_stats"], train_feat_stats)
    log(f"  → PHASE6_TRAIN_FEATURE_STATS.csv written ({len(train_feat_stats)} features)")

    # Attaching the unbiased reservoir arrays via a side-channel lookup dictionary attribute
    train_feat_stats._reservoir = final_reservoir_map

    row_counts  = {p: len(df) for p, df in patient_dfs.items()}
    total_rows  = sum(row_counts.values())
    log(f"  Full-load total rows: {total_rows:,}")
    for p, n in sorted(row_counts.items()):
        log(f"    {p}: {n:,} rows")

    memory_audit = {
        "parquet_size_gb"           : round(PARQUET_PATH.stat().st_size / 1e9, 3),
        "columns_loaded"            : len(needed_cols),
        "full_load_patients"        : list(row_counts.keys()),
        "train_patients_stats_only" : train_patients,
        "total_rows_full_loaded"    : total_rows,
        "train_reservoir_size"      : train_reservoir_size,
        "train_label_n"             : train_label_counts["n"],
        "train_label_pos"           : train_label_counts["pos"],
        "row_counts"                : row_counts,
        "peak_mb_before"            : memory_before,
        "peak_mb_after"             : memory_after,
        "strategy"                  : "TRUE_ALGORITHM_R_RESERVOIR_CONCAT_OPTIMIZED",
        "status"                    : "PASS",
    }
    write_json(OUT["memory_audit"], memory_audit)
    log("  → PHASE6_MEMORY_AUDIT.json written")
    return patient_dfs, memory_audit, train_feat_stats


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5  MODEL AUDIT & LOAD + FIX-9, FIX-12: STRICT ORDER VALIDATION FAIL
# ─────────────────────────────────────────────────────────────────────────────
def step5_model_audit(feat_names: list[str]) -> tuple:
    """
    FIX-9: Extract feature ordering metrics.
    FIX-12: Hardened validation pipeline. Converts loose WARN states into absolute script FAIL on discrepancy.
    """
    section("STEP 5 — MODEL AUDIT + FEATURE ORDER INTEGRITY DISCOVERY (FIX-9, FIX-12)")
    model = joblib.load(MODEL_PATH)
    model_type = type(model).__name__

    n_feat_in      : int | None       = getattr(model, "n_features_in_", None)
    model_feat_names: list[str] | None = None

    if hasattr(model, "feature_names_in_"):
        model_feat_names = list(model.feature_names_in_)

    for attr in ("estimator", "base_estimator"):
        sub = getattr(model, attr, None)
        if sub is None:
            continue
        if n_feat_in is None and hasattr(sub, "n_features_in_"):
            n_feat_in = sub.n_features_in_
        if model_feat_names is None and hasattr(sub, "feature_names_in_"):
            model_feat_names = list(sub.feature_names_in_)

    try:
        booster = None
        if hasattr(model, "get_booster"):
            booster = model.get_booster()
        elif hasattr(model, "estimator") and hasattr(model.estimator, "get_booster"):
            booster = model.estimator.get_booster()

        if booster is not None:
            xgb_feat_names = booster.feature_names
            if xgb_feat_names and model_feat_names is None:
                model_feat_names = list(xgb_feat_names)
    except Exception as e:
        log(f"  [WARN] Could not extract booster feature names: {e}", level="WARN")

    expected_count = len(feat_names)
    count_ok       = (n_feat_in is None) or (n_feat_in == expected_count)

    order_ok        = True
    order_mismatch  = []
    first_mismatch  = None

    if model_feat_names is not None:
        if len(model_feat_names) != len(feat_names):
            order_ok = False
            first_mismatch = (
                f"Length mismatch: signature={len(feat_names)} "
                f"model={len(model_feat_names)}"
            )
        else:
            for idx, (s_f, m_f) in enumerate(zip(feat_names, model_feat_names)):
                if s_f != m_f:
                    order_ok = False
                    order_mismatch.append({"idx": idx, "sig": s_f, "model": m_f})
            if order_mismatch:
                first_mismatch = (
                    f"Name mismatch at idx {order_mismatch[0]['idx']}: "
                    f"sig='{order_mismatch[0]['sig']}', model='{order_mismatch[0]['model']}'"
                )

    audit_feat_order = {
        "model_feature_names_found": model_feat_names is not None,
        "count_match"             : count_ok,
        "order_match"             : order_ok,
        "total_mismatches"        : len(order_mismatch),
        "first_mismatch"          : first_mismatch,
        "mismatch_samples"        : order_mismatch[:5],
    }
    write_json(OUT["feature_order_audit"], audit_feat_order)

    # FIX-12 Applied: Convert Warning checks into terminal Pipeline failures
    if model_feat_names is not None:
        if not order_ok:
            log(f"  [FAIL] Feature-order mismatch detected! First failure condition: {first_mismatch}", level="ERROR")
            raise RuntimeError(f"CRITICAL FORENSIC FAILURE: Feature name sequence mismatch against model metadata. Error: {first_mismatch}")
        else:
            log("  [PASS] Feature-order sequence verified against model metadata.")
    else:
        # If feature names metadata block isn't exposed by internal wrapper layers, we still require count verification
        if not count_ok:
            log(f"  [FAIL] Feature count mismatch! Model has {n_feat_in} features, expected {expected_count}", level="ERROR")
            raise RuntimeError(f"CRITICAL FORENSIC FAILURE: Feature tracking total count mismatch: Model={n_feat_in} vs Sig={expected_count}")
        log("  [WARN] feature_names_in_ not exposed by model wrapper pipeline. Verified count matches signature.", level="WARN")

    audit_model = {
        "model_type"       : model_type,
        "n_features_in"    : n_feat_in,
        "has_predict_proba": hasattr(model, "predict_proba"),
        "status"           : "PASS"
    }
    write_json(OUT["model_audit"], audit_model)
    log("  → PHASE6_MODEL_AUDIT.json and PHASE6_FEATURE_ORDER_AUDIT.json written")
    return model, audit_model


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6  CALIBRATION RECONSTRUCTION AUDIT
# ─────────────────────────────────────────────────────────────────────────────
def step6_calibration_audit(patient_dfs: dict, col_map: dict, feat_names: list[str], model) -> IsotonicRegression | None:
    """
    Documentary Track (Concern #4): Reconstructs Platt Scaling or Isotonic curves.
    Note: Direct calibrator fitting on internal calibration streams matches tracking mechanics.
    If the deployment target encapsulated CalibratedClassifierCV or cross-validated Platt estimators,
    this step acts as a baseline proxy for structural verification.
    """
    section("STEP 6 — CALIBRATION RECONSTRUCTION (Concern #4 Track)")
    pat_col   = col_map["patient"]
    label_col = col_map["label"]

    calib_pats = [p for p, df in patient_dfs.items() if p not in ALL_FAIL_PATIENTS and p not in GOOD_PATIENTS]
    if not calib_pats:
        log("  No explicit calibration patients found in dataframe maps. Defaulting to raw probabilities.")
        write_json(OUT["calibration_audit"], {"status": "ABSENT", "msg": "No calibration patients discovered"})
        return None

    log(f"  Constructing Isotonic mapping on patients: {calib_pats}")
    raw_probs_list = []
    y_list = []

    for pat in calib_pats:
        df = patient_dfs[pat]
        X  = df[feat_names].values.astype(np.float32)
        probs = model.predict_proba(X)[:, 1]
        raw_probs_list.append(probs)
        y_list.append(df[label_col].values.astype(int))

    raw_probs = np.concatenate(raw_probs_list).astype(np.float64)
    y_cal     = np.concatenate(y_list).astype(np.float64)

    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.fit(raw_probs, y_cal)

    test_points = np.linspace(0.0, 1.0, 11)
    cal_points  = calibrator.predict(test_points) # FIX-1: 1-D safe

    audit = {
        "calibration_patients": calib_pats,
        "total_calibration_rows": len(raw_probs),
        "curve_mapping": [{"raw": float(r), "calibrated": float(c)} for r, c in zip(test_points, cal_points)],
        "note": "Proxy reconstruction matching fit structure. Standard CalibratedClassifierCV/Platt details noted.",
        "status": "PASS"
    }
    write_json(OUT["calibration_audit"], audit)
    log("  → PHASE6_CALIBRATION_AUDIT.json written")
    return calibrator


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7  PROBABILITY GENERATION
# ─────────────────────────────────────────────────────────────────────────────
def step7_generate_probabilities(patient_dfs: dict, feat_names: list[str], model, calibrator) -> dict:
    section("STEP 7 — PROBABILITY GENERATION (FIX-1 applied)")
    prob_store: dict[str, np.ndarray] = {}
    for pat, df in patient_dfs.items():
        X = df[feat_names].values.astype(np.float32)
        raw = model.predict_proba(X)[:, 1]
        if calibrator is not None:
            cal = calibrator.predict(raw) # FIX-1 verified
        else:
            cal = raw
        prob_store[pat] = cal
        log(f"  {pat}: {len(cal):,} probs | max={cal.max():.4f} | mean={cal.mean():.5f}")
    return prob_store


# ─────────────────────────────────────────────────────────────────────────────
# STEP 8  FN AUDIT — FIX-5: Mirrors Phase5C pipeline
# ─────────────────────────────────────────────────────────────────────────────
def _apply_phase5c_pipeline(
    probs            : np.ndarray,
    smoothing_window : int,
    threshold        : float,
    min_duration     : int,
    min_peak_prob    : float,
) -> list[dict]:
    n = len(probs)
    if n == 0:
        return []

    # 1. Smoothing
    if smoothing_window > 1:
        kernel = np.ones(smoothing_window) / smoothing_window
        smoothed = np.convolve(probs, kernel, mode="same")
    else:
        smoothed = probs.copy()

    # 2. Threshold
    above = smoothed >= threshold

    # 3. Group contiguous candidate windows
    events = []
    in_event = False
    ev_start = 0

    for i in range(n):
        if above[i] and not in_event:
            in_event = True
            ev_start = i
        elif not above[i] and in_event:
            events.append({"start": ev_start, "end": i - 1})
            in_event = False
    if in_event:
        events.append({"start": ev_start, "end": n - 1})

    # 4 & 5. Apply min_duration and min_peak_probability filters
    filtered_events = []
    for ev in events:
        dur = (ev["end"] - ev["start"]) + 1
        if dur < min_duration:
            continue
        peak_val = float(probs[ev["start"]:ev["end"] + 1].max())
        if peak_val < min_peak_prob:
            continue
        ev["duration_windows"] = dur
        ev["peak_probability"] = peak_val
        filtered_events.append(ev)

    return filtered_events


def step8_fn_audit(patient_dfs: dict, prob_store: dict, col_map: dict) -> tuple[pd.DataFrame, dict]:
    section("STEP 8 — FALSE NEGATIVE RECONSTRUCTION AUDIT (FIX-5)")
    label_col = col_map["label"]
    fn_df     = pd.DataFrame()
    source    = "RECONSTRUCTED_VIA_PHASE5C_PIPELINE"

    if P5D_FN_EVENTS_PATH.exists():
        fn_df = safe_read_csv(P5D_FN_EVENTS_PATH)
        source = "PHASE5D_FALSE_NEGATIVE_EVENTS.csv"
        log(f"  Loaded FN events from Phase5D: {len(fn_df)} rows")
    else:
        log("  Phase5D FN file not found — reconstructing via Phase5C pipeline")
        log(f"  Pipeline: smooth={PROD_SMOOTHING_WINDOW} | thr={PROD_THRESHOLD} | "
            f"min_dur={PROD_MIN_DURATION} | mpp={PROD_MIN_PEAK_PROBABILITY}")
        rows = []
        for pat in patient_dfs:
            df = patient_dfs[pat]
            prb = prob_store[pat]
            if label_col not in df.columns:
                continue
            labels = df[label_col].astype(int).values

            detected_events = _apply_phase5c_pipeline(
                prb,
                smoothing_window = PROD_SMOOTHING_WINDOW,
                threshold        = PROD_THRESHOLD,
                min_duration     = PROD_MIN_DURATION,
                min_peak_prob    = PROD_MIN_PEAK_PROBABILITY,
            )

            detected_set = set()
            for ev in detected_events:
                for idx in range(ev["start"], ev["end"] + 1):
                    detected_set.add(idx)

            gt_events = []
            in_ev = False
            ev_start_gt = 0
            for i, lbl in enumerate(labels):
                if lbl == 1 and not in_ev:
                    in_ev = True
                    ev_start_gt = i
                elif lbl == 0 and in_ev:
                    gt_events.append((ev_start_gt, i - 1))
                    in_ev = False
            if in_ev:
                gt_events.append((ev_start_gt, len(labels) - 1))

            for gt_start, gt_end in gt_events:
                overlap = False
                for idx in range(gt_start, gt_end + 1):
                    if idx in detected_set:
                        overlap = True
                        break
                if not overlap:
                    rows.append({
                        "patient": pat,
                        "gt_start_window": gt_start,
                        "gt_end_window": gt_end,
                        "duration_windows": (gt_end - gt_start) + 1,
                        "max_prob_in_gt": float(prb[gt_start:gt_end + 1].max()) if gt_end >= gt_start else 0.0
                    })

        fn_df = pd.DataFrame(rows)
        write_csv(OUT["fn_audit"], fn_df)

    audit = {
        "source": source,
        "total_false_negative_events": len(fn_df),
        "breakdown_by_patient": fn_df["patient"].value_counts().to_dict() if not fn_df.empty else {},
        "status": "PASS"
    }
    write_json(OUT["fn_audit"].with_suffix(".json"), audit)
    log(f"  Total reconstructed false negative events: {len(fn_df)}")
    log("  → PHASE6_FN_AUDIT.json written")
    return fn_df, audit


# ─────────────────────────────────────────────────────────────────────────────
# STEP 9 PATIENT-LEVEL PERFORMANCE PROFILE
# ─────────────────────────────────────────────────────────────────────────────
def step9_patient_performance(patient_dfs: dict, prob_store: dict, col_map: dict) -> pd.DataFrame:
    section("STEP 9 — PATIENT-LEVEL PERFORMANCE PROFILING")
    label_col = col_map["label"]
    rows = []

    for pat, df in sorted(patient_dfs.items()):
        prb = prob_store[pat]
        lbl = df[label_col].astype(int).values
        n_pos = int(lbl.sum())
        n_neg = int((lbl == 0).sum())
        n_tot = len(lbl)
        pos_rate = n_pos / n_tot if n_tot else 0

        prob_pos = prb[lbl == 1] if n_pos > 0 else np.array([])
        prob_neg = prb[lbl == 0] if n_neg > 0 else np.array([])

        def _safe_stat(arr, fn):
            return float(fn(arr)) if len(arr) > 0 else float("nan")

        rows.append({
            "patient"            : pat,
            "category"           : (
                "PRIMARY_FAIL" if pat in PRIMARY_FAIL_PATIENTS
                else "SECONDARY_FAIL" if pat in SECONDARY_FAIL_PATIENTS
                else "GOOD" if pat in GOOD_PATIENTS
                else "CALIB"
            ),
            "total_windows"      : n_tot,
            "positive_windows"   : n_pos,
            "negative_windows"   : n_neg,
            "positive_rate"      : round(pos_rate, 6),
            "prob_mean_all"      : round(_safe_stat(prb, np.mean), 6),
            "prob_median_all"    : round(_safe_stat(prb, np.median), 6),
            "prob_std_all"       : round(_safe_stat(prb, np.std), 6),
            "prob_max_all"       : round(_safe_stat(prb, np.max), 6),
            "prob_p95_all"       : round(_safe_stat(prb, lambda x: np.percentile(x, 95)), 6),
            "prob_mean_positive" : round(_safe_stat(prob_pos, np.mean), 6),
            "prob_max_positive"  : round(_safe_stat(prob_pos, np.max), 6),
            "prob_mean_negative" : round(_safe_stat(prob_neg, np.mean), 6),
        })

    perf_df = pd.DataFrame(rows)
    write_csv(OUT["patient_performance"], perf_df)
    log(f"  → PHASE6_PATIENT_PERFORMANCE.csv written ({len(perf_df)} rows)")
    return perf_df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 10 STREAMING PASS COGNIZANT SHIFT ANALYSIS (FIX-6)
# ─────────────────────────────────────────────────────────────────────────────
def step10_feature_shift(patient_dfs: dict, feat_names: list[str], train_feat_stats: pd.DataFrame) -> pd.DataFrame:
    """
    FIX-6: Reference values extracted from unbiased true Algorithm-R reservoir cache map structure.
    """
    section("STEP 10 — FEATURE SHIFT COGNIZANT RUNTIME AUDIT (FIX-6)")
    reservoir = getattr(train_feat_stats, "_reservoir", {})
    rows = []

    target_patients = ALL_FAIL_PATIENTS + GOOD_PATIENTS
    log(f"  Analyzing shifts for target patients: {target_patients}")

    total = len(feat_names)
    for feat_idx, feat in enumerate(feat_names):
        if feat_idx % 100 == 0:
            log(f"    ... feature {feat_idx}/{total}")

        train_vals = reservoir.get(feat, np.array([]))
        if len(train_vals) == 0:
            continue

        for pat in target_patients:
            if pat not in patient_dfs:
                continue
            pat_df = patient_dfs[pat]
            pat_vals = pat_df[feat].dropna().values if feat in pat_df.columns else np.array([])
            if len(pat_vals) == 0:
                continue

            ks_stat, ks_pval = ks_2samp(train_vals, pat_vals)
            w_dist           = wasserstein_distance(train_vals, pat_vals)

            mean_shift      = float(np.mean(pat_vals) - np.mean(train_vals))
            var_shift       = float(np.var(pat_vals) - np.var(train_vals))
            std_ref         = float(np.std(train_vals))
            mean_shift_norm = mean_shift / std_ref if std_ref > 1e-9 else float("nan")

            rows.append({
                "feature"           : feat,
                "patient"           : pat,
                "ks_statistic"      : round(float(ks_stat), 6),
                "ks_pvalue"         : round(float(ks_pval), 6),
                "wasserstein"       : round(float(w_dist), 6),
                "mean_shift"        : round(mean_shift, 6),
                "mean_shift_normed" : round(mean_shift_norm, 6),
                "var_shift"         : round(var_shift, 6),
                "train_mean"        : round(float(np.mean(train_vals)), 6),
                "train_std"         : round(float(np.std(train_vals)), 6),
                "pat_mean"          : round(float(np.mean(pat_vals)), 6),
                "pat_std"           : round(float(np.std(pat_vals)), 6),
            })

    shift_df = pd.DataFrame(rows)
    write_csv(OUT["feature_shift"], shift_df)
    log(f"  → PHASE6_FEATURE_SHIFT_ANALYSIS.csv written ({len(shift_df)} rows)")
    return shift_df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 11 DEEP FORENSICS
# ─────────────────────────────────────────────────────────────────────────────
def _generate_individual_forensics(
    pat             : str,
    df              : pd.DataFrame,
    prb             : np.ndarray,
    col_map         : dict,
    feat_names      : list[str],
    fn_df           : pd.DataFrame,
    train_vals_dict : dict,
    out_path        : Path,
) -> pd.DataFrame:
    label_col = col_map["label"]
    labels    = df[label_col].astype(int).values
    pat_fn    = fn_df[fn_df["patient"] == pat] if not fn_df.empty else pd.DataFrame()

    fn_windows = set()
    if not pat_fn.empty:
        for _, r in pat_fn.iterrows():
            for w in range(int(r["gt_start_window"]), int(r["gt_end_window"]) + 1):
                if w < len(labels):
                    fn_windows.add(w)

    rows = []
    for feat in feat_names:
        if feat not in df.columns:
            continue
        vals = df[feat].values
        train_vals = train_vals_dict.get(feat, np.array([]))

        pos_vals = vals[labels == 1]
        neg_vals = vals[labels == 0]
        fn_vals  = vals[list(fn_windows & set(range(len(vals))))] if fn_windows else np.array([])

        def _m(a):  return float(np.mean(a)) if len(a) > 0 else float("nan")
        def _s(a):  return float(np.std(a))  if len(a) > 0 else float("nan")
        def _mx(a): return float(np.max(a))  if len(a) > 0 else float("nan")

        ks_stat, ks_pval = float("nan"), float("nan")
        w_dist = float("nan")
        if len(train_vals) > 0 and len(vals) > 0:
            ks_stat, ks_pval = ks_2samp(train_vals, vals)
            w_dist = wasserstein_distance(train_vals, vals)

        sep_stat, sep_pval = float("nan"), float("nan")
        if len(pos_vals) > 0 and len(neg_vals) > 0:
            sep_stat, sep_pval = ks_2samp(pos_vals, neg_vals)

        rows.append({
            "feature"                       : feat,
            "mean_all"                      : round(_m(vals), 6),
            "std_all"                       : round(_s(vals), 6),
            "mean_seizure"                  : round(_m(pos_vals), 6),
            "mean_non_seizure"              : round(_m(neg_vals), 6),
            "std_seizure"                   : round(_s(pos_vals), 6),
            "std_non_seizure"               : round(_s(neg_vals), 6),
            "max_seizure"                   : round(_mx(pos_vals), 6),
            "ks_vs_train"                   : round(ks_stat, 6) if not math.isnan(ks_stat) else float("nan"),
            "ks_pval_vs_train"              : round(ks_pval, 6) if not math.isnan(ks_pval) else float("nan"),
            "wasserstein_vs_train"          : round(w_dist, 6) if not math.isnan(w_dist) else float("nan"),
            "ks_seizure_vs_nonseizure"      : round(float(sep_stat), 6) if not math.isnan(sep_stat) else float("nan"),
            "ks_pval_seizure_vs_nonseizure" : round(float(sep_pval), 6) if not math.isnan(sep_pval) else float("nan"),
        })

    foren_df = pd.DataFrame(rows).sort_values("ks_vs_train", ascending=False)
    write_csv(out_path, foren_df)
    log(f"  → {out_path.name} written ({len(foren_df)} features)")
    return foren_df


def step11_deep_forensics(
    patient_dfs      : dict,
    prob_store       : dict,
    col_map          : dict,
    feat_names       : list[str],
    fn_df            : pd.DataFrame,
    train_feat_stats : pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    section("STEP 11 — PER-PATIENT DEEP FORENSICS (FIX-6)")
    forensics: dict[str, pd.DataFrame] = {}
    targets = [
        ("chb14", OUT["chb14_forensics"]),
        ("chb22", OUT["chb22_forensics"]),
        ("chb02", OUT["chb02_forensics"]),
    ]

    reservoir = getattr(train_feat_stats, "_reservoir", {})

    for pat, out_path in targets:
        if pat not in patient_dfs:
            continue
        log(f"  Generating deep forensic profile for: {pat}")
        df  = patient_dfs[pat]
        prb = prob_store[pat]
        forensics[pat] = _generate_individual_forensics(
            pat, df, prb, col_map, feat_names, fn_df, reservoir, out_path
        )
    return forensics


# ─────────────────────────────────────────────────────────────────────────────
# STEP 12 GOOD VS BAD PATIENTS DETAILED METRIC GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def step12_good_vs_bad(patient_dfs: dict, prob_store: dict, col_map: dict, feat_names: list[str]) -> pd.DataFrame:
    section("STEP 12 — GOOD VS BAD PATIENT ALIGNMENT ANALYSIS")
    label_col = col_map["label"]

    good_dfs = [patient_dfs[p] for p in GOOD_PATIENTS if p in patient_dfs]
    bad_dfs  = [patient_dfs[p] for p in ALL_FAIL_PATIENTS if p in patient_dfs]

    if not good_dfs or not bad_dfs:
        log("  [WARN] Missing good or bad patients. Good vs Bad table cannot be constructed.", level="WARN")
        empty = pd.DataFrame(columns=["feature", "ks_all_windows"])
        write_csv(OUT["good_vs_bad"], empty)
        return empty

    good_df = pd.concat(good_dfs, ignore_index=True)
    bad_df  = pd.concat(bad_dfs, ignore_index=True)

    rows = []
    for feat in feat_names:
        if feat not in good_df.columns or feat not in bad_df.columns:
            continue

        g_all = good_df[feat].dropna().values
        b_all = bad_df[feat].dropna().values

        g_pos = good_df[good_df[label_col] == 1][feat].dropna().values
        b_pos = bad_df[bad_df[label_col] == 1][feat].dropna().values

        if len(g_all) == 0 or len(b_all) == 0:
            continue

        ks_all, ks_all_p = ks_2samp(g_all, b_all)
        w_all            = wasserstein_distance(g_all, b_all)

        ks_pos, ks_pos_p = float("nan"), float("nan")
        w_pos            = float("nan")
        if len(g_pos) > 0 and len(b_pos) > 0:
            ks_pos, ks_pos_p = ks_2samp(g_pos, b_pos)
            w_pos            = float(wasserstein_distance(g_pos, b_pos))

        rows.append({
            "feature"             : feat,
            "good_mean_all"       : round(float(np.mean(g_all)) if len(g_all) else float("nan"), 6),
            "bad_mean_all"        : round(float(np.mean(b_all)) if len(b_all) else float("nan"), 6),
            "good_mean_seizure"   : round(float(np.mean(g_pos)) if len(g_pos) else float("nan"), 6),
            "bad_mean_seizure"    : round(float(np.mean(b_pos)) if len(b_pos) else float("nan"), 6),
            "ks_all_windows"      : round(ks_all, 6) if not math.isnan(ks_all) else float("nan"),
            "ks_pval_all"         : round(ks_all_p, 6) if not math.isnan(ks_all_p) else float("nan"),
            "ks_seizure_windows"  : round(ks_pos, 6) if not math.isnan(ks_pos) else float("nan"),
            "ks_pval_seizure"     : round(ks_pos_p, 6) if not math.isnan(ks_pos_p) else float("nan"),
            "wasserstein_all"     : round(w_all, 6) if not math.isnan(w_all) else float("nan"),
            "wasserstein_seizure" : round(w_pos, 6) if not math.isnan(w_pos) else float("nan"),
        })

    gvb_df = pd.DataFrame(rows).sort_values("ks_seizure_windows", ascending=False, na_position="last")
    write_csv(OUT["good_vs_bad"], gvb_df)
    log(f"  → PHASE6_GOOD_VS_BAD_PATIENTS.csv written ({len(gvb_df)} features)")
    return gvb_df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 13 IMPORTANCE × SHIFT ANALYSIS (FIX-3)
# ─────────────────────────────────────────────────────────────────────────────
def step13_importance_shift(shift_df: pd.DataFrame) -> pd.DataFrame:
    """
    FIX-3: Feature importance column names are discovered dynamically.
    """
    section("STEP 13 — DYNAMIC FEATURE IMPORTANCE × SHIFT CROSS-AUDIT (FIX-3)")
    if not FEAT_IMP_PATH.exists():
        log("  [WARN] Feature importance CSV missing. Creating mock weights.", level="WARN")
        mock = pd.DataFrame({"feature": shift_df["feature"].unique(), "importance": 1.0})
        imp_df, imp_col, feat_col = mock, "importance", "feature"
    else:
        imp_df = pd.read_csv(FEAT_IMP_PATH)
        c_low  = {c.lower(): c for c in imp_df.columns}

        feat_col = None
        for cand in ["feature", "feature_name", "name", "feat", "features"]:
            if cand in c_low:
                feat_col = c_low[cand]
                break

        imp_col = None
        for cand in ["importance", "gain", "weight", "importance_score", "score", "fscore"]:
            if cand in c_low:
                imp_col = c_low[cand]
                break

        if not feat_col or not imp_col:
            log(f"  [WARN] Mapping failed on {imp_df.columns}. Defaulting to col-0 and col-1.", level="WARN")
            feat_col = imp_df.columns[0]
            imp_col  = imp_df.columns[1]

    log(f"  Resolved mapping schema: key_column='{feat_col}' | importance_column='{imp_col}'")

    imp_sub = imp_df[[feat_col, imp_col]].copy()
    imp_sub.columns = ["feature", "importance"]
    imp_sub["feature"] = imp_sub["feature"].astype(str).str.strip()

    agg_shift = shift_df.groupby("feature").agg(
        mean_ks_stat           = ("ks_statistic", "mean"),
        max_ks_stat            = ("ks_statistic", "max"),
        mean_wasserstein       = ("wasserstein", "mean"),
        mean_mean_shift_normed = ("mean_shift_normed", lambda x: np.abs(x).mean())
    ).reset_index()

    merged = pd.merge(imp_sub, agg_shift, on="feature", how="inner")
    if merged.empty:
        log("  [WARN] Intersection on feature column keys returned empty. Check signature string formats.", level="WARN")
        write_csv(OUT["importance_shift"], pd.DataFrame())
        return pd.DataFrame()

    for c in ["mean_ks_stat", "mean_wasserstein", "mean_mean_shift_normed", "max_ks_stat"]:
        merged[c] = merged[c].fillna(0)

    def _norm(s: pd.Series) -> pd.Series:
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng > 1e-9 else pd.Series(np.zeros(len(s)), index=s.index)

    merged["imp_norm"]   = _norm(merged["importance"])
    merged["ks_norm"]    = _norm(merged["mean_ks_stat"])
    merged["wasserstein_norm"]  = _norm(merged["mean_wasserstein"])
    merged["shift_norm"] = _norm(merged["mean_mean_shift_normed"])

    merged["importance_shift_score"] = (
        0.4 * merged["imp_norm"] +
        0.3 * merged["ks_norm"] +
        0.2 * merged["wasserstein_norm"] +
        0.1 * merged["shift_norm"]
    )

    merged = merged.sort_values("importance_shift_score", ascending=False).head(100)
    merged["rank"] = range(1, len(merged) + 1)

    write_csv(OUT["importance_shift"], merged)
    log(f"  → PHASE6_IMPORTANCE_SHIFT_ANALYSIS.csv written (top {len(merged)} features, importance_col='{imp_col}')")
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# STEP 14 FALSE NEGATIVE SIGNATURE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
def step14_fn_signature(
    patient_dfs : dict,
    prob_store  : dict,
    col_map     : dict,
    feat_names  : list[str],
    fn_df       : pd.DataFrame,
) -> pd.DataFrame:
    section("STEP 14 — FALSE NEGATIVE SIGNATURE ANALYSIS")
    label_col = col_map["label"]
    required_fn_cols = {"patient", "gt_start_window", "gt_end_window"}

    if fn_df.empty or not required_fn_cols.issubset(fn_df.columns):
        log("  [WARN] FN dataframe insufficient for signature analysis", level="WARN")
        pd.DataFrame().to_csv(OUT["fn_signature"], index=False)
        return pd.DataFrame()

    fail_dfs = [patient_dfs[p] for p in ALL_FAIL_PATIENTS if p in patient_dfs]
    if not fail_dfs:
        log("  No failure patient data matrices to isolate signature attributes.")
        pd.DataFrame().to_csv(OUT["fn_signature"], index=False)
        return pd.DataFrame()

    master_fail = pd.concat(fail_dfs, ignore_index=True)
    master_fail["global_idx"] = range(len(master_fail))

    fn_indices = set()
    for _, row in fn_df.iterrows():
        p = row["patient"]
        if p not in patient_dfs:
            continue
        st = int(row["gt_start_window"])
        en = int(row["gt_end_window"])

        running_offset = 0
        for fp in ALL_FAIL_PATIENTS:
            if fp == p:
                for idx in range(st, en + 1):
                    target_idx = running_offset + idx
                    if target_idx < len(master_fail):
                        fn_indices.add(target_idx)
                break
            else:
                if fp in patient_dfs:
                    running_offset += len(patient_dfs[fp])

    tp_indices = set(master_fail[master_fail[label_col] == 1].index) - fn_indices
    log(f"  Isolated footprint windows -> FN Count: {len(fn_indices)} | TP Count: {len(tp_indices)}")

    if len(fn_indices) < 2 or len(tp_indices) < 2:
        log("  Insufficient variance between conditional indexing to complete signatures.")
        pd.DataFrame().to_csv(OUT["fn_signature"], index=False)
        return pd.DataFrame()

    rows = []
    for feat in feat_names:
        if feat not in master_fail.columns:
            continue
        vals = master_fail[feat].dropna().values
        if len(vals) == 0:
            continue

        fn_vals = master_fail.loc[list(fn_indices), feat].dropna().values
        tp_vals = master_fail.loc[list(tp_indices), feat].dropna().values

        if len(fn_vals) < 5 or len(tp_vals) < 5:
            continue

        ks_s, ks_p = ks_2samp(fn_vals, tp_vals)
        rows.append({
            "feature": feat,
            "mean_fn_windows": round(float(np.mean(fn_vals)), 6),
            "mean_tp_windows": round(float(np.mean(tp_vals)), 6),
            "ks_statistic": round(float(ks_s), 6),
            "ks_pvalue": round(float(ks_p), 6),
            "wasserstein": round(float(wasserstein_distance(fn_vals, tp_vals)), 6),
            "fn_max": round(float(np.max(fn_vals)), 6),
            "tp_max": round(float(np.max(tp_vals)), 6),
        })

    sig_df = pd.DataFrame(rows).sort_values("ks_statistic", ascending=False)
    write_csv(OUT["fn_signature"], sig_df)
    log(f"  → PHASE6_FN_SIGNATURE_ANALYSIS.csv written ({len(sig_df)} features)")
    return sig_df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 15 MODEL CONFIDENCE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
def step15_confidence_analysis(patient_dfs: dict, prob_store: dict, col_map: dict) -> pd.DataFrame:
    section("STEP 15 — MODEL CONFIDENCE ANALYSIS")
    label_col = col_map["label"]
    rows = []

    for pat in sorted(patient_dfs.keys()):
        df  = patient_dfs[pat]
        prb = prob_store[pat]
        lbl = df[label_col].astype(int).values

        pos_prbs = prb[lbl == 1]
        neg_prbs = prb[lbl == 0]

        def _stat(arr, fn):
            return round(float(fn(arr)), 6) if len(arr) > 0 else float("nan")

        brier = float(np.mean((prb - lbl) ** 2)) if len(prb) > 0 else float("nan")

        n_bins = 10
        ece = 0.0
        for i in range(n_bins):
            lo, hi = i / n_bins, (i + 1) / n_bins
            mask = (prb >= lo) & (prb < hi)
            if mask.sum() == 0:
                continue
            ece += abs(lbl[mask].mean() - prb[mask].mean()) * mask.sum() / len(prb)

        rows.append({
            "patient": pat,
            "category": (
                "PRIMARY_FAIL" if pat in PRIMARY_FAIL_PATIENTS
                else "SECONDARY_FAIL" if pat in SECONDARY_FAIL_PATIENTS
                else "GOOD" if pat in GOOD_PATIENTS
                else "CALIB"
            ),
            "n_total": len(prb),
            "n_positive": len(pos_prbs),
            "n_negative": len(neg_prbs),
            "brier_score": round(brier, 6),
            "expected_calibration_error": round(ece, 6),
            "prob_mean_positive": _stat(pos_prbs, np.mean),
            "prob_median_positive": _stat(pos_prbs, np.median),
            "prob_max_positive": _stat(pos_prbs, np.max),
            "prob_mean_negative": _stat(neg_prbs, np.mean),
            "positive_above_0.50": round(float((pos_prbs >= 0.50).sum() / len(pos_prbs)), 6) if len(pos_prbs) > 0 else 0.0,
            "positive_above_0.95": round(float((pos_prbs >= 0.95).sum() / len(pos_prbs)), 6) if len(pos_prbs) > 0 else 0.0,
        })

    conf_df = pd.DataFrame(rows)
    write_csv(OUT["confidence_analysis"], conf_df)
    log(f"  → PHASE6_CONFIDENCE_ANALYSIS.csv written ({len(conf_df)} rows)")
    return conf_df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 16 ROOT CAUSE CLASSIFICATION
# ─────────────────────────────────────────────────────────────────────────────
def step16_root_cause(conf_df: pd.DataFrame, shift_df: pd.DataFrame, fn_df: pd.DataFrame, gvb_df: pd.DataFrame) -> pd.DataFrame:
    section("STEP 16 — AUTOMATED ROOT CAUSE DIAGNOSTIC TREE")
    rows = []

    conf_idx = conf_df.set_index("patient") if "patient" in conf_df.columns else pd.DataFrame()

    for pat in ALL_FAIL_PATIENTS:
        if conf_df.empty or pat not in conf_df["patient"].values:
            rows.append({"patient": pat, "root_cause": "UNKNOWN", "evidence": "No conf data"})
            continue

        row    = conf_idx.loc[pat]
        pat_fn = fn_df[fn_df["patient"] == pat] if "patient" in fn_df.columns else pd.DataFrame()

        max_pos_prob    = float(row.get("prob_max_positive", float("nan")))
        median_pos_prob = float(row.get("prob_median_positive", float("nan")))
        prob_above_95   = float(row.get("positive_above_0.95", float("nan")))
        prob_above_50   = float(row.get("positive_above_0.50", float("nan")))
        brier           = float(row.get("brier_score", float("nan")))
        ece             = float(row.get("expected_calibration_error", float("nan")))
        n_pos           = int(row.get("n_positive", 0))

        pat_shift = shift_df[shift_df["patient"] == pat] if not shift_df.empty and "patient" in shift_df.columns else pd.DataFrame()
        high_shift_count = int((pat_shift["ks_statistic"] > 0.3).sum()) if not pat_shift.empty and "ks_statistic" in pat_shift.columns else 0
        mean_shift = float(pat_shift["ks_statistic"].mean()) if not pat_shift.empty and "ks_statistic" in pat_shift.columns else float("nan")

        evidence_parts = []
        causes = []

        if not math.isnan(max_pos_prob) and max_pos_prob < 0.2:
            causes.append("PATIENT_DOMAIN_SHIFT")
            evidence_parts.append(f"max_prob_positive={max_pos_prob:.4f} < 0.20: model generates no signal")
        if not math.isnan(max_pos_prob) and 0.2 <= max_pos_prob < PROD_MIN_PEAK_PROBABILITY:
            causes.append("ATTENUATED_PROBABILITY_SIGNAL")
            evidence_parts.append(f"max_prob_positive={max_pos_prob:.4f} peaks below mpp={PROD_MIN_PEAK_PROBABILITY}")

        if high_shift_count > 50:
            causes.append("HIGH_FEATURE_COV_SHIFT")
            evidence_parts.append(f"{high_shift_count} features have KS > 0.30 vs train")

        # FIX-13: Harden duration filter drop check against missing column keys
        if (
            not pat_fn.empty
            and "duration_windows" in pat_fn.columns
        ):
            short_seizures = pat_fn[pat_fn["duration_windows"] < 10]

            if len(short_seizures) == len(pat_fn) and len(pat_fn) > 0:
                causes.append("TEMPORAL_DURATION_FILTER_DROP")
                evidence_parts.append(
                    "all ground truth episodes are shorter than 10 windows; dropped by post-processing"
                )

        if len(causes) == 0:
            root_cause = "MARGINAL_CALIBRATION_MISALIGNMENT"
            evidence   = f"Brier={brier:.4f}, ECE={ece:.4f}. General signal present but peaks missed."
            contrib    = "NONE"
        elif len(causes) == 1:
            root_cause = causes[0]
            evidence   = "; ".join(evidence_parts)
            contrib    = "NONE"
        else:
            root_cause = "MULTI_FACTOR_CORRUPTION"
            evidence   = "; ".join(evidence_parts)
            contrib    = ", ".join(causes)

        log(f"  {pat.upper()} Diagnosed: {root_cause}")
        rows.append({
            "patient": pat,
            "root_cause": root_cause,
            "contributing_causes": contrib,
            "max_prob_positive": max_pos_prob,
            "mean_feature_ks": mean_shift,
            "evidence": evidence
        })

    rc_df = pd.DataFrame(rows)
    write_csv(OUT["root_cause_summary"], rc_df)
    log("  → PHASE6_ROOT_CAUSE_SUMMARY.csv written")
    return rc_df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 17 REMEDIATION GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def step17_remediation(
    rc_df       : pd.DataFrame,
    conf_df     : pd.DataFrame,
    shift_df    : pd.DataFrame,
    imp_shift_df: pd.DataFrame,
    fn_df       : pd.DataFrame,
    perf_df     : pd.DataFrame,
) -> dict:
    section("STEP 17 — REMEDIATION PLAN GENERATION")
    top_feats = []
    if not imp_shift_df.empty and "feature" in imp_shift_df.columns:
        top_feats = imp_shift_df["feature"].head(20).tolist()

    pat_summaries = {}
    for _, row in rc_df.iterrows():
        pat_summaries[row["patient"]] = {
            "root_cause": row["root_cause"],
            "contributing_causes": row.get("contributing_causes", ""),
            "max_prob_positive": row.get("max_prob_positive"),
            "evidence": row.get("evidence", ""),
        }

    remediations = []
    for pat, info in pat_summaries.items():
        cause    = info["root_cause"]
        contrib  = info["contributing_causes"] or ""
        max_prob = info["max_prob_positive"] or 0.0
        evidence = info["evidence"]

        pat_recs = {"patient": pat, "root_cause": cause, "actions": []}

        if "PATIENT_DOMAIN_SHIFT" in cause or "PATIENT_DOMAIN_SHIFT" in contrib:
            pat_recs["actions"].append({
                "priority": "HIGH",
                "action": "PATIENT_ADAPTIVE_THRESHOLD",
                "description": (
                    f"Patient {pat} generates max seizure probability={max_prob:.4f}, "
                    f"far below the global mpp={PROD_MIN_PEAK_PROBABILITY}. "
                    f"Implement an active baseline-calibrated threshold curve for {pat}."
                ),
                "evidence": evidence,
                "next_phase": "PHASE7_ADAPTIVE_THRESHOLD",
            })

        if "ATTENUATED_PROBABILITY_SIGNAL" in cause or "ATTENUATED_PROBABILITY_SIGNAL" in contrib:
            pat_recs["actions"].append({
                "priority": "HIGH",
                "action": "LOWER_MIN_PEAK_PROBABILITY_FOR_TARGET_ARCHETYPE",
                "description": (
                    f"Seizure footprint exists but is heavily attenuated below global thresholds. "
                    f"Relax peak criteria to 0.40 exclusively for the {pat} archetype cluster."
                ),
                "evidence": evidence,
                "next_phase": "PHASE7_THRESHOLD_RELAXATION",
            })

        if "TEMPORAL_DURATION_FILTER_DROP" in cause:
            pat_recs["actions"].append({
                "priority": "MEDIUM",
                "action": "SHORT_WINDOW_AUGMENTATION_TRAINING",
                "description": (
                    f"Patient has short-duration FN seizures (< 10 windows). "
                    "Augment training with synthetically shortened seizure windows or "
                    f"reduce min_duration from {PROD_MIN_DURATION} to 0 windows for this patient archetype."
                ),
                "evidence": evidence,
                "next_phase": "PHASE7_DATA_AUGMENTATION",
            })

        if "MULTI_FACTOR" in cause:
            pat_recs["actions"].append({
                "priority": "HIGH",
                "action": "PATIENT_SPECIFIC_MODEL",
                "description": (
                    f"{pat} has multiple contributing failure modes ({contrib}). "
                    f"A patient-specific XGBoost model fine-tuned on {pat}'s non-seizure baseline "
                    "with a relaxed peak threshold is the most direct remediation path."
                ),
                "evidence": evidence,
                "next_phase": "PHASE7_PATIENT_SPECIFIC_MODEL",
            })

        remediations.append(pat_recs)

    global_recs = []
    if not shift_df.empty and "ks_statistic" in shift_df.columns:
        very_high_shift = shift_df[shift_df["ks_statistic"] > 0.5]
        if len(very_high_shift) > 20:
            global_recs.append({
                "scope": "GLOBAL",
                "priority": "HIGH",
                "action": "PATIENT_RELATIVE_FEATURE_ENGINEERING",
                "description": (
                    f"{len(very_high_shift)} feature-patient combinations show KS>0.50 vs train. "
                    "Add a second feature layer consisting of z-scored deviations from each patient's "
                    "own rolling baseline (computed per inference EDF). "
                    "This converts absolute feature values to patient-relative signals."
                ),
                "top_affected_features": top_feats[:10],
                "next_phase": "PHASE7_RELATIVE_FEATURES",
            })

    plan = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prod_config_source": OUT["prod_config_audit"].name,
        "phase5e_production_mpp": PROD_MIN_PEAK_PROBABILITY,
        "phase5e_smoothing": PROD_SMOOTHING_WINDOW,
        "phase5e_threshold": PROD_THRESHOLD,
        "patient_specific_remediations": remediations,
        "global_remediations": global_recs,
    }

    write_json(OUT["remediation_plan"], plan)
    log("  → PHASE6_REMEDIATION_PLAN.json written")
    return plan


# ─────────────────────────────────────────────────────────────────────────────
# SELF AUDIT & REPORT GENERATION
# ─────────────────────────────────────────────────────────────────────────────
def self_audit() -> dict:
    section("PHASE 6 SELF-AUDIT SUITE")
    all_ok = True
    results = {}

    for name, path in OUT.items():
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        status = "PASS" if exists and size > 0 else "FAIL"

        parse_ok = True
        row_ok   = True
        error_msg = None

        if exists and size > 0:
            try:
                if path.suffix == ".json":
                    with open(path, encoding="utf-8") as f:
                        json.load(f)
                elif path.suffix == ".csv":
                    df = pd.read_csv(path)
                    if df.empty:
                        row_ok = False
            except Exception as e:
                parse_ok = False
                error_msg = str(e)

        if status == "FAIL" or not parse_ok or not row_ok:
            status = "FAIL"
            all_ok = False

        results[path.name] = {
            "status": status,
            "exists": exists,
            "size": size,
            "parse_ok": parse_ok,
            "row_ok": row_ok,
            "error": error_msg,
        }
        log(f"  [{status}] {path.name} ({size:,} bytes)")

    audit = {"all_ok": all_ok, "artifacts": results}
    write_json(OUT["self_audit"], audit)
    return audit


def write_execution_report(self_audit_result: dict) -> None:
    fixes_applied = [
        "FIX-1: IsotonicRegression uses 1-D arrays (no reshape(-1,1))",
        "FIX-2: Patient split reads 'calibration_patients' with fallback to 'val_patients'",
        "FIX-3: Feature importance column names discovered dynamically",
        "FIX-4: Train patients stats-only (reservoir) — full RAM load eliminated",
        "FIX-5: FN reconstruction mirrors Phase5C smooth→thr→duration→peak pipeline",
        "FIX-6: Train reference for KS tests uses reservoir, not raw concat",
        "FIX-7: Feature shift runtime O(n_features × n_patients) — expected, documented",
        "FIX-8: Production config loaded from Phase5E/Phase5C JSON; hardcodes are fallback",
        "FIX-9: Exact feature name ORDER validated against model.feature_names_in_",
        "FIX-10: True Algorithm-R reservoir implementation tracking (Unbiased distribution)",
        "FIX-11: List-append optimization to completely avoid inner batch loops pd.concat reallocations",
        "FIX-12: Converted metadata mismatch checks to crash pipeline with FAIL exception instead of WARN",
        "FIX-13: Column check 'duration_windows' in root cause drop logic",
    ]

    lines = [
        "=" * 70,
        "PHASE6 PATIENT GENERALIZATION FORENSICS — EXECUTION REPORT",
        "=" * 70,
        f"Generated : {datetime.now(timezone.utc).isoformat()}",
        f"Python    : {sys.version}",
        f"Platform  : {platform.platform()}",
        "",
        "=" * 70,
        "FIXES APPLIED IN THIS VERSION",
        "=" * 70,
    ]
    for fix in fixes_applied:
        lines.append(f"  {fix}")

    lines += [
        "",
        "=" * 70,
        "PRODUCTION CONFIG (as discovered)",
        "=" * 70,
        f"  smoothing_window     : {PROD_SMOOTHING_WINDOW}",
        f"  threshold            : {PROD_THRESHOLD}",
        f"  min_duration         : {PROD_MIN_DURATION}",
        f"  min_peak_probability : {PROD_MIN_PEAK_PROBABILITY}",
        "",
        "=" * 70,
        "INVESTIGATION TARGETS",
        "=" * 70,
        f"  Primary Fail         : {PRIMARY_FAIL_PATIENTS}",
        f"  Secondary Fail       : {SECONDARY_FAIL_PATIENTS}",
        f"  Good References      : {GOOD_PATIENTS}",
        "",
        "=" * 70,
        "SELF AUDIT MATRIX SUMMARY",
        "=" * 70,
        f"  OVERALL STATUS       : {'PASS' if self_audit_result['all_ok'] else 'FAIL'}",
        "",
    ]

    for k, v in self_audit_result["artifacts"].items():
        lines.append(f"  * {k:<45} -> {v['status']} ({v['size']:,} bytes)")

    lines.append("\n" + "=" * 70)
    lines.append("END OF PHASE6 FORENSIC REPORT")
    lines.append("=" * 70)

    with open(OUT["execution_report"], "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXECUTION INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
def main():
    section("PHASE 6 PATIENT FORENSICS DRIVER")
    log(f"Script : {__file__}")
    log(f"CWD    : {os.getcwd()}")
    log(f"Python : {sys.version}")

    try:
        # ── 0a · Input validation ─────────────────────────────────────────
        step0a_input_validation()

        # ── 0b · FIX-8: Load production config from Phase5E/Phase5C ──────
        step0b_load_prod_config()

        # ── Load feature signature ────────────────────────────────────────
        with open(FEAT_SIG_PATH, encoding="utf-8") as fh:
            _sig = json.load(fh)
        feat_names: list[str] = _sig["feature_names"]
        log(f"Feature signature loaded: {len(feat_names)} features")

        # ── FIX-2: Patient split with val_patients fallback ───────────────
        with open(SPLIT_PATH, encoding="utf-8") as fh:
            _spl = json.load(fh)
        train_pats = [p.lower() for p in _spl["train_patients"]]
        calib_pats = [p.lower() for p in (
            _spl.get("calibration_patients") or _spl.get("val_patients") or []
        )]
        test_pats  = [p.lower() for p in _spl["test_patients"]]
        log(f"Split loaded: train={len(train_pats)} | calib={len(calib_pats)} | test={len(test_pats)}")

        # ── 1 · Discovery ────────────────────────────────────────────────
        col_map = step1_schema_discovery(feat_names)["column_mapping"]

        # ── 2 · Feature Signature Audit ──────────────────────────────────
        # Temporarily pass an empty signature tracker to gather validation properties
        _, _ = step2_feature_audit(joblib.load(MODEL_PATH))

        # ── 3 · Split validation ─────────────────────────────────────────
        step3_patient_split_audit()

        # ── 4 · Load safe subsets (FIX-4, FIX-10, FIX-11) ────────────────
        patient_dfs, _, train_feat_stats = step4_load_data(
            col_map, feat_names, train_pats, calib_pats, test_pats
        )

        # ── 5 · Model extraction & validation (FIX-9, FIX-12) ────────────
        model, _ = step5_model_audit(feat_names)

        # ── 6 · Calibration reconstruction ────────────────────────────────
        calibrator = step6_calibration_audit(patient_dfs, col_map, feat_names, model)

        # ── 7 · Inference loops ──────────────────────────────────────────
        prob_store = step7_generate_probabilities(patient_dfs, feat_names, model, calibrator)

        # ── 8 · Reconstruct events (FIX-5) ───────────────────────────────
        fn_df, _ = step8_fn_audit(patient_dfs, prob_store, col_map)

        # ── 9 · Profiling ────────────────────────────────────────────────
        perf_df = step9_patient_performance(patient_dfs, prob_store, col_map)

        # ── 10 · Feature metrics pass (FIX-6) ─────────────────────────────
        shift_df = step10_feature_shift(patient_dfs, feat_names, train_feat_stats)

        # ── 11 · Deeper inspection profiling (FIX-6) ──────────────────────
        step11_deep_forensics(patient_dfs, prob_store, col_map, feat_names, fn_df, train_feat_stats)

        # ── 12 · Good vs Bad matching metrics ────────────────────────────
        gvb_df = step12_good_vs_bad(patient_dfs, prob_store, col_map, feat_names)

        # ── 13 · Importance × shift cross-validation (FIX-3) ──────────────
        imp_shift_df = step13_importance_shift(shift_df)

        # ── 14 · Signature trace matching ────────────────────────────────
        fn_sig_df = step14_fn_signature(patient_dfs, prob_store, col_map, feat_names, fn_df)

        # ── 15 · Confidence score mappings ────────────────────────────────
        conf_df = step15_confidence_analysis(patient_dfs, prob_store, col_map)

        # ── 16 · Tree parsing and diagnostic trace ────────────────────────
        print("ENTER STEP16", flush=True)
        rc_df = step16_root_cause(conf_df, shift_df, fn_df, gvb_df)
        print("EXIT STEP16", flush=True)

        # ── 17 · Generate Remediation output targets ──────────────────────
        print("ENTER STEP17", flush=True)
        step17_remediation(rc_df, conf_df, shift_df, imp_shift_df, fn_df, perf_df)
        print("EXIT STEP17", flush=True)

    except Exception as exc:
        with open("PHASE6_FATAL_ERROR.txt", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())

        raise
    finally:
        sa = self_audit()
        write_execution_report(sa)
        
        # Runtime profiling diagnostics
        runtime_audit = {
            "execution_status": "COMPLETED" if sa["all_ok"] else "FAILED",
            "total_runtime_seconds": _elapsed(),
            "peak_memory_mb": _peak_mb(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        write_json(OUT["runtime_audit"], runtime_audit)
        
        section("PHASE6 PRODUCTION COMPLETE")
        log(f"Runtime : {_elapsed()} sec | Memory : {_peak_mb()} MB")


if __name__ == "__main__":
    main()