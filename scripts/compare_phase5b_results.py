"""
compare_phase5b_results.py
--------------------------
Production-grade Phase 5B EEG benchmark analysis script.
Loads Phase 5B outputs, validates inputs, and generates five CSV benchmark reports
with a structured console summary.
"""

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
METRICS_FILE         = Path("PHASE5B_METRICS.json")
THRESHOLD_SWEEP_FILE = Path("PHASE5B_THRESHOLD_SWEEP.csv")
FEATURE_IMP_FILE     = Path("PHASE5B_FEATURE_IMPORTANCE.csv")

OUTPUT_METRIC_SUMMARY      = Path("PHASE5B_METRIC_SUMMARY.csv")
OUTPUT_BEST_THRESHOLDS     = Path("PHASE5B_BEST_THRESHOLDS.csv")
OUTPUT_CATEGORY_SUMMARY    = Path("PHASE5B_FEATURE_CATEGORY_SUMMARY.csv")
OUTPUT_TOP50_FEATURES      = Path("PHASE5B_TOP50_FEATURES.csv")
OUTPUT_THRESHOLD_TOP20     = Path("PHASE5B_THRESHOLD_TOP20.csv")

REQUIRED_METRICS = [
    "roc_auc", "pr_auc", "balanced_accuracy", "recall",
    "specificity", "precision", "f1", "mcc", "kappa",
    "brier_score", "calibration_error",
]

FEATURE_CATEGORIES = ["STATIC", "LAG1", "LAG3", "ROLLING_MEAN", "STABILITY", "POSITION"]

THRESHOLD_REQUIRED_COLS = [
    "threshold", "precision", "recall", "specificity",
    "f1", "balanced_accuracy", "mcc", "kappa",
]

# ---------------------------------------------------------------------------
# File validation
# ---------------------------------------------------------------------------

def validate_input_files() -> None:
    """Raise FileNotFoundError if any required input file is missing."""
    missing = [f for f in [METRICS_FILE, THRESHOLD_SWEEP_FILE, FEATURE_IMP_FILE] if not f.exists()]
    if missing:
        for m in missing:
            logger.error("Required input file not found: %s", m)
        raise FileNotFoundError(
            f"Missing input files: {[str(m) for m in missing]}. "
            "Ensure all Phase 5B output files are in the working directory."
        )
    logger.info("All required input files validated.")


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_metrics(path: Path) -> dict:
    """Load and validate PHASE5B_METRICS.json."""
    logger.info("Loading metrics from: %s", path)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in {path}: {exc}") from exc

    missing_keys = [k for k in REQUIRED_METRICS if k not in data]
    if missing_keys:
        logger.warning(
            "The following expected metric keys are absent from %s and will be NaN: %s",
            path, missing_keys,
        )
    return data


def load_threshold_sweep(path: Path) -> pd.DataFrame:
    """Load and validate PHASE5B_THRESHOLD_SWEEP.csv."""
    logger.info("Loading threshold sweep from: %s", path)
    df = pd.read_csv(path)
    missing_cols = [c for c in THRESHOLD_REQUIRED_COLS if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"PHASE5B_THRESHOLD_SWEEP.csv is missing required columns: {missing_cols}"
        )
    logger.info("Threshold sweep loaded: %d rows, %d columns.", len(df), len(df.columns))
    return df


def load_feature_importance(path: Path) -> pd.DataFrame:
    """Load and validate PHASE5B_FEATURE_IMPORTANCE.csv."""
    logger.info("Loading feature importance from: %s", path)
    df = pd.read_csv(path)
    required = ["feature", "importance"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"PHASE5B_FEATURE_IMPORTANCE.csv is missing required columns: {missing_cols}"
        )
    logger.info("Feature importance loaded: %d features.", len(df))
    return df


# ---------------------------------------------------------------------------
# Category inference
# ---------------------------------------------------------------------------

