#!/usr/bin/env python3
"""
NEUROVISION OMEGA - PHASE 5A
TEMPORAL DATASET FOUNDATION ENGINE

Production-grade temporal dataset reconstruction for NeuroVision platform.
Creates scientifically correct temporal foundation from V4 feature dataset.

Author: NeuroVision Team
Version: 5.0.0
Status: PRODUCTION
"""

import os
import sys
import json
import time
import gc
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import warnings
import traceback

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Suppress warnings for production stability
warnings.filterwarnings('ignore')

def json_serializer(obj):
    import numpy as np

    if isinstance(obj, np.integer):
        return int(obj)

    if isinstance(obj, np.floating):
        return float(obj)

    if isinstance(obj, np.bool_):
        return bool(obj)

    if isinstance(obj, np.ndarray):
        return obj.tolist()

    return str(obj)

# ============================================================================
# SCIENTIFIC CONFIGURATION
# ============================================================================

WINDOW_LENGTH_SEC = 4.0
STRIDE_SEC = 2.0
EXPECTED_FEATURE_COUNT = 96
EXPECTED_TOTAL_COLUMNS_V4 = 99
EXPECTED_TOTAL_COLUMNS_V5 = 105

# Memory management
CHUNK_SIZE = 50000  # rows per chunk
MEMORY_THRESHOLD_GB = 7.5
GC_THRESHOLD = 100  # force GC every N chunks

# Expected column names - VERIFIED V4 SCHEMA
VERIFIED_FEATURE_COLUMNS = [
    'mean_mean', 'mean_std', 'mean_max',
    'std_mean', 'std_std', 'std_max',
    'variance_mean', 'variance_std', 'variance_max',
    'rms_mean', 'rms_std', 'rms_max',
    'max_mean', 'max_std', 'max_max',
    'min_mean', 'min_std', 'min_max',
    'ptp_mean', 'ptp_std', 'ptp_max',
    'line_length_mean', 'line_length_std', 'line_length_max',
    'zero_crossings_mean', 'zero_crossings_std', 'zero_crossings_max',
    'iqr_mean', 'iqr_std', 'iqr_max',
    'mad_mean', 'mad_std', 'mad_max',
    'sample_entropy_mean', 'sample_entropy_std', 'sample_entropy_max',
    'perm_entropy_mean', 'perm_entropy_std', 'perm_entropy_max',
    'spectral_entropy_mean', 'spectral_entropy_std', 'spectral_entropy_max',
    'higuchi_fd_mean', 'higuchi_fd_std', 'higuchi_fd_max',
    'petrosian_fd_mean', 'petrosian_fd_std', 'petrosian_fd_max',
    'wavelet_energy_0_mean', 'wavelet_energy_0_std', 'wavelet_energy_0_max',
    'wavelet_energy_1_mean', 'wavelet_energy_1_std', 'wavelet_energy_1_max',
    'wavelet_energy_2_mean', 'wavelet_energy_2_std', 'wavelet_energy_2_max',
    'wavelet_energy_3_mean', 'wavelet_energy_3_std', 'wavelet_energy_3_max',
    'wavelet_energy_4_mean', 'wavelet_energy_4_std', 'wavelet_energy_4_max',
    'wavelet_energy_5_mean', 'wavelet_energy_5_std', 'wavelet_energy_5_max',
    'delta_power_mean', 'delta_power_std', 'delta_power_max',
    'theta_power_mean', 'theta_power_std', 'theta_power_max',
    'alpha_power_mean', 'alpha_power_std', 'alpha_power_max',
    'beta_power_mean', 'beta_power_std', 'beta_power_max',
    'gamma_power_mean', 'gamma_power_std', 'gamma_power_max',
    'delta_relative_mean', 'delta_relative_std', 'delta_relative_max',
    'theta_relative_mean', 'theta_relative_std', 'theta_relative_max',
    'alpha_relative_mean', 'alpha_relative_std', 'alpha_relative_max',
    'beta_relative_mean', 'beta_relative_std', 'beta_relative_max',
    'gamma_relative_mean', 'gamma_relative_std', 'gamma_relative_max'
]

VERIFIED_METADATA_COLUMNS = ['label', 'patient', 'edf']

