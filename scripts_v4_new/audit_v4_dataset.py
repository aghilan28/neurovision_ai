#!/usr/bin/env python3
"""
NeuroVision Omega - Phase 4 Dataset Audit
================================================================================
Comprehensive validation of the final parquet dataset.
Checks shape, memory, patient coverage, label distribution, and data quality.
================================================================================
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
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
DATASET_PATH = PROJECT_ROOT / "real_feature_dataset_v4.parquet"
AUDIT_REPORT_PATH = PROJECT_ROOT / "dataset_audit_v4.json"
SUMMARY_PATH = PROJECT_ROOT / "dataset_summary_v4.txt"

# Expected values
EXPECTED_PATIENTS = 24
EXPECTED_EDF_COUNT = 686
EXPECTED_FEATURE_COUNT = 96
EXPECTED_TOTAL_COLUMNS = 99

# Feature columns for validation
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
EXPECTED_FEATURE_COLUMNS = set([f"{f}_{a}" for f in BASE_FEATURES for a in AGGREGATIONS])


def load_dataset() -> pd.DataFrame:
    """Load the parquet dataset"""
    logger.info(f"Loading dataset from {DATASET_PATH}")
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")
    
    df = pd.read_parquet(DATASET_PATH)
    logger.info(f"Loaded {len(df):,} rows with {len(df.columns)} columns")
    return df


def analyze_shape(df: pd.DataFrame) -> Dict:
    """Analyze dataset shape"""
    feature_cols = [c for c in df.columns if c not in ['label', 'patient', 'edf']]
    
    return {
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'feature_columns': len(feature_cols),
        'metadata_columns': len(['label', 'patient', 'edf']),
        'expected_feature_count': EXPECTED_FEATURE_COUNT,
        'expected_total_columns': EXPECTED_TOTAL_COLUMNS,
        'feature_count_match': len(feature_cols) == EXPECTED_FEATURE_COUNT,
        'column_count_match': len(df.columns) == EXPECTED_TOTAL_COLUMNS
    }


def analyze_patients(df: pd.DataFrame) -> Dict:
    """Analyze patient distribution"""
    patients = sorted(df['patient'].unique())
    patient_counts = df['patient'].value_counts().to_dict()
    
    # Load expected patients
    expected_patients = [f"chb{str(i).zfill(2)}" for i in range(1, 25)]
    missing_patients = [p for p in expected_patients if p not in patients]
    extra_patients = [p for p in patients if p not in expected_patients]
    
    # Per-patient statistics
    patient_stats = {}
    for patient in patients:
        patient_df = df[df['patient'] == patient]
        patient_stats[patient] = {
            'rows': len(patient_df),
            'edf_files': patient_df['edf'].nunique(),
            'seizure_windows': len(patient_df[patient_df['label'] == 1]),
            'background_windows': len(patient_df[patient_df['label'] == 0]),
            'seizure_ratio': len(patient_df[patient_df['label'] == 1]) / max(1, len(patient_df))
        }
    
    return {
        'patients_found': patients,
        'patient_count': len(patients),
        'expected_patient_count': EXPECTED_PATIENTS,
        'missing_patients': missing_patients,
        'extra_patients': extra_patients,
        'rows_per_patient': patient_counts,
        'patient_statistics': patient_stats
    }


def analyze_edf_files(df: pd.DataFrame) -> Dict:
    """Analyze EDF file distribution"""
    edf_files = sorted(df['edf'].unique())
    edf_counts = df['edf'].value_counts().to_dict()
    
    # Group by patient
    edf_by_patient = {}
    for patient in df['patient'].unique():
        patient_edfs = df[df['patient'] == patient]['edf'].unique()
        edf_by_patient[patient] = sorted(patient_edfs)
    
    return {
        'unique_edf_files': len(edf_files),
        'expected_edf_count': EXPECTED_EDF_COUNT,
        'edf_count_match': len(edf_files) == EXPECTED_EDF_COUNT,
        'rows_per_edf_sample': {k: v for k, v in list(edf_counts.items())[:50]},
        'edf_files_per_patient': {p: len(edfs) for p, edfs in edf_by_patient.items()}
    }


def analyze_labels(df: pd.DataFrame) -> Dict:
    """Analyze label distribution"""
    label_counts = df['label'].value_counts().to_dict()
    seizure_rows = label_counts.get(1, 0)
    background_rows = label_counts.get(0, 0)
    
    # Per-patient label distribution
    patient_label_dist = {}
    for patient in df['patient'].unique():
        patient_df = df[df['patient'] == patient]
        patient_label_dist[patient] = {
            'seizure': len(patient_df[patient_df['label'] == 1]),
            'background': len(patient_df[patient_df['label'] == 0]),
            'ratio': len(patient_df[patient_df['label'] == 1]) / max(1, len(patient_df))
        }
    
    return {
        'background_windows': background_rows,
        'seizure_windows': seizure_rows,
        'total_windows': seizure_rows + background_rows,
        'seizure_percentage': 100 * seizure_rows / max(1, seizure_rows + background_rows),
        'seizure_to_background_ratio': seizure_rows / max(1, background_rows),
        'per_patient_distribution': patient_label_dist
    }


def analyze_data_quality(df: pd.DataFrame) -> Dict:
    """Analyze data quality issues"""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    # Null analysis
    null_counts = df.isnull().sum()
    null_columns = null_counts[null_counts > 0]
    
    # Inf analysis
    inf_counts = {}
    for col in numeric_cols:
        inf_count = np.isinf(df[col]).sum()
        if inf_count > 0:
            inf_counts[col] = int(inf_count)
    
    # Descriptive statistics for key features
    feature_cols = [c for c in numeric_cols if c not in ['label']]
    sample_stats = {}
    for col in feature_cols[:20]:  # Sample of features
        sample_stats[col] = {
            'mean': float(df[col].mean()),
            'std': float(df[col].std()),
            'min': float(df[col].min()),
            'max': float(df[col].max()),
            'q1': float(df[col].quantile(0.25)),
            'median': float(df[col].median()),
            'q3': float(df[col].quantile(0.75))
        }
    
    return {
        'null_count_total': int(null_counts.sum()),
        'null_columns': null_columns.to_dict(),
        'null_columns_count': len(null_columns),
        'inf_columns': inf_counts,
        'inf_columns_count': len(inf_counts),
        'has_nulls': len(null_columns) > 0,
        'has_infs': len(inf_counts) > 0,
        'sample_feature_statistics': sample_stats
    }


def analyze_schema(df: pd.DataFrame) -> Dict:
    """Analyze column schema"""
    actual_columns = set(df.columns)
    missing_features = EXPECTED_FEATURE_COLUMNS - actual_columns
    extra_columns = actual_columns - EXPECTED_FEATURE_COLUMNS - {'label', 'patient', 'edf'}
    
    # Data types
    dtypes = df.dtypes.astype(str).to_dict()
    
    return {
        'actual_columns': list(actual_columns),
        'missing_feature_columns': list(missing_features),
        'extra_columns': list(extra_columns),
        'schema_complete': len(missing_features) == 0,
        'no_extra_columns': len(extra_columns) == 0,
        'dtypes': dtypes
    }


def analyze_duplicates(df: pd.DataFrame) -> Dict:
    """Analyze duplicate rows"""
    # Check for exact duplicates across all columns
    exact_duplicates = df.duplicated().sum()
    
    # Check for duplicate (patient, edf) combinations that might indicate issues
    patient_edf_duplicates = df.duplicated(subset=['patient', 'edf']).sum()
    
    # Check for duplicate feature vectors (excluding label, patient, edf)
    feature_cols = [c for c in df.columns if c not in ['label', 'patient', 'edf']]
    feature_duplicates = df[feature_cols].duplicated().sum()
    
    return {
        'exact_duplicate_rows': int(exact_duplicates),
        'patient_edf_duplicate_entries': int(patient_edf_duplicates),
        'feature_vector_duplicates': int(feature_duplicates),
        'has_duplicates': exact_duplicates > 0
    }


def analyze_memory(df: pd.DataFrame) -> Dict:
    """Analyze memory usage"""
    memory_bytes = df.memory_usage(deep=True)
    total_memory_mb = memory_bytes.sum() / (1024 * 1024)
    
    # Per-column memory
    column_memory = {col: bytes_val / (1024 * 1024) for col, bytes_val in memory_bytes.items()}
    
    # Dtype distribution
    dtype_counts = df.dtypes.value_counts().to_dict()
    
    return {
        'total_memory_mb': round(total_memory_mb, 2),
        'memory_per_column_mb': {k: round(v, 2) for k, v in column_memory.items()},
        'dtype_distribution': {str(k): v for k, v in dtype_counts.items()}
    }


def generate_summary_report(audit: Dict, output_path: Path):
    """Generate human-readable summary report"""
    with open(output_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("NEUROVISION OMEGA - PHASE 4 DATASET AUDIT SUMMARY\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        # Shape
        shape = audit['shape']
        f.write("📊 DATASET SHAPE\n")
        f.write(f"   Rows: {shape['total_rows']:,}\n")
        f.write(f"   Columns: {shape['total_columns']}\n")
        f.write(f"   Feature columns: {shape['feature_columns']} / {EXPECTED_FEATURE_COUNT}\n")
        f.write(f"   ✓ Feature count match: {shape['feature_count_match']}\n\n")
        
        # Patients
        patients = audit['patients']
        f.write("👤 PATIENT COVERAGE\n")
        f.write(f"   Patients found: {patients['patient_count']} / {EXPECTED_PATIENTS}\n")
        if patients['missing_patients']:
            f.write(f"   ⚠️ MISSING: {patients['missing_patients']}\n")
        else:
            f.write(f"   ✓ All 24 patients present\n")
        f.write("\n")
        
        # EDF files
        edf = audit['edf_files']
        f.write("📁 EDF FILE COVERAGE\n")
        f.write(f"   EDF files: {edf['unique_edf_files']} / {EXPECTED_EDF_COUNT}\n")
        f.write(f"   ✓ Count match: {edf['edf_count_match']}\n\n")
        
        # Labels
        labels = audit['labels']
        f.write("🏷️ LABEL DISTRIBUTION\n")
        f.write(f"   Seizure windows: {labels['seizure_windows']:,} ({labels['seizure_percentage']:.2f}%)\n")
        f.write(f"   Background windows: {labels['background_windows']:,}\n")
        f.write(f"   Seizure/Background ratio: {labels['seizure_to_background_ratio']:.4f}\n\n")
        
        # Data quality
        quality = audit['data_quality']
        f.write("✅ DATA QUALITY\n")
        f.write(f"   Null values: {quality['null_count_total']:,}\n")
        f.write(f"   Columns with nulls: {quality['null_columns_count']}\n")
        f.write(f"   Columns with infinities: {quality['inf_columns_count']}\n")
        if quality['null_columns']:
            f.write(f"   Null columns: {list(quality['null_columns'].keys())[:10]}\n")
        f.write("\n")
        
        # Schema
        schema = audit['schema']
        f.write("📐 SCHEMA VALIDATION\n")
        f.write(f"   Schema complete: {schema['schema_complete']}\n")
        if schema['missing_feature_columns']:
            f.write(f"   Missing features: {len(schema['missing_feature_columns'])}\n")
        if schema['extra_columns']:
            f.write(f"   Extra columns: {schema['extra_columns']}\n")
        f.write("\n")
        
        # Duplicates
        duplicates = audit['duplicates']
        f.write("🔄 DUPLICATE ANALYSIS\n")
        f.write(f"   Exact duplicate rows: {duplicates['exact_duplicate_rows']:,}\n")
        f.write(f"   Feature vector duplicates: {duplicates['feature_vector_duplicates']:,}\n\n")
        
        # Memory
        memory = audit['memory']
        f.write("💾 MEMORY USAGE\n")
        f.write(f"   Total memory: {memory['total_memory_mb']:.2f} MB\n")
        f.write(f"   Dtype distribution: {memory['dtype_distribution']}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("AUDIT COMPLETE\n")
        f.write("=" * 80 + "\n")
    
    logger.info(f"Summary report saved to {output_path}")


def main():
    """Main audit execution"""
    logger.info("=" * 80)
    logger.info("NEUROVISION OMEGA - PHASE 4 DATASET AUDIT")
    logger.info(f"Dataset: {DATASET_PATH}")
    logger.info("=" * 80)
    
    # Load dataset
    df = load_dataset()
    
    # Run all analyses
    logger.info("\n📊 Analyzing dataset shape...")
    shape_analysis = analyze_shape(df)
    
    logger.info("👤 Analyzing patient distribution...")
    patient_analysis = analyze_patients(df)
    
    logger.info("📁 Analyzing EDF file coverage...")
    edf_analysis = analyze_edf_files(df)
    
    logger.info("🏷️ Analyzing label distribution...")
    label_analysis = analyze_labels(df)
    
    logger.info("✅ Analyzing data quality...")
    quality_analysis = analyze_data_quality(df)
    
    logger.info("📐 Analyzing schema...")
    schema_analysis = analyze_schema(df)
    
    logger.info("🔄 Analyzing duplicates...")
    duplicate_analysis = analyze_duplicates(df)
    
    logger.info("💾 Analyzing memory usage...")
    memory_analysis = analyze_memory(df)
    
    # Compile final audit
    audit = {
        'timestamp': datetime.now().isoformat(),
        'dataset_path': str(DATASET_PATH),
        'shape': shape_analysis,
        'patients': patient_analysis,
        'edf_files': edf_analysis,
        'labels': label_analysis,
        'data_quality': quality_analysis,
        'schema': schema_analysis,
        'duplicates': duplicate_analysis,
        'memory': memory_analysis
    }
    
    # Save JSON report
    with open(AUDIT_REPORT_PATH, 'w') as f:
        json.dump(audit, f, indent=2, default=str)
    logger.info(f"\nJSON audit report saved to {AUDIT_REPORT_PATH}")
    
    # Generate summary report
    generate_summary_report(audit, SUMMARY_PATH)
    
    # Print summary
    print("\n" + "=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    print(f"\nRows: {shape_analysis['total_rows']:,}")
    print(f"Columns: {shape_analysis['total_columns']} (features: {shape_analysis['feature_columns']})")
    print(f"Patients: {patient_analysis['patient_count']} / {EXPECTED_PATIENTS}")
    print(f"EDF files: {edf_analysis['unique_edf_files']} / {EXPECTED_EDF_COUNT}")
    print(f"Seizure windows: {label_analysis['seizure_windows']:,} ({label_analysis['seizure_percentage']:.2f}%)")
    print(f"Memory: {memory_analysis['total_memory_mb']:.2f} MB")
    
    # Validation result
    print("\n" + "-" * 40)
    all_valid = (
        shape_analysis['feature_count_match'] and
        patient_analysis['patient_count'] == EXPECTED_PATIENTS and
        edf_analysis['edf_count_match'] and
        not quality_analysis['has_nulls'] and
        not quality_analysis['has_infs'] and
        schema_analysis['schema_complete']
    )
    
    if all_valid:
        print("✅ ALL VALIDATION CHECKS PASSED")
        print("   Dataset is ready for training!")
    else:
        print("⚠️ SOME VALIDATION CHECKS FAILED")
        if quality_analysis['has_nulls']:
            print("   - Contains null values (run prepare script to fix)")
        if quality_analysis['has_infs']:
            print("   - Contains infinite values (run prepare script to fix)")
        if not schema_analysis['schema_complete']:
            print("   - Schema incomplete")
    print("=" * 80)


if __name__ == "__main__":
    main()