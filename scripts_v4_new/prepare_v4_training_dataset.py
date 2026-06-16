#!/usr/bin/env python3
"""
NeuroVision Omega - Phase 4 Training Dataset Preparation
================================================================================
Cleans the dataset for training by:
1. Replacing NaN values with 0
2. Replacing Inf values with 0
3. Converting float64 to float32 for memory efficiency
4. Validating data types
5. Saving optimized clean dataset
================================================================================
"""

import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
PROJECT_ROOT = Path(r"E:\Project\neurovision_ai")
INPUT_PATH = PROJECT_ROOT / "real_feature_dataset_v4.parquet"
OUTPUT_PATH = PROJECT_ROOT / "real_feature_dataset_v4_clean.parquet"
CLEANING_LOG = PROJECT_ROOT / "dataset_cleaning_log_v4.txt"

# Expected columns
EXPECTED_FEATURE_COUNT = 96
EXPECTED_TOTAL_COLUMNS = 99

# Base feature names (for validation)
BASE_FEATURES = [
    "mean", "std", "variance", "rms", "max", "min", "ptp",
    "line_length", "zero_crossings", "iqr", "mad",
    "sample_entropy", "perm_entropy", "spectral_entropy",
    "higuchi_fd", "petrosian_fd",
    "wavelet_energy_0", "wavelet_energy_1", "wavelet_energy_2",
    "wavelet_energy_3", "wavelet_energy_4", "wavelet_energy_5",
    "delta_power", "theta_power", "alpha_power", "beta_power", "gamma_power",
    "delta_relative", "theta_relative", "alpha_relative", "beta_relative", "gamma_relative"
]
AGGREGATIONS = ["mean", "std", "max"]
FEATURE_COLUMNS = [f"{f}_{a}" for f in BASE_FEATURES for a in AGGREGATIONS]
METADATA_COLUMNS = ['label', 'patient', 'edf']


def load_dataset() -> pd.DataFrame:
    """Load the raw dataset"""
    logger.info(f"Loading dataset from {INPUT_PATH}")
    
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {INPUT_PATH}")
    
    df = pd.read_parquet(INPUT_PATH)
    logger.info(f"Loaded {len(df):,} rows with {len(df.columns)} columns")
    
    return df


def validate_columns(df: pd.DataFrame) -> Tuple[bool, List[str], List[str]]:
    """Validate that all expected columns are present"""
    actual_columns = set(df.columns)
    expected_columns = set(FEATURE_COLUMNS + METADATA_COLUMNS)
    
    missing_columns = expected_columns - actual_columns
    extra_columns = actual_columns - expected_columns
    
    if missing_columns:
        logger.warning(f"Missing {len(missing_columns)} columns")
        for col in list(missing_columns)[:10]:
            logger.warning(f"  Missing: {col}")
    
    if extra_columns:
        logger.warning(f"Extra {len(extra_columns)} columns: {list(extra_columns)[:10]}")
    
    return len(missing_columns) == 0, list(missing_columns), list(extra_columns)


