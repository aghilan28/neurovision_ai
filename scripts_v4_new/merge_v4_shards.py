#!/usr/bin/env python3
"""
NeuroVision Omega - Phase 4 Shard Merger
================================================================================
Merges all individual shard files into final parquet dataset.
Includes comprehensive validation and audit report.
================================================================================
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Set
import pandas as pd
import numpy as np
import pyarrow.parquet as pq

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
PROJECT_ROOT = Path(r"E:\Project\neurovision_ai")
SHARD_DIR = PROJECT_ROOT / "real_feature_dataset_v4_shards"
OUTPUT_PATH = PROJECT_ROOT / "real_feature_dataset_v4.parquet"
AUDIT_PATH = PROJECT_ROOT / "merge_audit_v4.json"
LOG_PATH = PROJECT_ROOT / "merge_v4.log"

# Expected values
EXPECTED_PATIENTS = 24
EXPECTED_SHARDS = 686
EXPECTED_FEATURE_COUNT = 96
EXPECTED_TOTAL_COLUMNS = 99

# Known patient list
PATIENT_LIST = [f"chb{str(i).zfill(2)}" for i in range(1, 25)]

# Feature columns list (generated)
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
EXPECTED_FEATURE_COLUMNS = [f"{f}_{a}" for f in BASE_FEATURES for a in AGGREGATIONS]
REQUIRED_COLUMNS = EXPECTED_FEATURE_COLUMNS + ['label', 'patient', 'edf']


def get_shard_info() -> Dict[str, Dict]:
    """Scan shard directory and collect metadata"""
    shard_files = sorted(SHARD_DIR.glob("*.parquet"))
    
    shard_info = {}
    for shard_path in shard_files:
        try:
            # Parse patient from filename (format: chbXX_YY.parquet)
            name_parts = shard_path.stem.split('_')
            if len(name_parts) >= 1:
                patient = name_parts[0]
            else:
                patient = "unknown"
            
            # Get basic info without loading full dataframe
            parquet_file = pq.ParquetFile(shard_path)
            row_count = parquet_file.metadata.num_rows
            num_columns = parquet_file.metadata.num_columns
            
            shard_info[shard_path.name] = {
                'path': str(shard_path),
                'patient': patient,
                'rows': row_count,
                'columns': num_columns,
                'size_mb': shard_path.stat().st_size / (1024 * 1024)
            }
        except Exception as e:
            logger.error(f"Failed to read shard {shard_path.name}: {e}")
            shard_info[shard_path.name] = {
                'path': str(shard_path),
                'patient': 'error',
                'rows': 0,
                'columns': 0,
                'size_mb': 0,
                'error': str(e)
            }
    
    return shard_info


def validate_column_consistency(shard_paths: List[Path]) -> Tuple[bool, List[str], Set[str]]:
    """Validate all shards have same columns"""
    all_columns = None
    inconsistencies = []
    
    for shard_path in shard_paths:
        try:
            # Read just the schema
            parquet_file = pq.ParquetFile(shard_path)
            columns = set(parquet_file.schema.names)
            
            if all_columns is None:
                all_columns = columns
            elif columns != all_columns:
                missing = all_columns - columns
                extra = columns - all_columns
                inconsistencies.append(f"{shard_path.name}: Missing {missing}, Extra {extra}")
        except Exception as e:
            inconsistencies.append(f"{shard_path.name}: {str(e)}")
    
    return len(inconsistencies) == 0, inconsistencies, all_columns or set()


def merge_all_shards() -> Tuple[pd.DataFrame, Dict]:
    """Merge all shards into single DataFrame"""
    shard_paths = sorted(SHARD_DIR.glob("*.parquet"))
    logger.info(f"Found {len(shard_paths)} shard files")
    
    # Validate column consistency first
    is_consistent, inconsistencies, all_cols = validate_column_consistency(shard_paths)
    if not is_consistent:
        logger.error("Column inconsistency detected!")
        for inc in inconsistencies[:10]:
            logger.error(f"  {inc}")
        raise ValueError("Shards have inconsistent schemas")
    
    logger.info(f"All shards have consistent schema with {len(all_cols)} columns")
    
    # Read all shards into list of dataframes
    dfs = []
    total_rows = 0
    
    for shard_path in shard_paths:
        try:
            df = pd.read_parquet(shard_path)
            rows = len(df)
            total_rows += rows
            dfs.append(df)
            logger.info(f"  Loaded {shard_path.name}: {rows:,} rows")
        except Exception as e:
            logger.error(f"Failed to load {shard_path.name}: {e}")
            continue
    
    # Concatenate all dataframes
    logger.info(f"Concatenating {len(dfs)} dataframes...")
    final_df = pd.concat(dfs, ignore_index=True)
    
    logger.info(f"Final dataset: {len(final_df):,} rows, {len(final_df.columns)} columns")
    
    return final_df, {
        'shard_count': len(shard_paths),
        'rows_per_shard': {p.name: len(pd.read_parquet(p)) for p in shard_paths[:10]},  # Sample
        'total_rows': len(final_df)
    }


def generate_audit_report(df: pd.DataFrame, shard_info: Dict, merge_stats: Dict) -> Dict:
    """Generate comprehensive audit report"""
    
    # Patient analysis
    patients_found = sorted(df['patient'].unique())
    patient_counts = df['patient'].value_counts().to_dict()
    
    # EDF analysis
    edf_count = df['edf'].nunique()
    edf_counts = df['edf'].value_counts().head(20).to_dict()
    
    # Label distribution
    label_counts = df['label'].value_counts().to_dict()
    seizure_ratio = label_counts.get(1, 0) / max(1, label_counts.get(0, 0))
    
    # Check for nulls
    null_counts = df.isnull().sum()
    null_columns = null_counts[null_counts > 0].to_dict()
    
    # Check for infs
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    inf_counts = {}
    for col in numeric_cols:
        inf_count = np.isinf(df[col]).sum()
        if inf_count > 0:
            inf_counts[col] = int(inf_count)
    
    # Check for data types
    dtypes = df.dtypes.astype(str).to_dict()
    
    # Memory usage
    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    
    # Feature completeness
    feature_cols = [c for c in df.columns if c not in ['label', 'patient', 'edf']]
    missing_features = set(EXPECTED_FEATURE_COLUMNS) - set(feature_cols)
    extra_features = set(feature_cols) - set(EXPECTED_FEATURE_COLUMNS)
    
    audit = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'expected_columns': EXPECTED_TOTAL_COLUMNS,
            'feature_count': len(feature_cols),
            'expected_feature_count': EXPECTED_FEATURE_COUNT,
            'memory_usage_mb': round(memory_mb, 2),
            'shard_count': len(shard_info),
            'expected_shard_count': EXPECTED_SHARDS
        },
        'patient_analysis': {
            'patients_found': patients_found,
            'patient_count': len(patients_found),
            'expected_patient_count': EXPECTED_PATIENTS,
            'missing_patients': [p for p in PATIENT_LIST if p not in patients_found],
            'rows_per_patient': patient_counts
        },
        'edf_analysis': {
            'unique_edf_files': edf_count,
            'expected_edf_count': EXPECTED_SHARDS,
            'rows_per_edf_sample': {k: v for k, v in list(edf_counts.items())[:20]}
        },
        'label_analysis': {
            'background_windows': label_counts.get(0, 0),
            'seizure_windows': label_counts.get(1, 0),
            'seizure_ratio': round(seizure_ratio, 6),
            'label_distribution': label_counts
        },
        'data_quality': {
            'null_columns': null_columns,
            'inf_columns': inf_counts,
            'has_nulls': len(null_columns) > 0,
            'has_infs': len(inf_counts) > 0
        },
        'schema_validation': {
            'missing_feature_columns': list(missing_features),
            'extra_columns': list(extra_features),
            'columns_match': len(missing_features) == 0 and len(extra_features) == 0
        },
        'dtypes': dtypes,
        'shard_details': shard_info
    }
    
    return audit


def save_audit_report(audit: Dict, output_path: Path):
    """Save audit report as JSON"""
    # Convert non-serializable items
    def convert(obj):
        if isinstance(obj, pd.Int64Dtype):
            return 'Int64'
        if isinstance(obj, pd.Float64Dtype):
            return 'Float64'
        if isinstance(obj, pd.StringDtype):
            return 'string'
        return str(obj)
    
    with open(output_path, 'w') as f:
        json.dump(audit, f, indent=2, default=convert)
    
    logger.info(f"Audit report saved to {output_path}")


def print_audit_summary(audit: Dict):
    """Print human-readable audit summary"""
    print("\n" + "=" * 80)
    print("MERGE AUDIT SUMMARY")
    print("=" * 80)
    
    summary = audit['summary']
    print(f"\n📊 DATASET OVERVIEW")
    print(f"   Rows: {summary['total_rows']:,}")
    print(f"   Columns: {summary['total_columns']}")
    print(f"   Feature columns: {summary['feature_count']}")
    print(f"   Memory: {summary['memory_usage_mb']:.2f} MB")
    print(f"   Shards merged: {summary['shard_count']}")
    
    patient = audit['patient_analysis']
    print(f"\n👤 PATIENT ANALYSIS")
    print(f"   Patients found: {patient['patient_count']} / {patient['expected_patient_count']}")
    if patient['missing_patients']:
        print(f"   ⚠️ MISSING: {patient['missing_patients']}")
    else:
        print(f"   ✓ All patients present")
    
    label = audit['label_analysis']
    print(f"\n🏷️ LABEL DISTRIBUTION")
    print(f"   Background: {label['background_windows']:,}")
    print(f"   Seizure: {label['seizure_windows']:,}")
    print(f"   Seizure Ratio: {label['seizure_ratio']:.4f}")
    
    quality = audit['data_quality']
    print(f"\n✅ DATA QUALITY")
    if quality['has_nulls']:
        print(f"   ⚠️ Null columns: {len(quality['null_columns'])}")
    else:
        print(f"   ✓ No null values")
    if quality['has_infs']:
        print(f"   ⚠️ Inf columns: {len(quality['inf_columns'])}")
    else:
        print(f"   ✓ No infinite values")
    
    schema = audit['schema_validation']
    print(f"\n📐 SCHEMA VALIDATION")
    if schema['columns_match']:
        print(f"   ✓ All 96 feature columns match expected")
    else:
        print(f"   ⚠️ Missing features: {len(schema['missing_feature_columns'])}")
        print(f"   ⚠️ Extra columns: {len(schema['extra_columns'])}")
    
    print("\n" + "=" * 80)


def main():
    """Main merge execution"""
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("NEUROVISION OMEGA - PHASE 4 SHARD MERGER")
    logger.info(f"Shard directory: {SHARD_DIR}")
    logger.info(f"Output: {OUTPUT_PATH}")
    logger.info("=" * 80)
    
    # Step 1: Get shard information
    logger.info("\n📁 Scanning shard directory...")
    shard_info = get_shard_info()
    valid_shards = {name: info for name, info in shard_info.items() if info.get('rows', 0) > 0}
    
    logger.info(f"Found {len(valid_shards)} valid shards")
    total_rows_in_shards = sum(info['rows'] for info in valid_shards.values())
    logger.info(f"Total rows across shards: {total_rows_in_shards:,}")
    
    if len(valid_shards) < EXPECTED_SHARDS:
        logger.warning(f"Expected {EXPECTED_SHARDS} shards, found {len(valid_shards)}")
    
    # Step 2: Merge all shards
    logger.info("\n🔄 Merging shards...")
    final_df, merge_stats = merge_all_shards()
    
    # Step 3: Generate audit
    logger.info("\n🔍 Generating audit report...")
    audit = generate_audit_report(final_df, shard_info, merge_stats)
    
    # Step 4: Print summary
    print_audit_summary(audit)
    
    # Step 5: Save audit JSON
    save_audit_report(audit, AUDIT_PATH)
    
    # Step 6: Save final dataset
    logger.info(f"\n💾 Saving final dataset to {OUTPUT_PATH}...")
    final_df.to_parquet(OUTPUT_PATH, index=False)
    
    # Step 7: Verify saved file
    verification_df = pd.read_parquet(OUTPUT_PATH)
    assert len(verification_df) == len(final_df), "Verification failed: row count mismatch"
    
    file_size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    
    elapsed = time.time() - start_time
    logger.info("\n" + "=" * 80)
    logger.info("MERGE COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Output file: {OUTPUT_PATH}")
    logger.info(f"File size: {file_size_mb:.2f} MB")
    logger.info(f"Total rows: {len(final_df):,}")
    logger.info(f"Total columns: {len(final_df.columns)}")
    logger.info(f"Audit report: {AUDIT_PATH}")
    logger.info(f"Execution time: {elapsed:.2f} seconds")
    logger.info("=" * 80)
    
    # Final validation checks
    assert len(final_df) > 0, "Dataset is empty"
    assert 'label' in final_df.columns, "Missing label column"
    assert 'patient' in final_df.columns, "Missing patient column"
    assert 'edf' in final_df.columns, "Missing edf column"
    
    logger.info("\n✅ All validation checks passed!")
    logger.info("Dataset ready for training.")


if __name__ == "__main__":
    main()