def infer_category(feature_name: str) -> str:
    """
    Infer the feature category from the feature name using prefix/substring matching.
    Priority order mirrors the FEATURE_CATEGORIES list.
    Returns 'OTHER' if no category matches.
    """
    name_upper = str(feature_name).upper()

    if "ROLLING_MEAN" in name_upper:
        return "ROLLING_MEAN"
    if "STABILITY" in name_upper:
        return "STABILITY"
    if "POSITION" in name_upper:
        return "POSITION"
    if "LAG3" in name_upper or "_LAG3" in name_upper or "LAG_3" in name_upper:
        return "LAG3"
    if "LAG1" in name_upper or "_LAG1" in name_upper or "LAG_1" in name_upper:
        return "LAG1"
    if "STATIC" in name_upper:
        return "STATIC"

    # Secondary heuristics: suffix patterns like _L1, _L3
    if name_upper.endswith("_L1") or name_upper.endswith("L1_"):
        return "LAG1"
    if name_upper.endswith("_L3") or name_upper.endswith("L3_"):
        return "LAG3"

    return "OTHER"


# ---------------------------------------------------------------------------
# Output 1 – Metric Summary
# ---------------------------------------------------------------------------

def build_metric_summary(metrics: dict) -> pd.DataFrame:
    """Build PHASE5B_METRIC_SUMMARY.csv from the metrics dictionary."""
    rows = []
    for key in REQUIRED_METRICS:
        value = metrics.get(key, np.nan)
        rows.append({"metric": key, "value": value})
    df = pd.DataFrame(rows, columns=["metric", "value"])
    return df


# ---------------------------------------------------------------------------
# Output 2 – Best Thresholds
# ---------------------------------------------------------------------------

def build_best_thresholds(sweep: pd.DataFrame) -> pd.DataFrame:
    """
    Extract best thresholds for F1, Recall, and Balanced Accuracy
    from the threshold sweep DataFrame.
    """
    # Best F1
    idx_f1 = sweep["f1"].idxmax()
    best_f1_threshold = float(sweep.loc[idx_f1, "threshold"])
    best_f1_value     = float(sweep.loc[idx_f1, "f1"])

    # Best Recall
    idx_recall = sweep["recall"].idxmax()
    best_recall_threshold = float(sweep.loc[idx_recall, "threshold"])
    best_recall_value     = float(sweep.loc[idx_recall, "recall"])

    # Best Balanced Accuracy
    idx_ba = sweep["balanced_accuracy"].idxmax()
    best_ba_threshold = float(sweep.loc[idx_ba, "threshold"])
    best_ba_value     = float(sweep.loc[idx_ba, "balanced_accuracy"])

    df = pd.DataFrame([
        {
            "best_f1_threshold":                   best_f1_threshold,
            "best_f1_value":                        best_f1_value,
            "best_recall_threshold":               best_recall_threshold,
            "best_recall_value":                    best_recall_value,
            "best_balanced_accuracy_threshold":    best_ba_threshold,
            "best_balanced_accuracy_value":         best_ba_value,
        }
    ])
    return df


# ---------------------------------------------------------------------------
# Output 3 – Feature Category Summary
# ---------------------------------------------------------------------------