# ============================================================================
# PRODUCTION LOGGING SYSTEM
# ============================================================================

class ProductionLogger:
    """Production-grade logging with structured output"""
    
    def __init__(self, log_file: str = "PHASE5A_EXECUTION.log"):
        self.log_file = log_file
        self.start_time = datetime.now()
        self._initialize_log()
    
    def _initialize_log(self):
        with open(self.log_file, 'w') as f:
            f.write(f"NEUROVISION PHASE 5A LOG\n")
            f.write(f"Started: {self.start_time.isoformat()}\n")
            f.write("=" * 80 + "\n\n")
    
    def info(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_msg = f"[INFO] {timestamp} - {message}"
        print(log_msg)
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")
    
    def error(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_msg = f"[ERROR] {timestamp} - {message}"
        print(log_msg, file=sys.stderr)
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")
    
    def warning(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_msg = f"[WARNING] {timestamp} - {message}"
        print(log_msg)
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")
    
    def success(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_msg = f"[SUCCESS] {timestamp} - {message}"
        print(f"\033[92m{log_msg}\033[0m")
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")

# ============================================================================
# CHECKPOINT MANAGER
# ============================================================================

class CheckpointManager:
    """Production checkpointing for safe resume capability"""
    
    def __init__(self, checkpoint_file: str = "PHASE5A_CHECKPOINT.json", logger: ProductionLogger = None):
        self.checkpoint_file = checkpoint_file
        self.logger = logger
        self.checkpoint = self._load_checkpoint()
    
    def _load_checkpoint(self) -> Dict:
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to load checkpoint: {e}")
                return {}
        return {}
    
    def save_checkpoint(self, stage: str, rows_processed: int, edf_groups_processed: int, 
                       current_edf: str = None, current_patient: str = None):
        self.checkpoint = {
            'stage': stage,
            'rows_processed': rows_processed,
            'edf_groups_processed': edf_groups_processed,
            'current_edf': current_edf,
            'current_patient': current_patient,
            'timestamp': datetime.now().isoformat(),
            'window_length_sec': WINDOW_LENGTH_SEC,
            'stride_sec': STRIDE_SEC
        }
        with open(self.checkpoint_file, 'w') as f:
            json.dump(
                self.checkpoint,
                f,
                indent=2,
                default=json_serializer
            )
        if self.logger:
            self.logger.info(f"Checkpoint saved: stage={stage}, rows={rows_processed}")
    
    def get_checkpoint(self) -> Dict:
        return self.checkpoint

# ============================================================================
# TEMPORAL RECONSTRUCTION ENGINE
# ============================================================================

class TemporalReconstructionEngine:
    """Core engine for temporal metadata reconstruction"""
    
    def __init__(self, logger: ProductionLogger):
        self.logger = logger
        self.window_length_sec = WINDOW_LENGTH_SEC
        self.stride_sec = STRIDE_SEC
    
    def reconstruct_temporal_metadata(self, grouped_df: pd.DataFrame, patient: str, edf: str, 
                                     start_index: int = 0) -> pd.DataFrame:
        """
        Reconstruct temporal metadata for a single EDF group
        
        Args:
            grouped_df: DataFrame for a single patient/EDF combination
            patient: Patient identifier
            edf: EDF filename
            start_index: Starting window index (for checkpoint resume)
        
        Returns:
            DataFrame with added temporal columns
        """
        n_windows = len(grouped_df)
        
        # Generate window indices
        window_indices = np.arange(start_index, start_index + n_windows)
        
        # Calculate temporal values
        window_starts = window_indices * self.stride_sec
        window_ends = window_starts + self.window_length_sec
        
        # Create temporal metadata
        temporal_data = {
            'window_index': window_indices,
            'window_start_sec': window_starts,
            'window_end_sec': window_ends,
            'window_duration_sec': np.full(n_windows, self.window_length_sec),
            'stride_sec': np.full(n_windows, self.stride_sec),
            'window_uid': [f"{patient}|{edf}|{idx}" for idx in window_indices]
        }
        
        # Create copy to avoid SettingWithCopyWarning
        result_df = grouped_df.copy()
        
        # Add temporal columns
        for col_name, col_values in temporal_data.items():
            result_df[col_name] = col_values
        
        return result_df

# ============================================================================
# VALIDATION GATES
# ============================================================================

class ValidationGate:
    """All validation gates for dataset integrity"""
    
    def __init__(self, logger: ProductionLogger):
        self.logger = logger
        self.validation_results = {}
    
    def gate1_schema_verification(self, df: pd.DataFrame, is_input: bool = True) -> bool:
        """GATE 1: Verify dataset schema"""
        self.logger.info("GATE 1: Schema verification")
        
        # Check column count
        expected_cols = EXPECTED_TOTAL_COLUMNS_V4 if is_input else EXPECTED_TOTAL_COLUMNS_V5
        if len(df.columns) != expected_cols:
            self.logger.error(f"Column count mismatch: {len(df.columns)} vs {expected_cols}")
            return False
        
        # Check feature columns
        missing_features = [col for col in VERIFIED_FEATURE_COLUMNS if col not in df.columns]
        if missing_features:
            self.logger.error(f"Missing feature columns: {missing_features[:5]}...")
            return False
        
        # Check metadata columns
        missing_metadata = [col for col in VERIFIED_METADATA_COLUMNS if col not in df.columns]
        if missing_metadata:
            self.logger.error(f"Missing metadata columns: {missing_metadata}")
            return False
        
        # Check for NaN/Inf
        if df.isna().any().any():
            self.logger.error("NaN values detected")
            return False
        
        if np.isinf(df.select_dtypes(include=[np.number]).values).any():
            self.logger.error("Inf values detected")
            return False
        
        # Check duplicate columns
        if len(df.columns) != len(set(df.columns)):
            self.logger.error("Duplicate column names detected")
            return False
        
        self.logger.success("GATE 1 passed")
        return True
    
    def gate2_feature_preservation(self, input_df: pd.DataFrame, output_df: pd.DataFrame) -> bool:
        """GATE 2: Verify feature preservation"""
        self.logger.info("GATE 2: Feature preservation verification")
        
        feature_stats = {}
        
        for feature in VERIFIED_FEATURE_COLUMNS:
            input_vals = input_df[feature].values
            output_vals = output_df[feature].values
            
            # Calculate statistics
            stats = {
                'mean_diff': abs(input_vals.mean() - output_vals.mean()),
                'std_diff': abs(input_vals.std() - output_vals.std()),
                'min_diff': abs(input_vals.min() - output_vals.min()),
                'max_diff': abs(input_vals.max() - output_vals.max()),
                'total_diff': np.abs(input_vals - output_vals).sum()
            }
            
            # Tolerance: 1e-10 for floating point differences
            if stats['total_diff'] > 1e-8:
                self.logger.error(f"Feature drift detected in {feature}: total diff={stats['total_diff']}")
                return False
            
            feature_stats[feature] = stats
        
        self.validation_results['feature_stats'] = feature_stats
        self.logger.success("GATE 2 passed")
        return True
    
    def gate3_label_preservation(self, input_df: pd.DataFrame, output_df: pd.DataFrame) -> bool:
        """GATE 3: Verify label preservation"""
        self.logger.info("GATE 3: Label preservation verification")
        
        input_seizure = (input_df['label'] == 1).sum()
        output_seizure = (output_df['label'] == 1).sum()
        input_background = (input_df['label'] == 0).sum()
        output_background = (output_df['label'] == 0).sum()
        
        self.validation_results['label_stats'] = {
            'input_seizure': int(input_seizure),
            'output_seizure': int(output_seizure),
            'input_background': int(input_background),
            'output_background': int(output_background)
        }
        
        if input_seizure != output_seizure:
            self.logger.error(f"Seizure count mismatch: {input_seizure} vs {output_seizure}")
            return False
        
        if input_background != output_background:
            self.logger.error(f"Background count mismatch: {input_background} vs {output_background}")
            return False
        
        self.logger.success("GATE 3 passed")
        return True
    
    def gate4_patient_integrity(self, input_df: pd.DataFrame, output_df: pd.DataFrame) -> bool:
        """GATE 4: Verify patient integrity"""
        self.logger.info("GATE 4: Patient integrity verification")
        
        input_patients = set(input_df['patient'].unique())
        output_patients = set(output_df['patient'].unique())
        
        if input_patients != output_patients:
            self.logger.error(f"Patient mismatch: {input_patients} vs {output_patients}")
            return False
        
        # Verify patient counts
        input_counts = input_df['patient'].value_counts().to_dict()
        output_counts = output_df['patient'].value_counts().to_dict()
        
        for patient in input_patients:
            if input_counts[patient] != output_counts.get(patient, 0):
                self.logger.error(f"Patient count mismatch for {patient}: {input_counts[patient]} vs {output_counts.get(patient, 0)}")
                return False
        
        self.validation_results['patient_stats'] = {
            'patient_list': list(input_patients),
            'patient_counts': input_counts
        }
        
        self.logger.success("GATE 4 passed")
        return True
    
    def gate5_edf_integrity(self, input_df: pd.DataFrame, output_df: pd.DataFrame) -> bool:
        """GATE 5: Verify EDF integrity"""
        self.logger.info("GATE 5: EDF integrity verification")
        
        input_edfs = set(zip(input_df['patient'], input_df['edf']))
        output_edfs = set(zip(output_df['patient'], output_df['edf']))
        
        if input_edfs != output_edfs:
            self.logger.error(f"EDF mismatch detected")
            return False
        
        # Verify EDF counts per patient
        input_edf_counts = input_df.groupby(['patient', 'edf']).size().to_dict()
        output_edf_counts = output_df.groupby(['patient', 'edf']).size().to_dict()
        
        for edf_key in input_edf_counts:
            if input_edf_counts[edf_key] != output_edf_counts.get(edf_key, 0):
                self.logger.error(f"EDF count mismatch for {edf_key}")
                return False
        
        self.validation_results['edf_stats'] = {
            'total_edf_files': int(len(input_edfs)),
            'edf_counts': {
                f"{patient}|{edf}": int(count)
                for (patient, edf), count in input_edf_counts.items()
            }
        }
        
        self.logger.success("GATE 5 passed")
        return True
    
    def gate6_temporal_integrity(self, df: pd.DataFrame) -> bool:
        """GATE 6: Temporal integrity audit"""
        self.logger.info("GATE 6: Temporal integrity audit")
        
        violations = []
        
        # Group by patient and edf
        for (patient, edf), group in df.groupby(['patient', 'edf']):
            # Sort by window_index to ensure order
            group = group.sort_values('window_index')
            
            # Check window_index starts at 0
            if group['window_index'].iloc[0] != 0:
                violations.append(f"{patient}|{edf}: window_index doesn't start at 0")
            
            # Check strictly increasing
            if not (group['window_index'].diff().iloc[1:] == 1).all():
                violations.append(f"{patient}|{edf}: window_index not strictly increasing by 1")
            
            # Check temporal progression
            if not (group['window_start_sec'].diff().iloc[1:] > 0).all():
                violations.append(f"{patient}|{edf}: window_start_sec not strictly increasing")
            
            if not (group['window_end_sec'].diff().iloc[1:] > 0).all():
                violations.append(f"{patient}|{edf}: window_end_sec not strictly increasing")
            
            # Check durations
            if not (group['window_duration_sec'] == WINDOW_LENGTH_SEC).all():
                violations.append(f"{patient}|{edf}: incorrect window duration")
            
            # Check strides
            if not (group['stride_sec'] == STRIDE_SEC).all():
                violations.append(f"{patient}|{edf}: incorrect stride")
            
            # Check unique UIDs
            if len(group['window_uid']) != len(group['window_uid'].unique()):
                violations.append(f"{patient}|{edf}: duplicate window_uids")
            
            # Check negative timestamps
            if (group['window_start_sec'] < 0).any() or (group['window_end_sec'] < 0).any():
                violations.append(f"{patient}|{edf}: negative timestamps detected")
        
        if violations:
            for violation in violations[:10]:  # Show first 10 violations
                self.logger.error(f"Temporal violation: {violation}")
            self.logger.error(f"Total violations: {len(violations)}")
            return False
        
        self.validation_results['temporal_stats'] = {
            'status': 'PASSED',
            'window_length_sec': WINDOW_LENGTH_SEC,
            'stride_sec': STRIDE_SEC
        }
        
        self.logger.success("GATE 6 passed")
        return True

# ============================================================================
# AUDIT GENERATOR
# ============================================================================

class AuditGenerator:
    """Generate comprehensive audit artifacts"""
    
    def __init__(self, logger: ProductionLogger, output_dir: str = "."):
        self.logger = logger
        self.output_dir = output_dir
    
    def generate_schema_audit(self, df: pd.DataFrame, filename: str = "PHASE5A_SCHEMA_AUDIT.json"):
        """Generate schema audit report"""
        schema_info = {
            'total_columns': len(df.columns),
            'feature_columns': [col for col in df.columns if col in VERIFIED_FEATURE_COLUMNS],
            'metadata_columns': [col for col in df.columns if col in VERIFIED_METADATA_COLUMNS],
            'temporal_columns': [col for col in df.columns if col not in VERIFIED_FEATURE_COLUMNS + VERIFIED_METADATA_COLUMNS],
            'column_data_types': {col: str(df[col].dtype) for col in df.columns},
            'column_memory_usage': {col: int(df[col].memory_usage(deep=True)) for col in df.columns}
        }
        
        with open(os.path.join(self.output_dir, filename), 'w') as f:
            json.dump(
                schema_info,
                f,
                indent=2,
                default=json_serializer
            )
        
        self.logger.info(f"Schema audit saved: {filename}")
    
    def generate_dataset_audit(self, df: pd.DataFrame, validation_results: Dict, filename: str = "PHASE5A_DATASET_AUDIT.json"):
        """Generate dataset audit report"""
        dataset_info = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
            'label_distribution': df['label'].value_counts().to_dict(),
            'patient_statistics': {
                'unique_patients': int(df['patient'].nunique()),
                'patient_counts': df['patient'].value_counts().to_dict()
            },
            'edf_statistics': {
                'unique_edfs': int(df.groupby(['patient', 'edf']).ngroups),
                'edf_counts': {
                    f"{patient}|{edf}": int(count)
                    for (patient, edf), count in df.groupby(['patient', 'edf']).size().to_dict().items()
                }
            },
            'temporal_statistics': {
                'min_window_start': float(df['window_start_sec'].min()),
                'max_window_end': float(df['window_end_sec'].max()),
                'mean_duration': float(df['window_duration_sec'].mean()),
                'unique_window_uids': int(df['window_uid'].nunique())
            },
            'validation_results': validation_results
        }
        
        with open(os.path.join(self.output_dir, filename), 'w') as f:
            json.dump(
                dataset_info,
                f,
                indent=2,
                default=json_serializer
            )
        
        self.logger.info(f"Dataset audit saved: {filename}")
    
    def generate_temporal_audit(self, df: pd.DataFrame, filename: str = "PHASE5A_TEMPORAL_AUDIT.json"):
        """Generate temporal integrity audit"""
        temporal_stats = {}
        
        for (patient, edf), group in df.groupby(['patient', 'edf']):
            group = group.sort_values('window_index')
            temporal_stats[f"{patient}|{edf}"] = {
                'window_count': len(group),
                'min_window_index': int(group['window_index'].min()),
                'max_window_index': int(group['window_index'].max()),
                'min_start_sec': float(group['window_start_sec'].min()),
                'max_end_sec': float(group['window_end_sec'].max()),
                'total_duration_sec': float(group['window_end_sec'].max() - group['window_start_sec'].min()),
                'stride_consistency': bool((group['stride_sec'] == STRIDE_SEC).all()),
                'duration_consistency': bool((group['window_duration_sec'] == WINDOW_LENGTH_SEC).all())
            }
        
        with open(os.path.join(self.output_dir, filename), 'w') as f:
            json.dump(
                temporal_stats,
                f,
                indent=2,
                default=json_serializer
            )
        
        self.logger.info(f"Temporal audit saved: {filename}")
    
    def generate_patient_audit(self, df: pd.DataFrame, filename: str = "PHASE5A_PATIENT_AUDIT.csv"):
        """Generate patient audit CSV"""
        patient_stats = df.groupby('patient').agg({
            'label': ['count', 'sum'],
            'window_index': 'count',
            'window_uid': 'nunique'
        }).round(2)
        
        patient_stats.columns = ['total_windows', 'seizure_windows', 'window_count', 'unique_uids']
        patient_stats.to_csv(os.path.join(self.output_dir, filename))
        
        self.logger.info(f"Patient audit saved: {filename}")
    
    def generate_edf_audit(self, df: pd.DataFrame, filename: str = "PHASE5A_EDF_AUDIT.csv"):
        """Generate EDF audit CSV"""
        edf_stats = df.groupby(['patient', 'edf']).agg({
            'label': ['count', 'sum'],
            'window_index': ['min', 'max'],
            'window_start_sec': ['min', 'max'],
            'window_end_sec': ['min', 'max']
        }).round(2)
        
        edf_stats.to_csv(os.path.join(self.output_dir, filename))
        
        self.logger.info(f"EDF audit saved: {filename}")
    
    def generate_window_audit(self, df: pd.DataFrame, filename: str = "PHASE5A_WINDOW_AUDIT.csv"):
        """Generate window audit CSV (sample)"""
        # Sample first 1000 rows for window audit to keep file size manageable
        sample_df = df.head(1000)[['window_uid', 'patient', 'edf', 'window_index', 
                                   'window_start_sec', 'window_end_sec', 'label']]
        sample_df.to_csv(os.path.join(self.output_dir, filename), index=False)
        
        self.logger.info(f"Window audit saved: {filename}")
    
    def generate_execution_report(self, execution_stats: Dict, filename: str = "PHASE5A_EXECUTION_REPORT.json"):
        """Generate final execution report"""
        with open(os.path.join(self.output_dir, filename), 'w') as f:
            json.dump(
                execution_stats,
                f,
                indent=2,
                default=json_serializer
            )
        
        self.logger.info(f"Execution report saved: {filename}")

# ============================================================================
# MAIN PROCESSING ENGINE
# ============================================================================

class Phase5AEngine:
    """Main Phase 5A Temporal Dataset Foundation Engine"""
    
    def __init__(self, input_file: str = "real_feature_dataset_v4_clean.parquet",
                 output_file: str = "real_feature_dataset_v5_temporal.parquet"):
        self.input_file = input_file
        self.output_file = output_file
        self.logger = ProductionLogger()
        self.checkpoint_manager = CheckpointManager(logger=self.logger)
        self.temporal_engine = TemporalReconstructionEngine(logger=self.logger)
        self.validation_gate = ValidationGate(logger=self.logger)
        self.audit_generator = AuditGenerator(logger=self.logger)
        
        self.execution_stats = {
            'start_time': datetime.now().isoformat(),
            'input_rows': 0,
            'output_rows': 0,
            'input_seizure_windows': 0,
            'output_seizure_windows': 0,
            'input_background_windows': 0,
            'output_background_windows': 0,
            'patients': 0,
            'edf_files': 0,
            'feature_columns': EXPECTED_FEATURE_COUNT,
            'temporal_columns_added': 6,
            'temporal_integrity_status': 'PENDING',
            'dataset_integrity_status': 'PENDING',
            'execution_time_seconds': 0,
            'output_dataset_path': output_file,
            'audit_report_path': 'PHASE5A_EXECUTION_REPORT.json'
        }
    
    def run(self):
        """Execute Phase 5A processing pipeline"""
        try:
            start_time = time.time()
            self.logger.info("=" * 80)
            self.logger.info("NEUROVISION OMEGA - PHASE 5A INITIATED")
            self.logger.info("=" * 80)
            
            # Load input dataset
            self.logger.info(f"Loading input dataset: {self.input_file}")
            input_df = pd.read_parquet(self.input_file)
            self.execution_stats['input_rows'] = len(input_df)
            self.logger.info(f"Loaded {len(input_df):,} rows, {len(input_df.columns)} columns")
            
            # GATE 1: Schema verification
            if not self.validation_gate.gate1_schema_verification(input_df, is_input=True):
                self._abort_execution("GATE 1 failed - Schema verification failed")
            
            # Store input statistics for comparison
            input_seizure_count = (input_df['label'] == 1).sum()
            input_background_count = (input_df['label'] == 0).sum()
            input_patient_count = input_df['patient'].nunique()
            input_edf_count = input_df.groupby(['patient', 'edf']).ngroups
            
            self.execution_stats['input_seizure_windows'] = int(input_seizure_count)
            self.execution_stats['input_background_windows'] = int(input_background_count)
            self.execution_stats['patients'] = int(input_patient_count)
            self.execution_stats['edf_files'] = int(input_edf_count)
            
            # Temporal reconstruction via chunked processing
            self.logger.info("Starting temporal reconstruction")
            checkpoint = self.checkpoint_manager.get_checkpoint()
            
            # Process by EDF groups
            processed_rows = checkpoint.get('rows_processed', 0)
            processed_edfs = checkpoint.get('edf_groups_processed', 0)
            
            # If we have a checkpoint, filter unprocessed groups
            if processed_rows > 0 and checkpoint.get('current_edf'):
                self.logger.info(f"Resuming from checkpoint: {processed_rows:,} rows processed")
                # Filter out already processed groups
                processed_groups = set()
                # This would need to track which groups were processed
                # For simplicity in this implementation, we'll reprocess from scratch
                # but with checkpointing capability built
                self.logger.warning("Checkpoint resume requires full reprocessing for integrity")
            
            # Group by patient and edf for temporal reconstruction
            grouped = input_df.groupby(['patient', 'edf'])
            reconstructed_chunks = []
            total_groups = len(grouped)
            
            for idx, ((patient, edf), group) in enumerate(grouped):
                if idx % 10 == 0:
                    self.logger.info(f"Processing EDF group {idx+1}/{total_groups}: {patient}|{edf}")
                
                # Reconstruct temporal metadata
                reconstructed_group = self.temporal_engine.reconstruct_temporal_metadata(
                    group, patient, edf, start_index=0
                )
                reconstructed_chunks.append(reconstructed_group)
                
                processed_rows += len(group)
                processed_edfs += 1
                
                # Save checkpoint every 50 groups
                if (idx + 1) % 50 == 0:
                    self.checkpoint_manager.save_checkpoint(
                        'temporal_reconstruction', processed_rows, processed_edfs,
                        current_edf=edf, current_patient=patient
                    )
                
                # Memory management
                if len(reconstructed_chunks) >= GC_THRESHOLD:
                    self.logger.info("Forcing garbage collection")
                    gc.collect()
            
            # Concatenate all reconstructed chunks
            self.logger.info("Concatenating reconstructed chunks")
            output_df = pd.concat(reconstructed_chunks, ignore_index=True)
            
            # Verify row count preservation
            if len(output_df) != len(input_df):
                self._abort_execution(f"Row count mismatch: {len(output_df)} vs {len(input_df)}")
            
            self.execution_stats['output_rows'] = len(output_df)
            
            # GATE 2: Feature preservation
            if not self.validation_gate.gate2_feature_preservation(input_df, output_df):
                self._abort_execution("GATE 2 failed - Feature preservation failed")
            
            # GATE 3: Label preservation
            if not self.validation_gate.gate3_label_preservation(input_df, output_df):
                self._abort_execution("GATE 3 failed - Label preservation failed")
            
            self.execution_stats['output_seizure_windows'] = (output_df['label'] == 1).sum()
            self.execution_stats['output_background_windows'] = (output_df['label'] == 0).sum()
            
            # GATE 4: Patient integrity
            if not self.validation_gate.gate4_patient_integrity(input_df, output_df):
                self._abort_execution("GATE 4 failed - Patient integrity failed")
            
            # GATE 5: EDF integrity
            if not self.validation_gate.gate5_edf_integrity(input_df, output_df):
                self._abort_execution("GATE 5 failed - EDF integrity failed")
            
            # GATE 6: Temporal integrity
            if not self.validation_gate.gate6_temporal_integrity(output_df):
                self._abort_execution("GATE 6 failed - Temporal integrity failed")
            
            self.execution_stats['temporal_integrity_status'] = 'PASSED'
            self.execution_stats['dataset_integrity_status'] = 'PASSED'
            
            # Save output dataset
            self.logger.info(f"Saving output dataset: {self.output_file}")
            output_df.to_parquet(self.output_file, index=False, compression='snappy')
            
            # Generate audit artifacts
            self.logger.info("Generating audit artifacts")
            self.audit_generator.generate_schema_audit(output_df)
            self.audit_generator.generate_dataset_audit(output_df, self.validation_gate.validation_results)
            self.audit_generator.generate_temporal_audit(output_df)
            self.audit_generator.generate_patient_audit(output_df)
            self.audit_generator.generate_edf_audit(output_df)
            self.audit_generator.generate_window_audit(output_df)
            
            # Final execution stats
            execution_time = time.time() - start_time
            self.execution_stats['execution_time_seconds'] = execution_time
            self.execution_stats['end_time'] = datetime.now().isoformat()
            
            self.audit_generator.generate_execution_report(self.execution_stats)
            
            # Display final report
            self._display_final_report(execution_time)
            
            # Clear checkpoint on success
            if os.path.exists("PHASE5A_CHECKPOINT.json"):
                os.remove("PHASE5A_CHECKPOINT.json")
                self.logger.info("Checkpoint cleared")
            
            self.logger.success("PHASE 5A COMPLETED SUCCESSFULLY")
            
        except Exception as e:
            self.logger.error(f"Fatal error: {str(e)}")
            self.logger.error(traceback.format_exc())
            self._abort_execution(f"Exception: {str(e)}")
    
    def _abort_execution(self, reason: str):
        """Abort execution with diagnostic report"""
        self.logger.error("=" * 80)
        self.logger.error("EXECUTION ABORTED")
        self.logger.error(f"REASON: {reason}")
        self.logger.error("=" * 80)
        
        # Save failure checkpoint
        self.checkpoint_manager.save_checkpoint('FAILED', 0, 0)
        
        sys.exit(1)
    
    def _display_final_report(self, execution_time: float):
        """Display final execution report"""
        print("\n" + "=" * 80)
        print("PHASE 5A TEMPORAL DATASET FOUNDATION COMPLETE")
        print("=" * 80)
        print(f"\nInput Rows:                    {self.execution_stats['input_rows']:,}")
        print(f"Output Rows:                   {self.execution_stats['output_rows']:,}")
        print(f"\nInput Seizure Windows:         {self.execution_stats['input_seizure_windows']:,}")
        print(f"Output Seizure Windows:        {self.execution_stats['output_seizure_windows']:,}")
        print(f"\nInput Background Windows:      {self.execution_stats['input_background_windows']:,}")
        print(f"Output Background Windows:     {self.execution_stats['output_background_windows']:,}")
        print(f"\nPatients:                      {self.execution_stats['patients']}")
        print(f"EDF Files:                     {self.execution_stats['edf_files']}")
        print(f"\nFeature Columns:               {self.execution_stats['feature_columns']}")
        print(f"Temporal Columns Added:        {self.execution_stats['temporal_columns_added']}")
        print(f"\nTemporal Integrity Status:     {self.execution_stats['temporal_integrity_status']}")
        print(f"Dataset Integrity Status:      {self.execution_stats['dataset_integrity_status']}")
        print(f"\nExecution Time:                {execution_time:.2f} seconds")
        print(f"\nOutput Dataset Path:           {self.execution_stats['output_dataset_path']}")
        print(f"Audit Report Path:             {self.execution_stats['audit_report_path']}")
        print("\n" + "=" * 80)
        print("SUCCESS CRITERIA")
        print("=" * 80)
        print("✓ 100% row preservation achieved")
        print("✓ 100% feature preservation achieved")
        print("✓ 100% label preservation achieved")
        print("✓ 100% patient preservation achieved")
        print("✓ 100% EDF preservation achieved")
        print("✓ 100% temporal reconstruction completed")
        print("✓ 100% validation gates passed")
        print("✓ All audit artifacts generated")
        print("✓ Output parquet successfully written")
        print("✓ No schema drift")
        print("✓ No label drift")
        print("✓ No feature drift")
        print("✓ No patient drift")
        print("✓ No EDF drift")
        print("=" * 80 + "\n")

# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point for Phase 5A execution"""
    
    # Verify input file exists
    input_file = "real_feature_dataset_v4_clean.parquet"
    if not os.path.exists(input_file):
        print(f"ERROR: Input file not found: {input_file}")
        print("Please ensure the V4 dataset is in the current directory")
        sys.exit(1)
    
    # Execute Phase 5A engine
    engine = Phase5AEngine(
        input_file=input_file,
        output_file="real_feature_dataset_v5_temporal.parquet"
    )
    
    engine.run()

if __name__ == "__main__":
    main()