def clean_nan_inf(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """Replace NaN and Inf values"""
    cleaning_stats = {
        'initial_nan_count': 0,
        'initial_inf_count': 0,
        'nan_replaced': 0,
        'inf_replaced': 0,
        'columns_with_nan': [],
        'columns_with_inf': []
    }
    
    # Identify numeric columns (excluding label which is integer)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    numeric_cols = [c for c in numeric_cols if c != 'label']
    
    # Count initial issues
    for col in numeric_cols:
        nan_count = df[col].isna().sum()
        if nan_count > 0:
            cleaning_stats['initial_nan_count'] += nan_count
            cleaning_stats['columns_with_nan'].append(col)
        
        inf_count = np.isinf(df[col]).sum()
        if inf_count > 0:
            cleaning_stats['initial_inf_count'] += inf_count
            cleaning_stats['columns_with_inf'].append(col)
    
    logger.info(f"Initial issues: {cleaning_stats['initial_nan_count']:,} NaN, {cleaning_stats['initial_inf_count']:,} Inf")
    
    # Replace NaN and Inf
    for col in numeric_cols:
        nan_mask = df[col].isna()
        if nan_mask.any():
            df.loc[nan_mask, col] = 0.0
            cleaning_stats['nan_replaced'] += nan_mask.sum()
        
        inf_mask = np.isinf(df[col])
        if inf_mask.any():
            df.loc[inf_mask, col] = 0.0
            cleaning_stats['inf_replaced'] += inf_mask.sum()
    
    logger.info(f"Replaced {cleaning_stats['nan_replaced']:,} NaN values")
    logger.info(f"Replaced {cleaning_stats['inf_replaced']:,} Inf values")
    
    return df, cleaning_stats


def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Optimize data types for memory efficiency"""
    logger.info("Optimizing data types...")
    
    initial_memory = df.memory_usage(deep=True).sum() / (1024 * 1024)
    logger.info(f"Initial memory: {initial_memory:.2f} MB")
    
    # Convert feature columns to float32
    feature_cols = [c for c in df.columns if c not in METADATA_COLUMNS]
    for col in feature_cols:
        if col in df.columns:
            df[col] = df[col].astype(np.float32)
    
    # Convert label to int8 (saves memory)
    df['label'] = df['label'].astype(np.int8)
    
    # Convert patient to category (categorical string)
    df['patient'] = df['patient'].astype('category')
    
    # Convert edf to string (no compression for uniqueness)
    df['edf'] = df['edf'].astype('string')
    
    final_memory = df.memory_usage(deep=True).sum() / (1024 * 1024)
    logger.info(f"Final memory: {final_memory:.2f} MB")
    logger.info(f"Memory reduction: {initial_memory - final_memory:.2f} MB ({100 * (1 - final_memory/initial_memory):.1f}%)")
    
    return df


def validate_clean_dataset(df: pd.DataFrame) -> Tuple[bool, Dict]:
    """Validate the cleaned dataset"""
    validation = {
        'has_nan': False,
        'has_inf': False,
        'dtypes_correct': True,
        'row_count': len(df),
        'column_count': len(df.columns),
        'feature_count': len([c for c in df.columns if c not in METADATA_COLUMNS]),
        'label_distribution': df['label'].value_counts().to_dict(),
        'issues': []
    }
    
    # Check for remaining NaN/Inf
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].isna().any():
            validation['has_nan'] = True
            validation['issues'].append(f"NaN still present in {col}")
        if np.isinf(df[col]).any():
            validation['has_inf'] = True
            validation['issues'].append(f"Inf still present in {col}")
    
    # Check dtypes
    expected_dtypes = {
        'label': 'int8',
        'patient': 'category',
        'edf': 'string'
    }
    for col, expected in expected_dtypes.items():
        if col in df.columns:
            actual = str(df[col].dtype)
            if expected not in actual:
                validation['dtypes_correct'] = False
                validation['issues'].append(f"{col} dtype is {actual}, expected {expected}")
    
    # Check feature columns are float32
    feature_cols = [c for c in df.columns if c not in METADATA_COLUMNS]
    for col in feature_cols:
        if df[col].dtype != 'float32':
            validation['dtypes_correct'] = False
            validation['issues'].append(f"{col} dtype is {df[col].dtype}, expected float32")
            break
    
    validation['clean'] = not (validation['has_nan'] or validation['has_inf']) and validation['dtypes_correct']
    
    return validation['clean'], validation


def save_cleaning_log(cleaning_stats: Dict, validation: Dict, output_path: Path):
    """Save detailed cleaning log"""
    with open(output_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("NEUROVISION OMEGA - DATASET CLEANING LOG\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("🔧 CLEANING OPERATIONS\n")
        f.write(f"   Initial NaN count: {cleaning_stats['initial_nan_count']:,}\n")
        f.write(f"   Initial Inf count: {cleaning_stats['initial_inf_count']:,}\n")
        f.write(f"   NaN values replaced: {cleaning_stats['nan_replaced']:,}\n")
        f.write(f"   Inf values replaced: {cleaning_stats['inf_replaced']:,}\n")
        
        if cleaning_stats['columns_with_nan']:
            f.write(f"\n   Columns with NaN (before cleaning): {len(cleaning_stats['columns_with_nan'])}\n")
            for col in cleaning_stats['columns_with_nan'][:20]:
                f.write(f"     - {col}\n")
        
        if cleaning_stats['columns_with_inf']:
            f.write(f"\n   Columns with Inf (before cleaning): {len(cleaning_stats['columns_with_inf'])}\n")
            for col in cleaning_stats['columns_with_inf'][:20]:
                f.write(f"     - {col}\n")
        
        f.write("\n✅ VALIDATION RESULTS\n")
        f.write(f"   Dataset is clean: {validation['clean']}\n")
        f.write(f"   Has NaN: {validation['has_nan']}\n")
        f.write(f"   Has Inf: {validation['has_inf']}\n")
        f.write(f"   Dtypes correct: {validation['dtypes_correct']}\n")
        
        if validation['issues']:
            f.write(f"\n   Issues found:\n")
            for issue in validation['issues'][:20]:
                f.write(f"     - {issue}\n")
        
        f.write("\n📊 FINAL DATASET STATISTICS\n")
        f.write(f"   Rows: {validation['row_count']:,}\n")
        f.write(f"   Columns: {validation['column_count']}\n")
        f.write(f"   Features: {validation['feature_count']}\n")
        f.write(f"   Label distribution: {validation['label_distribution']}\n")
        
        f.write("\n" + "=" * 80 + "\n")


def main():
    """Main preparation execution"""
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("NEUROVISION OMEGA - PHASE 4 TRAINING DATASET PREPARATION")
    logger.info(f"Input: {INPUT_PATH}")
    logger.info(f"Output: {OUTPUT_PATH}")
    logger.info("=" * 80)
    
    # Step 1: Load dataset
    logger.info("\n📂 Step 1: Loading dataset...")
    df = load_dataset()
    
    # Step 2: Validate columns
    logger.info("\n📐 Step 2: Validating columns...")
    columns_valid, missing_cols, extra_cols = validate_columns(df)
    if not columns_valid:
        logger.warning(f"Missing {len(missing_cols)} expected columns")
        # Add missing columns with zeros
        for col in missing_cols:
            if col in FEATURE_COLUMNS:
                df[col] = 0.0
                logger.info(f"  Added missing column: {col}")
    
    # Step 3: Clean NaN and Inf
    logger.info("\n🧹 Step 3: Cleaning NaN and Inf values...")
    df, cleaning_stats = clean_nan_inf(df)
    
    # Step 4: Optimize dtypes
    logger.info("\n⚡ Step 4: Optimizing data types...")
    df = optimize_dtypes(df)
    
    # Step 5: Validate cleaned dataset
    logger.info("\n✅ Step 5: Validating cleaned dataset...")
    is_clean, validation = validate_clean_dataset(df)
    
    # Step 6: Save cleaned dataset
    logger.info(f"\n💾 Step 6: Saving cleaned dataset to {OUTPUT_PATH}...")
    df.to_parquet(OUTPUT_PATH, index=False)
    
    # Step 7: Save cleaning log
    logger.info("\n📝 Step 7: Saving cleaning log...")
    save_cleaning_log(cleaning_stats, validation, CLEANING_LOG)
    
    # Verify saved file
    verification_df = pd.read_parquet(OUTPUT_PATH)
    assert len(verification_df) == len(df), "Verification failed: row count mismatch"
    
    elapsed = time.time() - start_time
    file_size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    
    logger.info("\n" + "=" * 80)
    logger.info("PREPARATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Output file: {OUTPUT_PATH}")
    logger.info(f"File size: {file_size_mb:.2f} MB")
    logger.info(f"Rows: {len(df):,}")
    logger.info(f"Columns: {len(df.columns)}")
    logger.info(f"Memory optimized: {validation['feature_count']} features at float32")
    logger.info(f"Cleaning log: {CLEANING_LOG}")
    logger.info(f"Execution time: {elapsed:.2f} seconds")
    
    if is_clean:
        logger.info("\n✅ Dataset is clean and ready for training!")
    else:
        logger.warning("\n⚠️ Dataset has issues - check cleaning log for details")
    
    logger.info("=" * 80)


if __name__ == "__main__":
    main()