def build_category_summary(feat_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate feature importances by category and compute percentage contributions.
    Categories are inferred from feature names if a 'category' column is absent.
    """
    df = feat_df.copy()

    if "category" not in df.columns:
        logger.info("No 'category' column found; inferring categories from feature names.")
        df["category"] = df["feature"].apply(infer_category)
    else:
        # Normalise existing values; fall back to inference for blanks
        df["category"] = df["category"].astype(str).str.strip().str.upper()
        mask_blank = df["category"].isin(["", "NAN", "NONE"])
        if mask_blank.any():
            df.loc[mask_blank, "category"] = df.loc[mask_blank, "feature"].apply(infer_category)

    total_imp = df["importance"].sum()
    if total_imp == 0:
        raise ValueError("Total feature importance sums to zero – cannot compute percentages.")

    summary = (
        df.groupby("category", as_index=False)
          .agg(
              feature_count=("feature", "count"),
              total_importance=("importance", "sum"),
              mean_importance=("importance", "mean"),
          )
    )
    summary["importance_percentage"] = (
        summary["total_importance"] / total_imp * 100
    ).round(4)

    # Force percentage to sum exactly to 100 by adjusting the largest bucket
    pct_sum = summary["importance_percentage"].sum()
    if not np.isclose(pct_sum, 100.0, atol=1e-6):
        idx_max = summary["importance_percentage"].idxmax()
        summary.loc[idx_max, "importance_percentage"] += 100.0 - pct_sum
        summary["importance_percentage"] = summary["importance_percentage"].round(4)

    summary = summary.sort_values("total_importance", ascending=False).reset_index(drop=True)

    # Reorder columns
    summary = summary[["category", "feature_count", "total_importance", "mean_importance", "importance_percentage"]]
    return summary


# ---------------------------------------------------------------------------
# Output 4 – Top 50 Features
# ---------------------------------------------------------------------------

def build_top50_features(feat_df: pd.DataFrame) -> pd.DataFrame:
    """Return the top-50 features ranked by importance descending."""
    df = feat_df.copy()

    if "category" not in df.columns:
        df["category"] = df["feature"].apply(infer_category)
    else:
        df["category"] = df["category"].astype(str).str.strip().str.upper()
        mask_blank = df["category"].isin(["", "NAN", "NONE"])
        if mask_blank.any():
            df.loc[mask_blank, "category"] = df.loc[mask_blank, "feature"].apply(infer_category)

    df = df.sort_values("importance", ascending=False).reset_index(drop=True)
    top50 = df.head(50).copy()
    top50.insert(0, "rank", range(1, len(top50) + 1))
    top50 = top50[["rank", "feature", "importance", "category"]]
    return top50


# ---------------------------------------------------------------------------
# Output 5 – Threshold Top 20
# ---------------------------------------------------------------------------

def build_threshold_top20(sweep: pd.DataFrame) -> pd.DataFrame:
    """Return the top-20 threshold rows sorted by F1 descending."""
    cols = ["threshold", "precision", "recall", "specificity",
            "f1", "balanced_accuracy", "mcc", "kappa"]
    df = sweep[cols].sort_values("f1", ascending=False).head(20).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Console report
# ---------------------------------------------------------------------------

def print_console_report(
    metrics: dict,
    best_thresh_df: pd.DataFrame,
    cat_summary: pd.DataFrame,
    output_files: list,
) -> None:
    """Print the structured Phase 5B Analysis Report to stdout."""

    bt = best_thresh_df.iloc[0]

    print()
    print("=" * 60)
    print("           PHASE 5B ANALYSIS REPORT")
    print("=" * 60)

    # --- Metrics Summary ---
    print("\nMetrics Summary")
    print("-" * 40)
    metric_display = {
        "ROC-AUC":  metrics.get("roc_auc",           np.nan),
        "PR-AUC":   metrics.get("pr_auc",             np.nan),
        "Recall":   metrics.get("recall",             np.nan),
        "Precision":metrics.get("precision",          np.nan),
        "F1":       metrics.get("f1",                 np.nan),
        "MCC":      metrics.get("mcc",                np.nan),
    }
    for label, value in metric_display.items():
        print(f"  {label:<18} {value:.6f}" if not np.isnan(value) else f"  {label:<18} N/A")

    # --- Best Thresholds ---
    print("\nBest Thresholds")
    print("-" * 40)
    print(f"  Best F1 Threshold               {bt['best_f1_threshold']:.4f}  (F1 = {bt['best_f1_value']:.6f})")
    print(f"  Best Recall Threshold           {bt['best_recall_threshold']:.4f}  (Recall = {bt['best_recall_value']:.6f})")
    print(f"  Best Balanced Accuracy Threshold{bt['best_balanced_accuracy_threshold']:.4f}  (BA = {bt['best_balanced_accuracy_value']:.6f})")

    # --- Feature Category Contribution ---
    print("\nFeature Category Contribution")
    print("-" * 40)
    for _, row in cat_summary.iterrows():
        cat   = str(row["category"])
        pct   = float(row["importance_percentage"])
        n     = int(row["feature_count"])
        total = float(row["total_importance"])
        print(f"  {cat:<16} {pct:6.2f}%   (n={n:>4}, total_imp={total:.6f})")

    # --- Generated Files ---
    print()
    print("=" * 60)
    print("SUCCESS")
    print()
    print("Generated Files:")
    for f in output_files:
        print(f"  {f}")
    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("Phase 5B Analysis Script starting.")

    # 1. Validate inputs
    try:
        validate_input_files()
    except FileNotFoundError as exc:
        logger.critical("%s", exc)
        sys.exit(1)

    # 2. Load inputs
    try:
        metrics   = load_metrics(METRICS_FILE)
        sweep_df  = load_threshold_sweep(THRESHOLD_SWEEP_FILE)
        feat_df   = load_feature_importance(FEATURE_IMP_FILE)
    except (ValueError, pd.errors.ParserError, KeyError) as exc:
        logger.critical("Failed to load input files: %s", exc)
        sys.exit(1)

    # 3. Build outputs
    try:
        logger.info("Building OUTPUT 1 – Metric Summary …")
        metric_summary_df = build_metric_summary(metrics)

        logger.info("Building OUTPUT 2 – Best Thresholds …")
        best_thresh_df = build_best_thresholds(sweep_df)

        logger.info("Building OUTPUT 3 – Feature Category Summary …")
        cat_summary_df = build_category_summary(feat_df)

        logger.info("Building OUTPUT 4 – Top 50 Features …")
        top50_df = build_top50_features(feat_df)

        logger.info("Building OUTPUT 5 – Threshold Top 20 …")
        top20_thresh_df = build_threshold_top20(sweep_df)

    except (ValueError, KeyError, IndexError) as exc:
        logger.critical("Error during analysis: %s", exc)
        sys.exit(1)

    # 4. Write CSVs
    output_files = []
    try:
        metric_summary_df.to_csv(OUTPUT_METRIC_SUMMARY,   index=False)
        logger.info("Written: %s", OUTPUT_METRIC_SUMMARY)
        output_files.append(str(OUTPUT_METRIC_SUMMARY))

        best_thresh_df.to_csv(OUTPUT_BEST_THRESHOLDS,    index=False)
        logger.info("Written: %s", OUTPUT_BEST_THRESHOLDS)
        output_files.append(str(OUTPUT_BEST_THRESHOLDS))

        cat_summary_df.to_csv(OUTPUT_CATEGORY_SUMMARY,   index=False)
        logger.info("Written: %s", OUTPUT_CATEGORY_SUMMARY)
        output_files.append(str(OUTPUT_CATEGORY_SUMMARY))

        top50_df.to_csv(OUTPUT_TOP50_FEATURES,           index=False)
        logger.info("Written: %s", OUTPUT_TOP50_FEATURES)
        output_files.append(str(OUTPUT_TOP50_FEATURES))

        top20_thresh_df.to_csv(OUTPUT_THRESHOLD_TOP20,   index=False)
        logger.info("Written: %s", OUTPUT_THRESHOLD_TOP20)
        output_files.append(str(OUTPUT_THRESHOLD_TOP20))

    except OSError as exc:
        logger.critical("Failed to write output CSV: %s", exc)
        sys.exit(1)

    # 5. Console report
    print_console_report(metrics, best_thresh_df, cat_summary_df, output_files)

    logger.info("Phase 5B Analysis Script completed successfully.")


if __name__ == "__main__":
    main()