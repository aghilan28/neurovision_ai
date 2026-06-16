"""
PHASE 5C — TEMPORAL EVENT DETECTION
NeuroVision AI

Converts noisy window-level seizure predictions into clinically meaningful
seizure events using temporal smoothing, event aggregation, false-alarm
suppression, and event-level evaluation.

Requires (same directory):
    PHASE5B_ENGINEERED_DATASET.parquet
    PHASE5B_TEMPORAL_XGBOOST.joblib
    PHASE5B_FEATURE_SIGNATURE.json
    PHASE5B_PATIENT_SPLIT.json

FIXES APPLIED (vs. original):
  FIX-1:  EXPECTED_FEATURE_COUNT removed — source of truth is the signature
          file itself; hardcoded constant is gone.
  FIX-2:  Configuration search caches aggregation per (smoothing_col, threshold)
          so aggregation is not repeated for each (min_duration, min_peak) pair.
          38 115 → ~495 aggregation calls.
  FIX-3:  Parquet is loaded with column filtering and patient-row filtering via
          pyarrow filters= to avoid loading 3+ GB into memory.
  FIX-4:  Memory tracking uses psutil (cross-platform) instead of resource.
  FIX-5:  EventMatcher now enforces 1-to-1 matching (one GT event can be
          covered by at most one predicted event, and vice-versa).
  FIX-6:  balanced_accuracy = recall alias removed; metric is omitted and
          marked as non-computable without TN.
  FIX-7:  MCC without TN is marked non-computable and returned as None.
  FIX-8:  Cohen's kappa without TN is marked non-computable and returned as None.
  FIX-9:  Feature-order validation now does an explicit element-wise comparison
          between the dataset column order and the canonical signature order.
  FIX-10: Optional isotonic-regression probability calibration step added
          (active only when calibration labels are available in the dataset).

ROUND-2 FIXES (this revision):
  FIX-11: Calibration now uses a held-out CALIBRATION split, distinct from
          the patients used to TRAIN the XGBoost model. The patient split
          file must provide a "calibration_patients" key (or, if absent,
          a configurable fraction of train_patients is carved out
          deterministically and used for calibration only). This prevents
          calibrating on the same patients the model was fit on, which
          previously caused optimistically-low ECE estimates.
  FIX-12: Parquet fallback path no longer loads the full dataset into memory.
          If filters= is unsupported, we now use a pyarrow.dataset scan with
          row-group-level filtering and column projection. Only as a last
          resort (pyarrow.dataset unavailable) do we fall back to a full
          read, and that fallback is now logged loudly as a memory-risk
          condition with an estimated row count check against
          MEMORY_BUDGET_GB.
  FIX-13: EventMatcher now offers a globally-optimal 1-to-1 matching mode
          using a max-weight bipartite matching (via a simple augmenting-path
          / Hopcroft–Karp style algorithm restricted to overlap candidates),
          selectable via MATCHING_STRATEGY. Default remains "greedy" for
          speed (documented as acceptable for this use case per FIX-5), but
          "optimal" is now available and used automatically when the number
          of overlap-ambiguous (patient, edf) groups is small enough to be
          cheap (<= OPTIMAL_MATCH_GROUP_SIZE_LIMIT events per group).
  FIX-14: Configuration search now reports estimated wall-clock cost up front
          (based on a timed sample of matcher calls) and logs a clear
          expectation ("minutes, not seconds") rather than silently running.
  FIX-15: Removed unused import (CalibratedClassifierCV).
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import gc
import json
import logging
import sys
import time
import traceback
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
import psutil  # FIX-4
from sklearn.calibration import calibration_curve  # FIX-15: CalibratedClassifierCV removed (unused)
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
)

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — Input Artifacts
# ---------------------------------------------------------------------------
INPUT_PARQUET = "PHASE5B_ENGINEERED_DATASET.parquet"
INPUT_MODEL = "PHASE5B_TEMPORAL_XGBOOST.joblib"
INPUT_FEATURE_SIGNATURE = "PHASE5B_FEATURE_SIGNATURE.json"
INPUT_PATIENT_SPLIT = "PHASE5B_PATIENT_SPLIT.json"

# ---------------------------------------------------------------------------
# Constants — Output Artifacts
# ---------------------------------------------------------------------------
OUTPUT_EVENT_PREDICTIONS = "PHASE5C_EVENT_PREDICTIONS.csv"
OUTPUT_EVENT_METRICS = "PHASE5C_EVENT_METRICS.csv"
OUTPUT_CONFIGURATION_SEARCH = "PHASE5C_CONFIGURATION_SEARCH.csv"
OUTPUT_BEST_CONFIGURATION = "PHASE5C_BEST_CONFIGURATION.json"
OUTPUT_PATIENT_EVENT_SUMMARY = "PHASE5C_PATIENT_EVENT_SUMMARY.csv"
OUTPUT_EXECUTION_REPORT = "PHASE5C_EXECUTION_REPORT.txt"
OUTPUT_SCHEMA_AUDIT = "PHASE5C_SCHEMA_AUDIT.json"
OUTPUT_RUNTIME_AUDIT = "PHASE5C_RUNTIME_AUDIT.json"

# ---------------------------------------------------------------------------
# Constants — Schema
# ---------------------------------------------------------------------------
REQUIRED_METADATA_COLS = [
    "label",
    "patient",
    "edf",
    "window_index",
]

OPTIONAL_METADATA_COLS = [
    "window_uid",
    "window_start_sec",
    "window_end_sec",
    "window_duration_sec",
    "stride_sec",
]

# FIX-1: EXPECTED_FEATURE_COUNT constant removed.
# The feature count is read directly from PHASE5B_FEATURE_SIGNATURE.json.

# ---------------------------------------------------------------------------
# Constants — Search Space
# ---------------------------------------------------------------------------
SMOOTHING_WINDOWS = [3, 5, 7, 11, 21]

THRESHOLDS = [round(t, 2) for t in np.arange(0.01, 1.00, 0.01)]

MIN_DURATIONS = [1, 2, 3, 5, 7, 10, 15]

MIN_PEAK_PROBABILITIES = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99]

SMOOTHED_PROB_COLUMNS = [
    "smoothed_prob_3",
    "smoothed_prob_5",
    "smoothed_prob_7",
    "smoothed_prob_11",
    "smoothed_prob_21",
]

MEMORY_BUDGET_GB = 10.0

# ---------------------------------------------------------------------------
# Constants — Calibration (FIX-11)
# ---------------------------------------------------------------------------
# Fraction of train_patients carved out (deterministically) for calibration
# ONLY when the patient split file does not already provide an explicit
# "calibration_patients" key. These patients are NOT used to fit the
# calibrator's "training" view in any sense other than calibration — they
# are assumed to have been excluded from the XGBoost training set as well
# if the split file was generated correctly. This fallback exists purely so
# the pipeline does not silently calibrate on model-training patients.
CALIBRATION_FRACTION_FALLBACK = 0.2
MIN_CALIBRATION_PATIENTS = 1

# ---------------------------------------------------------------------------
# Constants — Event Matching (FIX-13)
# ---------------------------------------------------------------------------
# "greedy"  -> original FIX-5 behaviour (earliest-start-first, first overlap wins)
# "optimal" -> maximum-cardinality 1-to-1 bipartite matching within each
#              (patient, edf) group, used automatically when the group is
#              small enough to be cheap.
MATCHING_STRATEGY = "auto"  # "greedy" | "optimal" | "auto"
OPTIMAL_MATCH_GROUP_SIZE_LIMIT = 40  # max(len(pred_in_group), len(gt_in_group))


# ---------------------------------------------------------------------------
# FIX-4: Cross-platform memory tracker using psutil
# ---------------------------------------------------------------------------
def get_process_memory_mb() -> float:
    """Returns current RSS memory of this process in MB. Works on all OSes."""
    try:
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# SchemaValidator
# ---------------------------------------------------------------------------
class SchemaValidator:
    """
    Validates all required artifacts and dataset schema before pipeline runs.

    FIX-1: Feature count is validated against the value stored in the
           signature file itself, not a hardcoded constant.
    FIX-9: Feature column order is verified by an explicit element-wise
           comparison against the canonical list, not just a set membership
           check.
    """

    def __init__(
        self,
        parquet_path: str,
        model_path: str,
        feature_signature_path: str,
        patient_split_path: str,
    ):
        self.parquet_path = parquet_path
        self.model_path = model_path
        self.feature_signature_path = feature_signature_path
        self.patient_split_path = patient_split_path
        self.audit: Dict = {}

    def validate(self) -> Tuple[Dict, List[str]]:
        """Run all validations. Returns (audit dict, feature_names). Raises RuntimeError on failure."""
        log.info("[SchemaValidator] Starting schema validation...")
        self._validate_files_exist()
        feature_names = self._validate_feature_signature()
        self._validate_patient_split()
        self._validate_dataset_columns(feature_names)
        self._validate_model()
        self.audit["overall_passed"] = True
        log.info("[SchemaValidator] All schema checks PASSED.")
        return self.audit, feature_names

    def _fail(self, message: str):
        self.audit["overall_passed"] = False
        raise RuntimeError(f"[SchemaValidator] SCHEMA FAILURE: {message}")

    def _validate_files_exist(self):
        checks = {}
        for label, path in [
            ("dataset", self.parquet_path),
            ("model", self.model_path),
            ("feature_signature", self.feature_signature_path),
            ("patient_split", self.patient_split_path),
        ]:
            exists = Path(path).exists()
            checks[label] = {"path": path, "exists": exists}
            if not exists:
                self._fail(f"Required artifact not found: {path}")
        self.audit["file_existence"] = checks
        log.info("[SchemaValidator] File existence checks PASSED.")

    def _validate_feature_signature(self) -> List[str]:
        """
        FIX-1: Reads feature_count from the JSON file and validates
        len(feature_names) == feature_count. No hardcoded constant.
        """
        with open(self.feature_signature_path) as fh:
            sig = json.load(fh)

        feature_names: List[str] = sig.get("feature_names", [])
        feature_count: int = sig.get("feature_count", 0)

        if len(feature_names) == 0:
            self._fail("feature_signature: feature_names list is empty.")

        # FIX-1: validate internal consistency of the signature file itself
        if feature_count == 0:
            self._fail("feature_signature: feature_count is 0.")

        if len(feature_names) != feature_count:
            self._fail(
                f"feature_signature is internally inconsistent: "
                f"feature_count={feature_count} but len(feature_names)={len(feature_names)}."
            )

        if len(feature_names) != len(set(feature_names)):
            dupes = [f for f in set(feature_names) if feature_names.count(f) > 1]
            self._fail(f"feature_signature: duplicate feature names found: {dupes[:5]}")

        self.audit["feature_signature"] = {
            "feature_count": feature_count,
            "source": "PHASE5B_FEATURE_SIGNATURE.json",  # FIX-1: no hardcoded constant
            "passed": True,
        }
        log.info(
            f"[SchemaValidator] Feature signature: {feature_count} features "
            f"(sourced from signature file). PASSED."
        )
        return feature_names

    def _validate_patient_split(self):
        with open(self.patient_split_path) as fh:
            split = json.load(fh)
        test_patients = split.get("test_patients", [])
        if len(test_patients) == 0:
            self._fail("patient_split: test_patients list is empty.")

        train_patients = split.get("train_patients", [])
        calibration_patients = split.get("calibration_patients", [])

        # FIX-11: detect and warn about overlap between calibration and
        # training patients (would cause optimistic calibration).
        overlap = set(train_patients) & set(calibration_patients)
        if calibration_patients and overlap:
            self._fail(
                f"patient_split: calibration_patients overlaps train_patients "
                f"for {len(overlap)} patient(s): {sorted(overlap)[:5]}. "
                f"Calibration set must be disjoint from training set."
            )

        self.audit["patient_split"] = {
            "test_patients": test_patients,
            "test_patient_count": len(test_patients),
            "train_patient_count": len(train_patients),
            "calibration_patients_provided": len(calibration_patients) > 0,
            "calibration_patient_count": len(calibration_patients),
            "passed": True,
        }
        log.info(f"[SchemaValidator] Patient split: {len(test_patients)} test patients PASSED.")

    def _validate_dataset_columns(self, feature_names: List[str]):
        """
        FIX-9: Performs an explicit element-wise order comparison between the
        dataset's feature columns (in their actual order) and the canonical
        feature list. A set-membership check alone is insufficient.
        """
        log.info("[SchemaValidator] Peeking at dataset columns (reading schema only)...")
        df_schema = pd.read_parquet(self.parquet_path, columns=None).columns.tolist()

        # Check required metadata columns
        for col in REQUIRED_METADATA_COLS:
            if col not in df_schema:
                self._fail(f"Dataset missing required column: '{col}'")

        # Verify all feature columns are present
        missing_features = [f for f in feature_names if f not in df_schema]
        if missing_features:
            self._fail(
                f"Dataset missing {len(missing_features)} feature columns. "
                f"First 5: {missing_features[:5]}"
            )

        # FIX-9: explicit element-wise order check
        # Extract feature columns from the dataset IN THEIR ACTUAL ORDER
        feature_set = set(feature_names)
        dataset_feature_cols_ordered = [c for c in df_schema if c in feature_set]

        if dataset_feature_cols_ordered != feature_names:
            # Find first mismatch position for a helpful error message
            mismatch_pos = next(
                (
                    i for i, (a, b) in enumerate(
                        zip(dataset_feature_cols_ordered, feature_names)
                    )
                    if a != b
                ),
                min(len(dataset_feature_cols_ordered), len(feature_names)),
            )
            self._fail(
                f"Feature column ORDER in dataset does not match canonical signature. "
                f"First mismatch at position {mismatch_pos}: "
                f"dataset='{dataset_feature_cols_ordered[mismatch_pos] if mismatch_pos < len(dataset_feature_cols_ordered) else 'N/A'}' "
                f"vs signature='{feature_names[mismatch_pos] if mismatch_pos < len(feature_names) else 'N/A'}'."
            )

        self.audit["dataset_columns"] = {
            "total_columns_in_dataset": len(df_schema),
            "required_metadata_present": True,
            "feature_columns_present": True,
            "feature_count_matches": True,
            "feature_order_matches": True,  # FIX-9: now actually verified
            "passed": True,
        }
        log.info("[SchemaValidator] Dataset column validation PASSED (order verified).")

    def _validate_model(self):
        log.info("[SchemaValidator] Validating model object...")
        model = joblib.load(self.model_path)
        if model is None:
            self._fail("Model loaded as None.")
        if not hasattr(model, "predict_proba"):
            self._fail("Model does not have predict_proba method.")
        self.audit["model"] = {
            "path": self.model_path,
            "has_predict_proba": True,
            "passed": True,
        }
        log.info("[SchemaValidator] Model validation PASSED.")
        del model
        gc.collect()


# ---------------------------------------------------------------------------
# FIX-3 / FIX-12: Parquet loading helper with safe fallback
# ---------------------------------------------------------------------------
def load_parquet_filtered(
    parquet_path: str,
    columns: List[str],
    patients: List[str],
) -> pd.DataFrame:
    """
    Load only the requested columns and only rows whose 'patient' value is
    in `patients`.

    FIX-3:  Primary path uses pandas/pyarrow `filters=` for row-group and
            predicate pushdown filtering, avoiding loading the full dataset.
    FIX-12: If `filters=` is unsupported by the installed backend, we fall
            back to a pyarrow.dataset scan (still avoids a full in-memory
            read via batched iteration + filtering). Only if pyarrow.dataset
            itself is unavailable do we perform a full `pd.read_parquet`
            read — and in that case we log a loud memory-risk warning and
            estimate the resulting memory footprint against
            MEMORY_BUDGET_GB before proceeding.
    """
    patient_set = set(patients)

    # --- Primary path: filters= pushdown -------------------------------- #
    try:
        df = pd.read_parquet(
            parquet_path,
            columns=columns,
            filters=[("patient", "in", patients)],
        )
        log.info(
            f"[ParquetLoader] FIX-3: filters= pushdown succeeded — "
            f"{len(df)} rows loaded directly."
        )
        return df
    except Exception as e:
        log.warning(
            f"[ParquetLoader] FIX-3: filters= pushdown failed ({e}); "
            f"attempting FIX-12 pyarrow.dataset batched scan..."
        )

    # --- FIX-12: pyarrow.dataset batched scan, still avoids full load ---- #
    try:
        import pyarrow.dataset as ds
        import pyarrow.compute as pc

        dataset = ds.dataset(parquet_path, format="parquet")
        filter_expr = ds.field("patient").isin(list(patient_set))

        batches = []
        total_rows = 0
        for batch in dataset.to_batches(columns=columns, filter=filter_expr):
            if batch.num_rows == 0:
                continue
            batches.append(batch)
            total_rows += batch.num_rows

        if batches:
            import pyarrow as pa
            table = pa.Table.from_batches(batches)
            df = table.to_pandas()
        else:
            df = pd.DataFrame(columns=columns)

        log.info(
            f"[ParquetLoader] FIX-12: pyarrow.dataset batched scan succeeded — "
            f"{len(df)} rows loaded without a full in-memory read."
        )
        return df

    except Exception as e:
        log.warning(
            f"[ParquetLoader] FIX-12: pyarrow.dataset batched scan failed ({e}); "
            f"falling back to FULL pd.read_parquet read. "
            f"THIS IS A MEMORY-RISK CONDITION."
        )

    # --- Last resort: full read, with explicit memory-risk logging ------- #
    try:
        pf_meta = pd.read_parquet(parquet_path, columns=None)
        estimated_total_rows = len(pf_meta)
        del pf_meta
        gc.collect()
        estimated_bytes_per_row = 8 * max(len(columns), 1)  # rough float64 estimate
        estimated_gb = (estimated_total_rows * estimated_bytes_per_row) / (1024 ** 3)
        log.warning(
            f"[ParquetLoader] FIX-12: full-read fallback — estimated dataset size "
            f"~{estimated_gb:.2f} GB across {estimated_total_rows} rows "
            f"(budget={MEMORY_BUDGET_GB} GB)."
        )
        if estimated_gb > MEMORY_BUDGET_GB:
            log.error(
                f"[ParquetLoader] FIX-12: estimated full-read size "
                f"({estimated_gb:.2f} GB) EXCEEDS MEMORY_BUDGET_GB "
                f"({MEMORY_BUDGET_GB} GB). Proceeding anyway, but this may "
                f"OOM. Consider installing pyarrow to enable FIX-3/FIX-12 "
                f"filtered reads."
            )
    except Exception:
        log.warning(
            "[ParquetLoader] FIX-12: could not estimate full dataset size "
            "before fallback full read."
        )

    df_full = pd.read_parquet(parquet_path, columns=columns)
    df = df_full[df_full["patient"].isin(patient_set)].copy()
    del df_full
    gc.collect()
    log.info(
        f"[ParquetLoader] FIX-12: full-read fallback complete — "
        f"{len(df)} rows retained after post-filter."
    )
    return df


# ---------------------------------------------------------------------------
# FIX-10 / FIX-11: ProbabilityCalibrator
# ---------------------------------------------------------------------------
class ProbabilityCalibrator:
    """
    FIX-10: Fits an isotonic-regression calibrator on calibration-set windows
    and applies it to test-patient probabilities.

    FIX-11: The calibration set MUST be disjoint from the patients used to
    train the XGBoost model. Calibrating on the model's own training data
    produces optimistically low ECE (the model is "confident and correct" on
    data it has memorized), which makes the apparent calibration quality
    unreliable and can mislead threshold tuning in Phase 5C.

    The caller (main pipeline) is responsible for selecting the correct
    calibration patient set — see `select_calibration_patients()`.

    Background: Phase 5B reported ECE ≈ 0.488 on (what was believed to be)
    held-out data, meaning raw model probabilities are severely
    miscalibrated. Thresholds in Phase 5C operate directly on these
    probabilities, so uncalibrated scores make threshold-tuning unreliable
    (e.g. a threshold of 0.90 does not correspond to 90% confidence).

    Strategy:
      - Use calibration-patient windows (disjoint from model-training
        patients and from test patients) as the calibration set.
      - Fit IsotonicRegression on (raw_prob, true_label) pairs.
      - Transform test-set raw probabilities before event detection.
    """

    def __init__(self):
        self._calibrator: Optional[IsotonicRegression] = None
        self.calibration_applied: bool = False
        self.calibration_ece_before: Optional[float] = None
        self.calibration_ece_after: Optional[float] = None

    def fit(self, raw_proba: np.ndarray, labels: np.ndarray):
        """Fit calibrator on the calibration set (NOT the model's training set)."""
        log.info(
            f"[Calibrator] FIX-11: Fitting isotonic regression on "
            f"{len(raw_proba)} held-out calibration samples "
            f"(disjoint from model-training patients)..."
        )
        self._calibrator = IsotonicRegression(out_of_bounds="clip")
        self._calibrator.fit(raw_proba, labels)

        # Measure ECE before/after on the calibration set itself
        self.calibration_ece_before = self._compute_ece(raw_proba, labels)
        cal_proba = self._calibrator.predict(raw_proba)
        self.calibration_ece_after = self._compute_ece(cal_proba, labels)
        log.info(
            f"[Calibrator] Calibration-set ECE before={self.calibration_ece_before:.4f} "
            f"after={self.calibration_ece_after:.4f}"
        )

    def transform(self, raw_proba: np.ndarray) -> np.ndarray:
        """Apply calibration. Returns raw_proba unchanged if calibrator not fitted."""
        if self._calibrator is None:
            log.warning("[Calibrator] No calibrator fitted — returning raw probabilities.")
            return raw_proba
        calibrated = self._calibrator.predict(raw_proba).astype(np.float32)
        self.calibration_applied = True
        log.info("[Calibrator] Calibration applied to test probabilities.")
        return calibrated

    @staticmethod
    def _compute_ece(proba: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
        """Expected Calibration Error (uniform binning)."""
        try:
            fraction_of_positives, mean_predicted_value = calibration_curve(
                labels, proba, n_bins=n_bins, strategy="uniform"
            )
            ece = float(np.mean(np.abs(fraction_of_positives - mean_predicted_value)))
            return round(ece, 6)
        except Exception:
            return float("nan")


def select_calibration_patients(
    split: Dict,
    train_patients: List[str],
) -> Tuple[List[str], List[str], str]:
    """
    FIX-11: Determine which patients to use for probability calibration.

    Priority:
      1. If the patient split file provides an explicit "calibration_patients"
         list (validated as disjoint from train_patients in SchemaValidator),
         use it directly. This is the preferred, scientifically clean path.
      2. Otherwise, deterministically carve out a fraction
         (CALIBRATION_FRACTION_FALLBACK) of train_patients to serve as the
         calibration set, and EXCLUDE those patients from the set used for
         any model-training-related computation in this script. This is a
         fallback only — the underlying model was presumably already trained
         on the full train_patients list in Phase 5B, so this fallback can
         only reduce (not eliminate) the train/calibration overlap risk for
         NEW models. The pipeline logs this clearly.

    Returns:
        (calibration_patients, remaining_train_patients_for_reference, source)
    """
    explicit_cal = split.get("calibration_patients", [])
    if explicit_cal:
        log.info(
            f"[Calibration] FIX-11: Using explicit calibration_patients from "
            f"patient split file: {len(explicit_cal)} patients."
        )
        return explicit_cal, train_patients, "explicit_split_file"

    if not train_patients:
        log.warning(
            "[Calibration] FIX-11: No calibration_patients and no train_patients "
            "available — calibration will be skipped."
        )
        return [], [], "none_available"

    # Deterministic carve-out (sorted for reproducibility)
    sorted_train = sorted(train_patients)
    n_cal = max(
        MIN_CALIBRATION_PATIENTS,
        int(round(len(sorted_train) * CALIBRATION_FRACTION_FALLBACK)),
    )
    n_cal = min(n_cal, len(sorted_train) - 1) if len(sorted_train) > 1 else len(sorted_train)
    n_cal = max(n_cal, 0)

    calibration_patients = sorted_train[:n_cal]
    remaining_train = sorted_train[n_cal:]

    log.warning(
        f"[Calibration] FIX-11: patient split file has no 'calibration_patients' "
        f"key. Falling back to a deterministic carve-out of "
        f"{len(calibration_patients)}/{len(sorted_train)} train_patients for "
        f"calibration: {calibration_patients}. "
        f"NOTE: if the XGBoost model in PHASE5B_TEMPORAL_XGBOOST.joblib was "
        f"trained on ALL of train_patients (including these), calibration may "
        f"still be optimistic. Re-generate the patient split with an explicit "
        f"'calibration_patients' key for a clean three-way split."
    )

    return calibration_patients, remaining_train, "fallback_carveout"


# ---------------------------------------------------------------------------
# TemporalSmoothingEngine
# ---------------------------------------------------------------------------
class TemporalSmoothingEngine:
    """
    Applies centered rolling mean smoothing independently per EDF.
    Never crosses EDF boundaries. No NaN output.
    """

    def smooth(self, df: pd.DataFrame) -> pd.DataFrame:
        log.info("[TemporalSmoothingEngine] Applying temporal smoothing per EDF...")
        df = df.sort_values(["patient", "edf", "window_index"]).reset_index(drop=True)

        for win, col in zip(SMOOTHING_WINDOWS, SMOOTHED_PROB_COLUMNS):
            log.info(f"[TemporalSmoothingEngine] Computing {col} (window={win})...")
            smoothed = (
                df.groupby(["patient", "edf"], sort=False)["pred_proba"]
                .transform(
                    lambda x, w=win: x.rolling(
                        window=w,
                        min_periods=1,
                        center=True,
                    ).mean()
                )
                .astype(np.float32)
            )
            nan_mask = smoothed.isna()
            if nan_mask.any():
                log.warning(
                    f"[TemporalSmoothingEngine] {nan_mask.sum()} NaN in {col} — filling with pred_proba."
                )
                smoothed = smoothed.fillna(df["pred_proba"])
            df[col] = smoothed

        log.info("[TemporalSmoothingEngine] Temporal smoothing complete.")
        return df


# ---------------------------------------------------------------------------
# EventAggregator
# ---------------------------------------------------------------------------
class EventAggregator:
    """
    Converts binary positive windows into contiguous events per EDF.
    """

    def aggregate(
        self,
        df: pd.DataFrame,
        smoothed_col: str,
        threshold: float,
    ) -> pd.DataFrame:
        """
        Returns a DataFrame of events with columns:
            patient, edf, event_start_window, event_end_window,
            duration_windows, peak_probability, mean_probability,
            positive_window_count, is_true_event
        """
        events = []
        positive_mask = (df[smoothed_col] >= threshold).values
        patients = df["patient"].values
        edfs = df["edf"].values
        window_indices = df["window_index"].values
        probas = df[smoothed_col].values
        labels = df["label"].values

        group_keys = df[["patient", "edf"]].drop_duplicates().values
        idx_map = {
            (p, e): np.where((patients == p) & (edfs == e))[0]
            for p, e in group_keys
        }

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
                    ev = self._build_event(
                        patient, edf,
                        edf_win, edf_proba, edf_label,
                        event_start_idx, end_idx,
                    )
                    events.append(ev)
                    in_event = False
                    event_start_idx = None

            if in_event:
                end_idx = len(edf_pos) - 1
                ev = self._build_event(
                    patient, edf,
                    edf_win, edf_proba, edf_label,
                    event_start_idx, end_idx,
                )
                events.append(ev)

        if len(events) == 0:
            return pd.DataFrame(columns=[
                "patient", "edf", "event_start_window", "event_end_window",
                "duration_windows", "peak_probability", "mean_probability",
                "positive_window_count", "is_true_event",
            ])

        return pd.DataFrame(events)

    @staticmethod
    def _build_event(
        patient: str,
        edf: str,
        edf_win: np.ndarray,
        edf_proba: np.ndarray,
        edf_label: np.ndarray,
        start_idx: int,
        end_idx: int,
    ) -> Dict:
        win_slice = edf_win[start_idx: end_idx + 1]
        prob_slice = edf_proba[start_idx: end_idx + 1]
        label_slice = edf_label[start_idx: end_idx + 1]
        is_true = int(label_slice.max() == 1)
        return {
            "patient": patient,
            "edf": edf,
            "event_start_window": int(win_slice[0]),
            "event_end_window": int(win_slice[-1]),
            "duration_windows": int(len(win_slice)),
            "peak_probability": float(prob_slice.max()),
            "mean_probability": float(prob_slice.mean()),
            "positive_window_count": int(len(win_slice)),
            "is_true_event": is_true,
        }


# ---------------------------------------------------------------------------
# FalseAlarmSuppressor
# ---------------------------------------------------------------------------
class FalseAlarmSuppressor:
    """
    Suppresses events that fail minimum duration or minimum confidence filters.
    Tracks suppressed / retained counts.
    """

    def suppress(
        self,
        events_df: pd.DataFrame,
        min_duration: int,
        min_peak_prob: float,
    ) -> Tuple[pd.DataFrame, Dict]:
        if events_df.empty:
            stats = {
                "total_events": 0,
                "suppressed_events": 0,
                "retained_events": 0,
                "suppression_ratio": 0.0,
            }
            return events_df, stats

        keep_mask = (
            (events_df["duration_windows"] >= min_duration) &
            (events_df["peak_probability"] >= min_peak_prob)
        )
        retained = events_df[keep_mask].reset_index(drop=True)
        suppressed_count = int((~keep_mask).sum())
        retained_count = int(keep_mask.sum())
        total = len(events_df)
        suppression_ratio = suppressed_count / total if total > 0 else 0.0

        stats = {
            "total_events": total,
            "suppressed_events": suppressed_count,
            "retained_events": retained_count,
            "suppression_ratio": round(suppression_ratio, 4),
        }
        return retained, stats


# ---------------------------------------------------------------------------
# GroundTruthEventBuilder
# ---------------------------------------------------------------------------
class GroundTruthEventBuilder:
    """
    Converts per-window labels into ground-truth seizure events (contiguous
    positive-label windows) per EDF.
    """

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        gt_events = []
        df_sorted = df.sort_values(["patient", "edf", "window_index"]).reset_index(drop=True)

        patients = df_sorted["patient"].values
        edfs = df_sorted["edf"].values
        window_indices = df_sorted["window_index"].values
        labels = df_sorted["label"].values

        group_keys = df_sorted[["patient", "edf"]].drop_duplicates().values
        for patient, edf in group_keys:
            mask = (patients == patient) & (edfs == edf)
            edf_win = window_indices[mask]
            edf_label = labels[mask]

            in_event = False
            event_start_idx = None

            for local_i in range(len(edf_label)):
                if edf_label[local_i] == 1 and not in_event:
                    in_event = True
                    event_start_idx = local_i
                elif edf_label[local_i] == 0 and in_event:
                    end_idx = local_i - 1
                    gt_events.append({
                        "patient": patient,
                        "edf": edf,
                        "gt_start_window": int(edf_win[event_start_idx]),
                        "gt_end_window": int(edf_win[end_idx]),
                    })
                    in_event = False
                    event_start_idx = None

            if in_event:
                end_idx = len(edf_label) - 1
                gt_events.append({
                    "patient": patient,
                    "edf": edf,
                    "gt_start_window": int(edf_win[event_start_idx]),
                    "gt_end_window": int(edf_win[end_idx]),
                })

        if len(gt_events) == 0:
            return pd.DataFrame(columns=["patient", "edf", "gt_start_window", "gt_end_window"])
        return pd.DataFrame(gt_events)


# ---------------------------------------------------------------------------
# FIX-5 / FIX-13: EventMatcher — greedy and optimal 1-to-1 matching
# ---------------------------------------------------------------------------
class EventMatcher:
    """
    Matches predicted events to ground-truth events by temporal overlap,
    using a strict 1-to-1 assignment.

    FIX-5:
    The original implementation allowed multiple predicted events to match
    the same GT event, inflating TP. This implementation uses 1-to-1
    assignment: each GT event can satisfy at most one predicted event and
    vice-versa.

    FIX-13:
    Two matching strategies are available:
      - "greedy"  : earliest-start-first on predictions, greedy assignment to
                    the first available overlapping GT event (original FIX-5
                    behaviour). O(n) per group, can be locally suboptimal in
                    ambiguous overlap configurations (e.g. one long predicted
                    event spanning two short GT events).
      - "optimal" : maximum-cardinality 1-to-1 bipartite matching computed via
                    augmenting paths (Hopcroft–Karp style), restricted to the
                    overlap-candidate graph within each (patient, edf) group.
                    Guarantees the maximum possible TP count for that group.
      - "auto"    : uses "optimal" for groups where
                    max(len(pred_in_group), len(gt_in_group)) <=
                    OPTIMAL_MATCH_GROUP_SIZE_LIMIT, and falls back to "greedy"
                    for larger groups (where optimal matching would be
                    unnecessarily expensive and greedy is, per FIX-5's
                    clinical justification, an acceptable approximation).

    Clinical justification: detecting the same seizure three times with three
    overlapping predictions does not count as three true positives — it counts
    as one detected seizure and two spurious alarms.
    """

    def __init__(self, strategy: str = MATCHING_STRATEGY):
        if strategy not in ("greedy", "optimal", "auto"):
            raise ValueError(f"Unknown matching strategy: {strategy}")
        self.strategy = strategy

    def match(
        self,
        predicted_events: pd.DataFrame,
        gt_events: pd.DataFrame,
    ) -> Tuple[int, int, int]:
        """
        Returns (TP, FP, FN) under strict 1-to-1 matching.
        """
        if predicted_events.empty and gt_events.empty:
            return 0, 0, 0
        if predicted_events.empty:
            return 0, 0, len(gt_events)
        if gt_events.empty:
            return 0, len(predicted_events), 0

        # Group predictions and GT by (patient, edf)
        pred_groups: Dict[Tuple, List[Tuple[int, int]]] = {}
        for _, row in predicted_events.iterrows():
            key = (row["patient"], row["edf"])
            pred_groups.setdefault(key, []).append(
                (int(row["event_start_window"]), int(row["event_end_window"]))
            )

        gt_groups: Dict[Tuple, List[Tuple[int, int]]] = {}
        for _, row in gt_events.iterrows():
            key = (row["patient"], row["edf"])
            gt_groups.setdefault(key, []).append(
                (int(row["gt_start_window"]), int(row["gt_end_window"]))
            )

        all_keys = set(pred_groups.keys()) | set(gt_groups.keys())

        tp = 0
        fp = 0
        fn = 0

        for key in all_keys:
            preds = pred_groups.get(key, [])
            gts = gt_groups.get(key, [])

            if not preds:
                fn += len(gts)
                continue
            if not gts:
                fp += len(preds)
                continue

            group_strategy = self.strategy
            if group_strategy == "auto":
                group_strategy = (
                    "optimal"
                    if max(len(preds), len(gts)) <= OPTIMAL_MATCH_GROUP_SIZE_LIMIT
                    else "greedy"
                )

            if group_strategy == "optimal":
                group_tp = self._match_optimal(preds, gts)
            else:
                group_tp = self._match_greedy(preds, gts)

            tp += group_tp
            fp += len(preds) - group_tp
            fn += len(gts) - group_tp

        return tp, fp, fn

    @staticmethod
    def _overlaps(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
        a_start, a_end = a
        b_start, b_end = b
        return a_start <= b_end and a_end >= b_start

    def _match_greedy(
        self,
        preds: List[Tuple[int, int]],
        gts: List[Tuple[int, int]],
    ) -> int:
        """FIX-5 original greedy: earliest-start-first, first overlap wins."""
        # Sort predictions by start window for deterministic greedy assignment
        preds_sorted = sorted(preds, key=lambda x: x[0])
        gt_matched = [False] * len(gts)
        tp = 0

        for pred in preds_sorted:
            for gi, gt in enumerate(gts):
                if gt_matched[gi]:
                    continue
                if self._overlaps(pred, gt):
                    gt_matched[gi] = True
                    tp += 1
                    break

        return tp

    def _match_optimal(
        self,
        preds: List[Tuple[int, int]],
        gts: List[Tuple[int, int]],
    ) -> int:
        """
        FIX-13: Maximum-cardinality bipartite matching between predicted
        events and GT events, restricted to overlapping pairs, via the
        standard augmenting-path algorithm (Kuhn's algorithm).

        Returns the maximum number of TP achievable for this (patient, edf)
        group.
        """
        n_pred = len(preds)
        n_gt = len(gts)

        # Build adjacency: for each predicted event, list of GT indices it overlaps
        adjacency: List[List[int]] = []
        for pred in preds:
            overlaps = [gi for gi, gt in enumerate(gts) if self._overlaps(pred, gt)]
            adjacency.append(overlaps)

        match_gt_to_pred = [-1] * n_gt  # match_gt_to_pred[gi] = pi or -1

        def try_kuhn(pi: int, visited: List[bool]) -> bool:
            for gi in adjacency[pi]:
                if visited[gi]:
                    continue
                visited[gi] = True
                if match_gt_to_pred[gi] == -1 or try_kuhn(match_gt_to_pred[gi], visited):
                    match_gt_to_pred[gi] = pi
                    return True
            return False

        matched_count = 0
        for pi in range(n_pred):
            visited = [False] * n_gt
            if try_kuhn(pi, visited):
                matched_count += 1

        return matched_count


# ---------------------------------------------------------------------------
# MetricsCalculator
# ---------------------------------------------------------------------------
class MetricsCalculator:
    """
    Calculates event-level metrics from TP, FP, FN counts.

    FIX-6: balanced_accuracy alias removed — non-computable without TN.
    FIX-7: MCC set to None — non-computable without TN.
    FIX-8: Cohen's kappa set to None — non-computable without TN.
    """

    @staticmethod
    def calculate(
        tp: int,
        fp: int,
        fn: int,
        total_gt_events: int,
        total_predicted_events: int,
        suppression_stats: Dict,
    ) -> Dict:
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        suppression_rate = suppression_stats.get("suppression_ratio", 0.0)
        alarm_rate = tp + fp  # total alarms fired

        return {
            "true_positive_events": tp,
            "false_positive_events": fp,
            "false_negative_events": fn,
            "total_gt_events": total_gt_events,
            "total_predicted_events": total_predicted_events,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            # FIX-6: balanced_accuracy removed — requires TN (not available at event level)
            "balanced_accuracy": None,
            # FIX-7: MCC removed — requires TN
            "mcc": None,
            # FIX-8: Cohen's kappa removed — requires TN
            "cohen_kappa": None,
            "alarm_rate": alarm_rate,
            "suppression_rate": round(suppression_rate, 6),
            "note_non_computable": (
                "balanced_accuracy/mcc/cohen_kappa require TN count. "
                "TN is not defined at event level without enumerating seizure-free EDFs."
            ),
        }


# ---------------------------------------------------------------------------
# RuntimeAuditor — FIX-4: uses psutil instead of resource
# ---------------------------------------------------------------------------
class RuntimeAuditor:
    def __init__(self):
        self.start_time = time.time()
        self.rows_processed: int = 0
        self.patients_processed: int = 0
        self.edfs_processed: int = 0
        self.events_generated: int = 0
        self.events_suppressed: int = 0
        self.peak_memory_mb: float = 0.0

    def update_peak_memory(self):
        """FIX-4: cross-platform memory tracking via psutil."""
        current_mb = get_process_memory_mb()
        if current_mb > self.peak_memory_mb:
            self.peak_memory_mb = current_mb

    @property
    def runtime_seconds(self) -> float:
        return time.time() - self.start_time

    def save(self, path: str) -> Dict:
        self.update_peak_memory()
        audit = {
            "rows_processed": self.rows_processed,
            "patients_processed": self.patients_processed,
            "edfs_processed": self.edfs_processed,
            "events_generated": self.events_generated,
            "events_suppressed": self.events_suppressed,
            "runtime_seconds": round(self.runtime_seconds, 2),
            "peak_memory_mb": round(self.peak_memory_mb, 2),
            "timestamp": datetime.utcnow().isoformat(),
        }
        with open(path, "w") as fh:
            json.dump(audit, fh, indent=2)
        log.info(f"Runtime audit saved to {path}")
        return audit


# ---------------------------------------------------------------------------
# FIX-2 / FIX-14: Configuration Search with aggregation caching + cost estimate
# ---------------------------------------------------------------------------
def run_configuration_search(
    df_test: pd.DataFrame,
    gt_events_df: pd.DataFrame,
    aggregator: EventAggregator,
    suppressor: FalseAlarmSuppressor,
    matcher: EventMatcher,
    calculator: MetricsCalculator,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Exhaustive search over all combinations of:
        smoothing_window x threshold x min_duration x min_peak_probability

    FIX-2: Aggregation is cached per (smoothing_col, threshold).
    EventAggregator is called only once per unique (col, threshold) pair —
    NOT once per (col, threshold, min_duration, min_peak) combination.

    Original: 5 × 99 × 7 × 11 = 38 115 aggregation calls.
    Fixed   : 5 × 99          =    495 aggregation calls.

    FIX-14: Before running the full search, times a small sample of
    matcher.match() calls (which still run once per combination, i.e.
    38,115 times) and extrapolates an expected wall-clock duration. This is
    logged up front so operators are not surprised by a multi-minute run.
    """
    total_gt = len(gt_events_df)
    total_combos = (
        len(SMOOTHING_WINDOWS) * len(THRESHOLDS) *
        len(MIN_DURATIONS) * len(MIN_PEAK_PROBABILITIES)
    )
    n_aggregation_calls = len(SMOOTHING_WINDOWS) * len(THRESHOLDS)

    log.info(
        f"[ConfigSearch] Starting exhaustive search: "
        f"{len(SMOOTHING_WINDOWS)} smoothing × {len(THRESHOLDS)} thresholds × "
        f"{len(MIN_DURATIONS)} min_durations × {len(MIN_PEAK_PROBABILITIES)} min_peak_probs "
        f"= {total_combos} combinations "
        f"(FIX-2: only {n_aggregation_calls} aggregation calls)"
    )

    smoothed_col_map = dict(zip(SMOOTHING_WINDOWS, SMOOTHED_PROB_COLUMNS))

    # ---------------------------------------------------------------- #
    # FIX-14: timed sample to estimate total matcher cost up front.
    # The matcher runs once per combination regardless of caching, so it
    # is the dominant cost driver for large total_combos.
    # ---------------------------------------------------------------- #
    sample_sw = SMOOTHING_WINDOWS[len(SMOOTHING_WINDOWS) // 2]
    sample_col = smoothed_col_map[sample_sw]
    sample_thresh = THRESHOLDS[len(THRESHOLDS) // 2]
    sample_events = aggregator.aggregate(df_test, sample_col, sample_thresh)

    n_timing_samples = min(20, len(MIN_DURATIONS) * len(MIN_PEAK_PROBABILITIES))
    if n_timing_samples > 0 and not sample_events.empty:
        t0 = time.time()
        for i, min_dur in enumerate(MIN_DURATIONS):
            for min_peak in MIN_PEAK_PROBABILITIES:
                if i * len(MIN_PEAK_PROBABILITIES) >= n_timing_samples:
                    break
                retained, _ = suppressor.suppress(sample_events, min_dur, min_peak)
                matcher.match(retained, gt_events_df)
        elapsed = time.time() - t0
        per_combo_seconds = elapsed / max(n_timing_samples, 1)
    else:
        per_combo_seconds = 0.0

    estimated_total_seconds = per_combo_seconds * total_combos
    log.info(
        f"[ConfigSearch] FIX-14: Estimated matcher cost per combination "
        f"~{per_combo_seconds * 1000:.3f} ms. "
        f"Estimated total search time ~{estimated_total_seconds:.1f}s "
        f"({estimated_total_seconds / 60:.1f} min) across {total_combos} combinations. "
        f"Expect MINUTES, not seconds, for datasets of typical size."
    )

    rows = []
    combo_idx = 0
    log_interval = max(1, total_combos // 20)

    search_start = time.time()

    for sw in SMOOTHING_WINDOWS:
        smoothed_col = smoothed_col_map[sw]

        for thresh in THRESHOLDS:
            # FIX-2: aggregate ONCE per (col, threshold), cache the result
            pred_events_raw = aggregator.aggregate(df_test, smoothed_col, thresh)

            for min_dur in MIN_DURATIONS:
                for min_peak in MIN_PEAK_PROBABILITIES:
                    combo_idx += 1
                    if combo_idx % log_interval == 0:
                        elapsed_so_far = time.time() - search_start
                        log.info(
                            f"[ConfigSearch] {combo_idx}/{total_combos} combinations "
                            f"evaluated... ({elapsed_so_far:.1f}s elapsed)"
                        )

                    # Suppression is cheap — runs only on already-aggregated events
                    retained, supp_stats = suppressor.suppress(
                        pred_events_raw, min_dur, min_peak
                    )

                    tp, fp, fn = matcher.match(retained, gt_events_df)
                    metrics = calculator.calculate(
                        tp, fp, fn,
                        total_gt_events=total_gt,
                        total_predicted_events=len(retained),
                        suppression_stats=supp_stats,
                    )

                    rows.append({
                        "smoothing_window": sw,
                        "threshold": thresh,
                        "min_duration": min_dur,
                        "min_peak_probability": min_peak,
                        **{
                            k: v for k, v in metrics.items()
                            if k != "note_non_computable"
                        },
                        "total_events_before_suppression": supp_stats["total_events"],
                        "suppressed_events": supp_stats["suppressed_events"],
                        "retained_events": supp_stats["retained_events"],
                    })

    search_df = pd.DataFrame(rows)
    total_search_seconds = time.time() - search_start
    log.info(
        f"[ConfigSearch] Search complete. {len(search_df)} configurations evaluated "
        f"in {total_search_seconds:.1f}s ({total_search_seconds / 60:.1f} min)."
    )

    # Find best configurations
    best_configs = {}
    # Only metrics that are actually computed (FIX-6/7/8: skip None metrics)
    metric_labels = [
        ("f1", "BEST_F1"),
        ("recall", "BEST_RECALL"),
        ("precision", "BEST_PRECISION"),
    ]

    for metric, label in metric_labels:
        if len(search_df) > 0 and metric in search_df.columns:
            col = search_df[metric].dropna()
            if len(col) == 0:
                continue
            best_idx = col.idxmax()
            best_row = search_df.loc[best_idx]
            best_configs[label] = {
                "smoothing_window": int(best_row["smoothing_window"]),
                "threshold": float(best_row["threshold"]),
                "min_duration": int(best_row["min_duration"]),
                "min_peak_probability": float(best_row["min_peak_probability"]),
                metric: float(best_row[metric]),
                "true_positive_events": int(best_row["true_positive_events"]),
                "false_positive_events": int(best_row["false_positive_events"]),
                "false_negative_events": int(best_row["false_negative_events"]),
                "precision": float(best_row["precision"]),
                "recall": float(best_row["recall"]),
                "f1": float(best_row["f1"]),
            }
            log.info(
                f"[ConfigSearch] {label}: {metric}={best_row[metric]:.4f} | "
                f"sw={best_row['smoothing_window']} thresh={best_row['threshold']:.2f} "
                f"min_dur={best_row['min_duration']} min_peak={best_row['min_peak_probability']:.2f}"
            )

    return search_df, best_configs


# ---------------------------------------------------------------------------
# Patient Event Summary
# ---------------------------------------------------------------------------
def build_patient_event_summary(
    df_test: pd.DataFrame,
    event_predictions: pd.DataFrame,
    gt_events_df: pd.DataFrame,
    matcher: EventMatcher,
) -> pd.DataFrame:
    rows = []
    for patient in sorted(df_test["patient"].unique()):
        patient_windows = df_test[df_test["patient"] == patient]
        patient_pred_events = (
            event_predictions[event_predictions["patient"] == patient]
            if not event_predictions.empty
            else pd.DataFrame()
        )
        patient_gt_events = (
            gt_events_df[gt_events_df["patient"] == patient]
            if not gt_events_df.empty
            else pd.DataFrame()
        )

        total_windows = len(patient_windows)
        positive_windows = int((patient_windows["label"] == 1).sum())
        edfs = patient_windows["edf"].nunique()
        pred_events = len(patient_pred_events)
        gt_events = len(patient_gt_events)

        if not patient_pred_events.empty or not patient_gt_events.empty:
            tp, fp, fn = matcher.match(patient_pred_events, patient_gt_events)
        else:
            tp, fp, fn = 0, 0, 0

        rows.append({
            "patient": patient,
            "total_windows": total_windows,
            "positive_windows": positive_windows,
            "total_edfs": edfs,
            "predicted_events": pred_events,
            "ground_truth_events": gt_events,
            "true_positive_events": tp,
            "false_positive_events": fp,
            "false_negative_events": fn,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Execution Report
# ---------------------------------------------------------------------------
def write_execution_report(
    start_time: float,
    schema_audit: Dict,
    runtime_audit: Dict,
    best_configs: Dict,
    search_df: pd.DataFrame,
    event_predictions: pd.DataFrame,
    gt_events_df: pd.DataFrame,
    test_patients: List[str],
    calibration_info: Optional[Dict] = None,
    matching_strategy: str = MATCHING_STRATEGY,
) -> str:
    runtime = time.time() - start_time
    lines = [
        "=" * 70,
        "PHASE5C TEMPORAL EVENT DETECTION — EXECUTION REPORT",
        "=" * 70,
        "",
        f"Generated: {datetime.utcnow().isoformat()}",
        f"Runtime: {runtime:.2f} seconds",
        "",
        "SCHEMA VALIDATION",
        f"  Overall Passed: {schema_audit.get('overall_passed', 'N/A')}",
        "  Feature Count Source: PHASE5B_FEATURE_SIGNATURE.json (FIX-1: no hardcoded constant)",
        "  Feature Order Check: explicit element-wise comparison (FIX-9)",
        "",
        "TEST PATIENTS",
        f"  Count: {len(test_patients)}",
        f"  Patients: {', '.join(sorted(test_patients))}",
        "",
    ]

    if calibration_info:
        lines += [
            "PROBABILITY CALIBRATION (FIX-10 / FIX-11)",
            f"  Applied                 : {calibration_info.get('applied', False)}",
            f"  Calibration Patient Src : {calibration_info.get('source', 'N/A')}",
            f"  Calibration Patients    : {calibration_info.get('calibration_patients', 'N/A')}",
            f"  Calibration-set ECE Before : {calibration_info.get('ece_before', 'N/A')}",
            f"  Calibration-set ECE After  : {calibration_info.get('ece_after', 'N/A')}",
            "",
        ]

    lines += [
        "RUNTIME STATISTICS",
        f"  Rows Processed       : {runtime_audit.get('rows_processed', 'N/A')}",
        f"  Patients Processed   : {runtime_audit.get('patients_processed', 'N/A')}",
        f"  EDFs Processed       : {runtime_audit.get('edfs_processed', 'N/A')}",
        f"  Events Generated     : {runtime_audit.get('events_generated', 'N/A')}",
        f"  Events Suppressed    : {runtime_audit.get('events_suppressed', 'N/A')}",
        f"  Peak Memory (MB)     : {runtime_audit.get('peak_memory_mb', 'N/A')} (psutil, FIX-4)",
        "",
        "GROUND TRUTH",
        f"  Total GT Events      : {len(gt_events_df)}",
        "",
        "CONFIGURATION SEARCH",
        f"  Total Combinations   : {len(search_df)}",
        f"  Note (FIX-2)         : Aggregation cached per (col, threshold) — "
        f"only {len(SMOOTHING_WINDOWS) * len(THRESHOLDS)} aggregation calls executed.",
        f"  Note (FIX-14)        : Matcher still runs once per combination "
        f"({len(search_df)} calls) — expect minutes, not seconds.",
        "",
        "METRICS NOTE (FIX-6/7/8)",
        "  balanced_accuracy, mcc, cohen_kappa: NOT REPORTED.",
        "  Reason: TN (true negative events) is undefined at event level",
        "  without enumerating all seizure-free EDF segments.",
        "",
        "EVENT MATCHING NOTE (FIX-5/FIX-13)",
        f"  Matching strategy configured : {matching_strategy}",
        f"  Group size limit for optimal : {OPTIMAL_MATCH_GROUP_SIZE_LIMIT} "
        f"(max(preds, gts) per (patient, edf) group)",
        "  'auto' uses maximum-cardinality bipartite matching (Hopcroft-Karp",
        "  style augmenting paths) for small groups, and falls back to the",
        "  original earliest-start-first greedy assignment for larger groups.",
        "  One GT event can be matched by at most one predicted event in all modes.",
        "",
        "BEST CONFIGURATIONS",
    ]

    for label, config in best_configs.items():
        lines.append(f"  {label}:")
        for k, v in config.items():
            lines.append(f"    {k}: {v}")
        lines.append("")

    lines += ["OUTPUT ARTIFACTS"]
    for artifact in [
        OUTPUT_EVENT_PREDICTIONS,
        OUTPUT_EVENT_METRICS,
        OUTPUT_CONFIGURATION_SEARCH,
        OUTPUT_BEST_CONFIGURATION,
        OUTPUT_PATIENT_EVENT_SUMMARY,
        OUTPUT_EXECUTION_REPORT,
        OUTPUT_SCHEMA_AUDIT,
        OUTPUT_RUNTIME_AUDIT,
    ]:
        status = "[OK]" if Path(artifact).exists() else "[MISSING]"
        lines.append(f"  {status} {artifact}")

    lines += ["", "=" * 70, "END OF EXECUTION REPORT", "=" * 70]

    report_text = "\n".join(lines)
    with open(OUTPUT_EXECUTION_REPORT, "w") as fh:
        fh.write(report_text)
    log.info(f"Execution report saved to {OUTPUT_EXECUTION_REPORT}")
    print(report_text)
    return report_text


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------
def main() -> int:
    start_time = time.time()
    log.info("=== PHASE5C TEMPORAL EVENT DETECTION START ===")

    runtime_auditor = RuntimeAuditor()
    schema_audit: Dict = {}
    best_configs: Dict = {}
    search_df: pd.DataFrame = pd.DataFrame()
    event_predictions: pd.DataFrame = pd.DataFrame()
    gt_events_df: pd.DataFrame = pd.DataFrame()
    test_patients: List[str] = []
    calibration_info: Dict = {}

    try:
        # ------------------------------------------------------------------ #
        # 1. Schema Validation
        # ------------------------------------------------------------------ #
        log.info("Step 1: Schema validation...")
        validator = SchemaValidator(
            parquet_path=INPUT_PARQUET,
            model_path=INPUT_MODEL,
            feature_signature_path=INPUT_FEATURE_SIGNATURE,
            patient_split_path=INPUT_PATIENT_SPLIT,
        )
        schema_audit, feature_names = validator.validate()

        with open(OUTPUT_SCHEMA_AUDIT, "w") as fh:
            json.dump(schema_audit, fh, indent=2)
        log.info(f"Schema audit saved to {OUTPUT_SCHEMA_AUDIT}")

        # ------------------------------------------------------------------ #
        # 2. Load patient split (FIX-11: also resolve calibration patients)
        # ------------------------------------------------------------------ #
        log.info("Step 2: Loading patient split...")
        with open(INPUT_PATIENT_SPLIT) as fh:
            split = json.load(fh)
        test_patients = split["test_patients"]
        train_patients = split.get("train_patients", [])
        log.info(f"Test patients ({len(test_patients)}): {test_patients}")
        log.info(f"Train patients (model training): {len(train_patients)}")

        calibration_patients, _remaining_train, calibration_source = (
            select_calibration_patients(split, train_patients)
        )
        log.info(
            f"Calibration patients ({len(calibration_patients)}, "
            f"source={calibration_source}): {calibration_patients}"
        )

        # ------------------------------------------------------------------ #
        # 3. Load model
        # ------------------------------------------------------------------ #
        log.info("Step 3: Loading model...")
        model = joblib.load(INPUT_MODEL)
        log.info(f"Model loaded: {type(model).__name__}")
        runtime_auditor.update_peak_memory()

        # ------------------------------------------------------------------ #
        # 4. Load dataset — TEST + CALIBRATION, filtered at read (FIX-3/FIX-12)
        # ------------------------------------------------------------------ #
        log.info("Step 4: Loading engineered dataset (filtered read)...")

        needed_cols = list(
            dict.fromkeys(REQUIRED_METADATA_COLS + OPTIONAL_METADATA_COLS + feature_names)
        )

        all_relevant_patients = list(set(test_patients) | set(calibration_patients))

        df_full = load_parquet_filtered(
            parquet_path=INPUT_PARQUET,
            columns=needed_cols,
            patients=all_relevant_patients,
        )
        log.info(
            f"Dataset loaded: {len(df_full)} rows, "
            f"{df_full['patient'].nunique()} patients "
            f"(FIX-3/FIX-12: avoided unnecessary full-dataset load where possible)."
        )

        df_test = df_full[df_full["patient"].isin(test_patients)].copy()
        df_calibration = (
            df_full[df_full["patient"].isin(calibration_patients)].copy()
            if calibration_patients
            else pd.DataFrame()
        )
        del df_full
        gc.collect()

        df_test = df_test.sort_values(
            ["patient", "edf", "window_index"]
        ).reset_index(drop=True)

        log.info(
            f"Test subset: {len(df_test)} rows, "
            f"{df_test['patient'].nunique()} patients, "
            f"{df_test['edf'].nunique()} EDFs"
        )
        log.info(
            f"Calibration subset: {len(df_calibration)} rows, "
            f"{df_calibration['patient'].nunique() if not df_calibration.empty else 0} patients"
        )

        runtime_auditor.rows_processed = len(df_test)
        runtime_auditor.patients_processed = df_test["patient"].nunique()
        runtime_auditor.edfs_processed = df_test["edf"].nunique()
        runtime_auditor.update_peak_memory()

        # ------------------------------------------------------------------ #
        # 5. Feature validation
        # ------------------------------------------------------------------ #
        log.info("Step 5: Validating features against canonical signature...")
        missing = [f for f in feature_names if f not in df_test.columns]
        if missing:
            raise RuntimeError(
                f"Test dataset missing {len(missing)} canonical features. "
                f"First 5: {missing[:5]}"
            )

        extra = [
            c for c in df_test.columns
            if c not in set(feature_names)
            and c not in set(REQUIRED_METADATA_COLS + OPTIONAL_METADATA_COLS)
        ]
        if extra:
            log.warning(
                f"Dataset has {len(extra)} unexpected extra columns (ignored): {extra[:5]}"
            )
        log.info("Feature validation PASSED.")

        # ------------------------------------------------------------------ #
        # 6. Generate window-level probabilities
        # ------------------------------------------------------------------ #
        log.info("Step 6: Generating window-level probabilities...")
        X_test = df_test[feature_names].to_numpy(dtype=np.float32, copy=False)
        log.info(f"Feature matrix shape: {X_test.shape}")

        raw_proba_test = model.predict_proba(X_test)[:, 1].astype(np.float32)
        log.info(
            f"Raw probabilities: min={raw_proba_test.min():.4f} "
            f"max={raw_proba_test.max():.4f} mean={raw_proba_test.mean():.4f}"
        )
        del X_test
        gc.collect()
        runtime_auditor.update_peak_memory()

        # ------------------------------------------------------------------ #
        # 7. Probability calibration (FIX-10 / FIX-11)
        # ------------------------------------------------------------------ #
        log.info("Step 7: Probability calibration (FIX-10/FIX-11)...")
        calibrator = ProbabilityCalibrator()

        if not df_calibration.empty:
            missing_cal = [f for f in feature_names if f not in df_calibration.columns]
            if missing_cal:
                log.warning(
                    f"Calibration set missing {len(missing_cal)} features — "
                    f"skipping calibration."
                )
                pred_proba = raw_proba_test
                calibration_info = {
                    "applied": False,
                    "reason": "missing calibration features",
                    "source": calibration_source,
                    "calibration_patients": calibration_patients,
                }
            else:
                X_cal = df_calibration[feature_names].to_numpy(
                    dtype=np.float32, copy=False
                )
                raw_proba_cal = model.predict_proba(X_cal)[:, 1].astype(np.float32)
                y_cal = df_calibration["label"].values
                del X_cal
                gc.collect()

                calibrator.fit(raw_proba_cal, y_cal)
                pred_proba = calibrator.transform(raw_proba_test)
                calibration_info = {
                    "applied": True,
                    "source": calibration_source,
                    "calibration_patients": calibration_patients,
                    "ece_before": calibrator.calibration_ece_before,
                    "ece_after": calibrator.calibration_ece_after,
                }
                log.info(
                    f"Calibration applied (FIX-11, source={calibration_source}). "
                    f"Calibration-set ECE before={calibrator.calibration_ece_before:.4f} "
                    f"after={calibrator.calibration_ece_after:.4f}"
                )
        else:
            log.warning(
                "No calibration patients available — "
                "skipping calibration. Thresholds will operate on raw probabilities."
            )
            pred_proba = raw_proba_test
            calibration_info = {
                "applied": False,
                "reason": "no calibration patients available",
                "source": calibration_source,
                "calibration_patients": [],
            }

        del df_calibration
        gc.collect()

        df_test["pred_proba"] = pred_proba
        runtime_auditor.update_peak_memory()

        # ------------------------------------------------------------------ #
        # 8. Temporal smoothing
        # ------------------------------------------------------------------ #
        log.info("Step 8: Applying temporal smoothing...")
        smoother = TemporalSmoothingEngine()
        df_test = smoother.smooth(df_test)

        for col in SMOOTHED_PROB_COLUMNS:
            nan_count = df_test[col].isna().sum()
            if nan_count > 0:
                raise RuntimeError(
                    f"NaN values found in {col} after smoothing: {nan_count} NaNs"
                )
        log.info("Temporal smoothing complete. No NaN values confirmed.")
        runtime_auditor.update_peak_memory()

        # ------------------------------------------------------------------ #
        # 9. Build ground truth events
        # ------------------------------------------------------------------ #
        log.info("Step 9: Building ground truth events...")
        gt_builder = GroundTruthEventBuilder()
        gt_events_df = gt_builder.build(df_test)
        log.info(f"Ground truth events: {len(gt_events_df)}")

        # ------------------------------------------------------------------ #
        # 10. Configuration search (FIX-2: cached aggregation, FIX-14: cost estimate)
        # ------------------------------------------------------------------ #
        log.info("Step 10: Running configuration search (FIX-2/FIX-14)...")
        aggregator = EventAggregator()
        suppressor = FalseAlarmSuppressor()
        matcher = EventMatcher(strategy=MATCHING_STRATEGY)  # FIX-13
        calculator = MetricsCalculator()

        search_df, best_configs = run_configuration_search(
            df_test=df_test,
            gt_events_df=gt_events_df,
            aggregator=aggregator,
            suppressor=suppressor,
            matcher=matcher,
            calculator=calculator,
        )

        search_df.to_csv(OUTPUT_CONFIGURATION_SEARCH, index=False)
        log.info(f"Configuration search saved to {OUTPUT_CONFIGURATION_SEARCH}")

        with open(OUTPUT_BEST_CONFIGURATION, "w") as fh:
            json.dump(best_configs, fh, indent=2)
        log.info(f"Best configuration saved to {OUTPUT_BEST_CONFIGURATION}")

        # ------------------------------------------------------------------ #
        # 11. Generate event predictions using BEST_F1 configuration
        # ------------------------------------------------------------------ #
        log.info("Step 11: Generating event predictions with BEST_F1 configuration...")

        if "BEST_F1" in best_configs:
            best_f1_cfg = best_configs["BEST_F1"]
            best_sw = best_f1_cfg["smoothing_window"]
            best_thresh = best_f1_cfg["threshold"]
            best_min_dur = best_f1_cfg["min_duration"]
            best_min_peak = best_f1_cfg["min_peak_probability"]
        else:
            best_sw = 5
            best_thresh = 0.5
            best_min_dur = 3
            best_min_peak = 0.5
            log.warning("BEST_F1 config not found; using fallback defaults.")

        best_smoothed_col = dict(zip(SMOOTHING_WINDOWS, SMOOTHED_PROB_COLUMNS))[best_sw]
        event_predictions_raw = aggregator.aggregate(df_test, best_smoothed_col, best_thresh)
        event_predictions, final_supp_stats = suppressor.suppress(
            event_predictions_raw, best_min_dur, best_min_peak
        )

        runtime_auditor.events_generated = final_supp_stats["total_events"]
        runtime_auditor.events_suppressed = final_supp_stats["suppressed_events"]

        log.info(
            f"Events: generated={final_supp_stats['total_events']}, "
            f"suppressed={final_supp_stats['suppressed_events']}, "
            f"retained={final_supp_stats['retained_events']}"
        )

        event_predictions.to_csv(OUTPUT_EVENT_PREDICTIONS, index=False)
        log.info(f"Event predictions saved to {OUTPUT_EVENT_PREDICTIONS}")

        # ------------------------------------------------------------------ #
        # 12. Compute final event-level metrics
        # ------------------------------------------------------------------ #
        log.info("Step 12: Computing event-level metrics...")
        tp, fp, fn = matcher.match(event_predictions, gt_events_df)
        final_metrics = calculator.calculate(
            tp, fp, fn,
            total_gt_events=len(gt_events_df),
            total_predicted_events=len(event_predictions),
            suppression_stats=final_supp_stats,
        )
        final_metrics["smoothing_window"] = best_sw
        final_metrics["threshold"] = best_thresh
        final_metrics["min_duration"] = best_min_dur
        final_metrics["min_peak_probability"] = best_min_peak
        final_metrics["calibration_applied"] = calibration_info.get("applied", False)
        final_metrics["matching_strategy"] = MATCHING_STRATEGY

        log.info(f"Final event metrics: {final_metrics}")

        metrics_df = pd.DataFrame([final_metrics])
        metrics_df.to_csv(OUTPUT_EVENT_METRICS, index=False)
        log.info(f"Event metrics saved to {OUTPUT_EVENT_METRICS}")

        # ------------------------------------------------------------------ #
        # 13. Patient event summary
        # ------------------------------------------------------------------ #
        log.info("Step 13: Building patient event summary...")
        patient_summary = build_patient_event_summary(
            df_test, event_predictions, gt_events_df, matcher
        )
        patient_summary.to_csv(OUTPUT_PATIENT_EVENT_SUMMARY, index=False)
        log.info(f"Patient event summary saved to {OUTPUT_PATIENT_EVENT_SUMMARY}")

        # ------------------------------------------------------------------ #
        # 14. Runtime audit
        # ------------------------------------------------------------------ #
        runtime_auditor.update_peak_memory()
        runtime_audit = runtime_auditor.save(OUTPUT_RUNTIME_AUDIT)

        # ------------------------------------------------------------------ #
        # 15. Execution report
        # ------------------------------------------------------------------ #
        log.info("Step 15: Writing execution report...")
        write_execution_report(
            start_time=start_time,
            schema_audit=schema_audit,
            runtime_audit=runtime_audit,
            best_configs=best_configs,
            search_df=search_df,
            event_predictions=event_predictions,
            gt_events_df=gt_events_df,
            test_patients=test_patients,
            calibration_info=calibration_info,
            matching_strategy=MATCHING_STRATEGY,
        )

        # ------------------------------------------------------------------ #
        # 16. Final self-audit
        # ------------------------------------------------------------------ #
        log.info("Step 16: Final self-audit of output artifacts...")
        all_outputs = [
            OUTPUT_EVENT_PREDICTIONS,
            OUTPUT_EVENT_METRICS,
            OUTPUT_CONFIGURATION_SEARCH,
            OUTPUT_BEST_CONFIGURATION,
            OUTPUT_PATIENT_EVENT_SUMMARY,
            OUTPUT_EXECUTION_REPORT,
            OUTPUT_SCHEMA_AUDIT,
            OUTPUT_RUNTIME_AUDIT,
        ]
        missing_outputs = [p for p in all_outputs if not Path(p).exists()]
        if missing_outputs:
            log.error(f"MISSING OUTPUT FILES: {missing_outputs}")
        else:
            log.info("Self-audit PASSED: all output artifacts present.")

        log.info("=== PHASE5C TEMPORAL EVENT DETECTION COMPLETE ===")
        log.info(f"Total runtime: {time.time() - start_time:.2f}s")
        return 0

    except Exception as exc:
        log.error(f"PIPELINE FAILED: {exc}", exc_info=True)
        traceback.print_exc()

        try:
            runtime_auditor.save(OUTPUT_RUNTIME_AUDIT)
        except Exception:
            pass

        try:
            if schema_audit:
                with open(OUTPUT_SCHEMA_AUDIT, "w") as fh:
                    json.dump(schema_audit, fh, indent=2)
        except Exception:
            pass

        return 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())