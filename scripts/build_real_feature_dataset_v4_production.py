#!/usr/bin/env python3
"""
NeuroVision Omega Seizure Detection System - Phase 4 Production
Channel-Aware Aggregated Features - ULTIMATE PRODUCTION VERSION v3
================================================================================
CRITICAL FIXES APPLIED:
1. Correct seizure database path (E:\Project\neurovision_ai\SEIZURE_INTERVAL_DATABASE.json)
2. Maintained scientific continuity: STRIDE = 2.0 seconds (same as V1-V3)
3. Correct output path for training pipeline integration
4. Fixed PyArrow writer with proper string handling (NO in-place dict modification)
5. Robust feature validation with fallbacks
6. Production-ready with checkpointing and fault tolerance
7. Dictionary copy safety - no pop() mutations on original dicts
8. FIXED: numpy.trapz compatibility issue - using scipy.integrate.trapezoid instead
================================================================================
"""

import json
import gc
import time
import warnings
import logging
import traceback
import pickle
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import pandas as pd
import pywt
import antropy as ant
import mne
from scipy.signal import welch
from scipy.integrate import trapezoid  # FIXED: Use scipy's trapezoid instead of np.trapz
import pyarrow as pa
import pyarrow.parquet as pq
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed

# Suppress warnings
warnings.filterwarnings("ignore")
mne.set_log_level("ERROR")

# ============================================================================
# PRODUCTION CONSTANTS - CRITICAL PATH FIXES
# ============================================================================

# CORRECTED: Seizure database location (project root, not dataset root)
PROJECT_ROOT = Path(r"E:\Project\neurovision_ai")
DATASET_ROOT = Path(r"E:\NeuroVision\datasets\chbmit")
SEIZURE_DB_PATH = PROJECT_ROOT / "SEIZURE_INTERVAL_DATABASE.json"

# CORRECTED: Output path for training pipeline integration
OUTPUT_PATH = PROJECT_ROOT / "real_feature_dataset_v4.parquet"

# Checkpoint and log directories
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints_v4"
FAILED_EDF_LOG = PROJECT_ROOT / "FAILED_EDF_LOG_v4.txt"
VALIDATION_LOG = PROJECT_ROOT / "VALIDATION_LOG_v4.txt"

# Window configuration - MAINTAINED for scientific continuity with V1-V3
WINDOW_LENGTH_SEC = 4.0
STRIDE_SEC = 2.0  # CRITICAL: Must match V1-V3 for benchmark comparison

# Production batch size (optimized for 16GB RAM)
BATCH_SIZE = 10000

# Memory management
MEMORY_THRESHOLD_PERCENT = 85.0

# Processing configuration
MAX_WORKERS = 4  # Threads for channel processing
RETRY_ATTEMPTS = 3
RETRY_DELAY_SEC = 2

# Frequency bands for spectral features
FREQ_BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 45.0)
}

# Wavelet configuration
WAVELET_NAME = "db4"
WAVELET_LEVEL = 5
MIN_WAVELET_SAMPLES = 2 ** WAVELET_LEVEL

# Base features (per channel) - MUST match aggregation
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
EXPECTED_FEATURE_COUNT = len(BASE_FEATURES) * len(AGGREGATIONS)  # 32 * 3 = 96

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "v4_production.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# ENTROPY MONITORING
# ============================================================================

class EntropyFailureMonitor:
    """Monitor entropy computation failures"""
    def __init__(self):
        self.failure_counts = defaultdict(int)
        self.total_attempts = defaultdict(int)
        self.threshold = 1000
    
    def record_failure(self, feature_name: str):
        self.failure_counts[feature_name] += 1
        if self.failure_counts[feature_name] % self.threshold == 0:
            logger.warning(f"Entropy {feature_name} failed {self.failure_counts[feature_name]} times")
    
    def record_attempt(self, feature_name: str):
        self.total_attempts[feature_name] += 1
    
    def get_failure_rate(self, feature_name: str) -> float:
        total = self.total_attempts.get(feature_name, 1)
        return self.failure_counts.get(feature_name, 0) / total

entropy_monitor = EntropyFailureMonitor()

# ============================================================================
# OPTIMIZED FEATURE FUNCTIONS
# ============================================================================

def safe_entropy_func(func, data, feature_name: str, *args, **kwargs) -> float:
    """Safely compute entropy with monitoring"""
    entropy_monitor.record_attempt(feature_name)
    try:
        result = func(data, *args, **kwargs)
        if np.isnan(result) or np.isinf(result):
            entropy_monitor.record_failure(feature_name)
            return 0.0
        return float(result)
    except Exception as e:
        entropy_monitor.record_failure(feature_name)
        if entropy_monitor.failure_counts[feature_name] % 100 == 0:
            logger.debug(f"Entropy {feature_name} error: {str(e)[:100]}")
        return 0.0

def compute_time_features(signal: np.ndarray) -> Dict[str, float]:
    """Extract time-domain features with minimal allocation"""
    signal_f32 = signal.astype(np.float32)
    
    # Basic statistics
    mean_val = np.mean(signal_f32)
    std_val = np.std(signal_f32)
    
    features = {
        "mean": float(mean_val),
        "std": float(std_val),
        "variance": float(std_val ** 2),
        "rms": float(np.sqrt(np.mean(signal_f32 ** 2))),
        "max": float(np.max(signal_f32)),
        "min": float(np.min(signal_f32)),
        "ptp": float(np.ptp(signal_f32)),
        "line_length": float(np.sum(np.abs(np.diff(signal_f32)))),
        "zero_crossings": float(np.sum(np.diff(np.signbit(signal_f32)) != 0))
    }
    
    # Percentile-based features (use float64 for accuracy)
    signal_f64 = signal_f32.astype(np.float64)
    percentiles = np.percentile(signal_f64, [25, 75])
    features["iqr"] = float(percentiles[1] - percentiles[0])
    features["mad"] = float(np.median(np.abs(signal_f64 - np.median(signal_f64))))
    
    return features

def compute_entropy_features(signal: np.ndarray, sfreq: float) -> Dict[str, float]:
    """Extract entropy-based features with monitoring"""
    signal_f64 = signal.astype(np.float64)
    
    return {
        "sample_entropy": safe_entropy_func(ant.sample_entropy, signal_f64, "sample_entropy"),
        "perm_entropy": safe_entropy_func(ant.perm_entropy, signal_f64, "perm_entropy", order=3, delay=1),
        "spectral_entropy": safe_entropy_func(ant.spectral_entropy, signal_f64, "spectral_entropy", sfreq, method='welch', normalize=True)
    }

def compute_fractal_features(signal: np.ndarray) -> Dict[str, float]:
    """Extract fractal dimension features"""
    signal_f64 = signal.astype(np.float64)
    
    return {
        "higuchi_fd": safe_entropy_func(ant.higuchi_fd, signal_f64, "higuchi_fd"),
        "petrosian_fd": safe_entropy_func(ant.petrosian_fd, signal_f64, "petrosian_fd")
    }

def compute_wavelet_features_adaptive(signal: np.ndarray) -> Dict[str, float]:
    """Extract wavelet energy with adaptive level selection"""
    features = {}
    signal_length = len(signal)
    
    # Determine maximum feasible decomposition level
    max_level = int(np.log2(signal_length)) - 1 if signal_length > 4 else 1
    actual_level = min(WAVELET_LEVEL, max_level)
    
    if actual_level < 1 or signal_length < MIN_WAVELET_SAMPLES:
        # Signal too short for wavelet decomposition
        for i in range(WAVELET_LEVEL + 1):
            features[f"wavelet_energy_{i}"] = 0.0
        return features
    
    try:
        coeffs = pywt.wavedec(signal, WAVELET_NAME, level=actual_level)
        
        # Compute energies
        for i, coeff in enumerate(coeffs):
            energy = np.sum(coeff ** 2)
            features[f"wavelet_energy_{i}"] = float(energy) if not np.isnan(energy) else 0.0
        
        # Pad with zeros for missing levels
        for i in range(actual_level + 1, WAVELET_LEVEL + 1):
            features[f"wavelet_energy_{i}"] = 0.0
            
    except Exception as e:
        logger.debug(f"Wavelet decomposition failed at level {actual_level}: {str(e)[:50]}")
        for i in range(WAVELET_LEVEL + 1):
            features[f"wavelet_energy_{i}"] = 0.0
    
    return features

def compute_spectral_features_stable(signal: np.ndarray, sfreq: float) -> Dict[str, float]:
    """Extract spectral features with numerical stability - FIXED np.trapz issue"""
    signal_f32 = signal.astype(np.float32)
    n = len(signal_f32)
    
    # Apply Hanning window to reduce spectral leakage
    window = np.hanning(n)
    signal_windowed = signal_f32 * window
    
    # Compute power spectral density using Welch's method for stability
    nperseg = min(256, n // 2)
    if nperseg < 4:
        nperseg = n
    
    freqs, psd = welch(signal_windowed, fs=sfreq, nperseg=nperseg, noverlap=None)
    
    features = {}
    band_powers = {}
    total_power = 1e-12  # Epsilon to prevent division by zero
    
    # Band powers - FIXED: Using scipy.integrate.trapezoid instead of np.trapz
    for band_name, (low, high) in FREQ_BANDS.items():
        mask = (freqs >= low) & (freqs < high)
        if np.any(mask):
            # Use trapezoid integration for accurate power calculation
            band_power = trapezoid(psd[mask], freqs[mask])
        else:
            band_power = 0.0
        
        band_powers[band_name] = band_power
        features[f"{band_name}_power"] = float(np.log1p(band_power))  # Log transform for stability
        total_power += band_power
    
    # Relative powers with numerical stability
    for band_name in FREQ_BANDS.keys():
        power = band_powers[band_name]
        relative = power / total_power if total_power > 1e-10 else 0.0
        features[f"{band_name}_relative"] = float(np.clip(relative, 0.0, 1.0))
    
    return features

def extract_channel_features_optimized(signal: np.ndarray, sfreq: float) -> Dict[str, float]:
    """Extract all features from a single channel with optimization"""
    features = {}
    
    # Time features (fastest, compute first)
    features.update(compute_time_features(signal))
    
    # Use float64 for complex computations
    signal_f64 = signal.astype(np.float64)
    
    # Entropy and fractal features
    features.update(compute_entropy_features(signal_f64, sfreq))
    features.update(compute_fractal_features(signal_f64))
    
    # Wavelet features (computationally intensive)
    features.update(compute_wavelet_features_adaptive(signal_f64))
    
    # Spectral features
    features.update(compute_spectral_features_stable(signal_f64, sfreq))
    
    # Verify all base features are present
    for base_feature in BASE_FEATURES:
        if base_feature not in features:
            features[base_feature] = 0.0
    
    return features

def aggregate_channel_features(channel_features_list: List[Dict[str, float]]) -> Dict[str, float]:
    """Aggregate features across channels using mean, std, and max"""
    if not channel_features_list:
        # Return zeros for all expected features
        aggregated = {}
        for feature_name in BASE_FEATURES:
            for agg in AGGREGATIONS:
                aggregated[f"{feature_name}_{agg}"] = 0.0
        return aggregated
    
    aggregated = {}
    
    for feature_name in BASE_FEATURES:
        values = [ch.get(feature_name, 0.0) for ch in channel_features_list]
        
        if values:
            aggregated[f"{feature_name}_mean"] = float(np.mean(values))
            aggregated[f"{feature_name}_std"] = float(np.std(values))
            aggregated[f"{feature_name}_max"] = float(np.max(values))
        else:
            aggregated[f"{feature_name}_mean"] = 0.0
            aggregated[f"{feature_name}_std"] = 0.0
            aggregated[f"{feature_name}_max"] = 0.0
    
    return aggregated

# ============================================================================
# SEIZURE INTERVAL VALIDATION
# ============================================================================

def validate_seizure_database(db: Dict[str, Dict[str, List[List[float]]]]) -> Tuple[bool, List[str]]:
    """Validate all seizure intervals before processing"""
    issues = []
    
    for patient, files in db.items():
        for edf_file, intervals in files.items():
            for idx, (start, end) in enumerate(intervals):
                # Check temporal order
                if start >= end:
                    issues.append(f"Invalid interval {idx} in {patient}/{edf_file}: {start} >= {end}")
                
                # Check for negative values
                if start < 0 or end < 0:
                    issues.append(f"Negative interval in {patient}/{edf_file}: {start}-{end}")
                
                # Check for overlapping intervals
                if idx > 0:
                    prev_end = intervals[idx-1][1]
                    if start < prev_end:
                        issues.append(f"Overlapping intervals in {patient}/{edf_file}: {prev_end} vs {start}")
                
                # Check for zero-length intervals
                if abs(end - start) < 0.001:
                    issues.append(f"Zero-length interval in {patient}/{edf_file}: {start}-{end}")
    
    for issue in issues:
        logger.error(issue)
    
    return len(issues) == 0, issues

def overlaps_with_seizure(window_start: float, window_end: float, seizure_intervals: List[List[float]], epsilon: float = 1e-9) -> bool:
    """
    Clinical labeling: Window is positive if ANY portion overlaps seizure.
    Includes boundary cases where window exactly touches seizure boundaries.
    """
    for s, e in seizure_intervals:
        # Validate interval
        if s >= e:
            continue
        
        # Standard overlap condition
        if (window_start + epsilon) < e and (window_end - epsilon) > s:
            return True
        
        # Edge case: window exactly aligned with seizure start
        if abs(window_end - s) < epsilon:
            return True
        # Edge case: window exactly aligned with seizure end
        if abs(window_start - e) < epsilon:
            return True
            
    return False

# ============================================================================
# EDF LOADING WITH ERROR HANDLING
# ============================================================================

def load_edf_production(edf_path: Path) -> Optional[mne.io.Raw]:
    """Production-grade EDF loading with comprehensive error handling"""
    try:
        # Verify file exists and is readable
        if not edf_path.exists():
            logger.error(f"EDF file not found: {edf_path}")
            return None
        
        if edf_path.stat().st_size == 0:
            logger.error(f"EDF file is empty: {edf_path}")
            return None
        
        # Load with explicit parameters for robustness
        raw = mne.io.read_raw_edf(
            edf_path, 
            preload=True, 
            verbose=False,
            stim_channel='auto'  # Auto-detect stimulus channels
        )
        
        # Identify EEG channels (exclude non-EEG channels)
        eeg_keywords = ['EEG', 'C', 'F', 'P', 'O', 'T', 'FP', 'FZ', 'CZ', 'PZ', 'OZ']
        eeg_channels = []
        
        for ch in raw.ch_names:
            ch_upper = ch.upper()
            if any(keyword in ch_upper for keyword in eeg_keywords):
                eeg_channels.append(ch)
            elif ch_upper.startswith('EKG') or ch_upper.startswith('ECG'):
                continue  # Skip cardiac channels
            elif ch_upper.startswith('EOG'):
                continue  # Skip eye movement channels
            else:
                # Keep if it looks like an EEG channel
                if len(ch) <= 4 and ch_upper.isalnum():
                    eeg_channels.append(ch)
        
        if len(eeg_channels) < 2:
            logger.warning(f"Less than 2 EEG channels found in {edf_path.name}, using all channels")
            eeg_channels = raw.ch_names
        
        # Select only EEG channels
        if len(eeg_channels) < len(raw.ch_names):
            raw.pick_channels(eeg_channels)
        
        # Handle duplicate channel names by creating unique names
        ch_names = raw.ch_names
        if len(ch_names) != len(set(ch_names)):
            new_names = []
            counter = defaultdict(int)
            for name in ch_names:
                if counter[name] > 0:
                    new_names.append(f"{name}_{counter[name]}")
                else:
                    new_names.append(name)
                counter[name] += 1
            raw.rename_channels({old: new for old, new in zip(ch_names, new_names)})
        
        # Check for NaN or Inf in data
        data_check = raw.get_data()[:5, :100]  # Sample small portion
        if np.any(np.isnan(data_check)) or np.any(np.isinf(data_check)):
            logger.error(f"Data contains NaN or Inf values in {edf_path.name}")
            return None
        
        return raw
        
    except Exception as e:
        logger.error(f"Failed to load {edf_path.name}: {str(e)}")
        return None

# ============================================================================
# PARALLEL CHANNEL PROCESSING
# ============================================================================

def process_channel_parallel(args):
    """Wrapper for parallel channel processing"""
    signal, sfreq, ch_idx = args
    try:
        features = extract_channel_features_optimized(signal, sfreq)
        return ch_idx, features
    except Exception as e:
        logger.error(f"Channel {ch_idx} processing failed: {str(e)[:100]}")
        return ch_idx, {}

def process_window_parallel(window_data: np.ndarray, sfreq: float) -> Dict[str, float]:
    """Process a window using parallel channel extraction"""
    n_channels = window_data.shape[0]
    
    # Prepare arguments for parallel processing
    channel_args = [(window_data[ch_idx, :], sfreq, ch_idx) for ch_idx in range(n_channels)]
    
    # Process channels in parallel
    channel_features = [{}] * n_channels
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_channel_parallel, args) for args in channel_args]
        for future in as_completed(futures):
            ch_idx, features = future.result()
            if features:
                channel_features[ch_idx] = features
    
    # Filter out failed channels
    valid_features = [f for f in channel_features if f]
    
    if not valid_features:
        return {}
    
    # Aggregate across channels
    return aggregate_channel_features(valid_features)

# ============================================================================
# WINDOW GENERATION (MAINTAINS STRIDE=2.0 FOR SCIENTIFIC CONTINUITY)
# ============================================================================

def generate_windows_from_edf(raw: mne.io.Raw, seizure_intervals: List[List[float]], 
                              patient_id: str, edf_name: str) -> List[Tuple[Dict[str, float], int]]:
    """Generate windows with STRIDE=2.0 seconds (matching V1-V3 for continuity)"""
    sfreq = raw.info['sfreq']
    duration = raw.times[-1]
    
    window_length_samples = int(WINDOW_LENGTH_SEC * sfreq)
    stride_samples = int(STRIDE_SEC * sfreq)  # 2.0 seconds - CRITICAL for continuity
    
    # Get full data as float32
    data = raw.get_data().astype(np.float32)
    n_samples = data.shape[1]
    
    windows = []
    
    for start_sample in range(0, n_samples - window_length_samples + 1, stride_samples):
        end_sample = start_sample + window_length_samples
        window_data = data[:, start_sample:end_sample]
        
        window_start_sec = start_sample / sfreq
        window_end_sec = end_sample / sfreq
        
        # Validate window
        if window_start_sec >= window_end_sec or window_start_sec < 0 or window_end_sec > duration:
            continue
        
        # Extract features
        features = process_window_parallel(window_data, sfreq)
        
        if not features:
            continue
        
        # Label window
        label = 1 if overlaps_with_seizure(window_start_sec, window_end_sec, seizure_intervals) else 0
        
        windows.append((features, label))
    
    return windows

# ============================================================================
# FIXED: PRODUCTION PARQUET WRITER - NO IN-PLACE DICT MODIFICATION
# ============================================================================

class ProductionParquetWriter:
    """Memory-efficient batch parquet writer with proper string handling and NO dict mutation"""
    
    def __init__(self, output_path: Path, batch_size: int = BATCH_SIZE):
        self.output_path = output_path
        self.batch_size = batch_size
        self.buffer_features = []  # Store feature dictionaries
        self.buffer_labels = []    # Store labels separately
        self.buffer_patients = []  # Store patient IDs separately
        self.buffer_edfs = []      # Store EDF names separately
        self.row_count = 0
        self.writer = None
        self.schema = None
        self.column_names = None
        
    def add_row(self, row: Dict[str, Any]):
        """
        Add a row to the buffer - SAFE: no modification of original dict.
        Creates a copy for feature data instead of mutating input.
        """
        # SAFE: Extract values without modifying original dict
        label = row["label"]
        patient = row["patient"]
        edf = row["edf"]
        
        # SAFE: Create a new dict for features (exclude metadata columns)
        feature_row = {
            k: v for k, v in row.items() 
            if k not in ("label", "patient", "edf")
        }
        
        # Store components separately
        self.buffer_features.append(feature_row)
        self.buffer_labels.append(label)
        self.buffer_patients.append(patient)
        self.buffer_edfs.append(edf)
        
        self.row_count += 1
        
        if len(self.buffer_features) >= self.batch_size:
            self.flush()
    
    def flush(self):
        """Write buffer to parquet file with proper type handling"""
        if not self.buffer_features:
            return
        
        # Convert features to DataFrame (all numeric)
        df_features = pd.DataFrame(self.buffer_features)
        
        # Add back the string columns
        df_features['label'] = self.buffer_labels
        df_features['patient'] = self.buffer_patients
        df_features['edf'] = self.buffer_edfs
        
        # Verify column count
        expected_cols = EXPECTED_FEATURE_COUNT + 3
        if df_features.shape[1] != expected_cols:
            logger.warning(f"Column count mismatch: {df_features.shape[1]} vs {expected_cols}")
            # Find missing columns
            actual_cols = set(df_features.columns)
            expected_cols_set = {f"{f}_{a}" for f in BASE_FEATURES for a in AGGREGATIONS}
            expected_cols_set.update(['label', 'patient', 'edf'])
            missing = expected_cols_set - actual_cols
            if missing:
                logger.warning(f"Missing columns: {missing}")
                # Add missing columns with zeros
                for col in missing:
                    df_features[col] = 0.0
        
        # Convert to PyArrow Table with proper schema
        table = pa.Table.from_pandas(df_features)
        
        # Write or append
        if self.writer is None:
            self.writer = pq.ParquetWriter(self.output_path, table.schema)
        
        self.writer.write_table(table)
        
        # Clear buffers and force GC
        self.buffer_features = []
        self.buffer_labels = []
        self.buffer_patients = []
        self.buffer_edfs = []
        gc.collect()
    
    def close(self):
        """Finalize writing"""
        self.flush()
        if self.writer:
            self.writer.close()

# ============================================================================
# CHECKPOINT MANAGEMENT
# ============================================================================

@dataclass
class ProcessingCheckpoint:
    """Checkpoint for resumable processing"""
    processed_files: Set[str] = field(default_factory=set)
    failed_files: Set[str] = field(default_factory=set)
    total_rows: int = 0
    seizure_windows: int = 0
    background_windows: int = 0
    last_update: float = field(default_factory=time.time)
    
    def save(self, checkpoint_dir: Path):
        """Save checkpoint to disk"""
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = checkpoint_dir / "v4_checkpoint.pkl"
        
        # Convert sets to lists for serialization
        save_data = {
            'processed_files': list(self.processed_files),
            'failed_files': list(self.failed_files),
            'total_rows': self.total_rows,
            'seizure_windows': self.seizure_windows,
            'background_windows': self.background_windows,
            'last_update': self.last_update
        }
        
        with open(checkpoint_path, 'wb') as f:
            pickle.dump(save_data, f)
        
        logger.debug(f"Checkpoint saved: {len(self.processed_files)} files processed")
    
    def load(self, checkpoint_dir: Path) -> bool:
        """Load checkpoint if exists"""
        checkpoint_path = checkpoint_dir / "v4_checkpoint.pkl"
        if not checkpoint_path.exists():
            return False
        
        try:
            with open(checkpoint_path, 'rb') as f:
                save_data = pickle.load(f)
            
            self.processed_files = set(save_data['processed_files'])
            self.failed_files = set(save_data['failed_files'])
            self.total_rows = save_data['total_rows']
            self.seizure_windows = save_data['seizure_windows']
            self.background_windows = save_data['background_windows']
            self.last_update = save_data['last_update']
            
            logger.info(f"Loaded checkpoint: {len(self.processed_files)} files already processed")
            return True
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return False

# ============================================================================
# MEMORY MONITORING
# ============================================================================

class MemoryMonitor:
    """Monitor and manage memory usage"""
    
    def __init__(self, threshold_percent: float = MEMORY_THRESHOLD_PERCENT):
        self.threshold = threshold_percent
        self.warning_count = 0
    
    def check_memory(self) -> bool:
        """Check if memory usage is below threshold"""
        try:
            memory = psutil.virtual_memory()
            if memory.percent > self.threshold:
                self.warning_count += 1
                logger.warning(f"Memory usage at {memory.percent:.1f}% (threshold: {self.threshold}%)")
                
                # Force garbage collection
                gc.collect()
                
                if self.warning_count > 5:
                    logger.error("Persistent high memory usage")
                
                return False
            else:
                self.warning_count = max(0, self.warning_count - 1)
                return True
        except Exception as e:
            logger.debug(f"Memory check failed: {e}")
            return True
    
    def wait_if_needed(self):
        """Wait if memory is high"""
        if not self.check_memory():
            time.sleep(2)
            gc.collect()

# ============================================================================
# MAIN PROCESSING PIPELINE
# ============================================================================

def scan_edf_files_production(dataset_root: Path) -> List[Tuple[Path, str]]:
    """Comprehensive EDF file scanning"""
    edf_files = []
    extensions = ['*.edf', '*.EDF']
    
    # Expected patient folders (CHB-MIT specific)
    expected_patients = [f"chb{str(i).zfill(2)}" for i in range(1, 25)]
    found_patients = []
    
    for patient_id in expected_patients:
        patient_dir = dataset_root / patient_id
        if not patient_dir.exists():
            logger.warning(f"Expected patient folder {patient_id} not found")
            continue
        
        found_patients.append(patient_id)
        
        for ext in extensions:
            for edf_file in sorted(patient_dir.glob(ext)):
                # Skip summary and info files
                if 'summary' in edf_file.name.lower() or 'info' in edf_file.name.lower():
                    continue
                edf_files.append((edf_file, patient_id))
    
    # Remove duplicates (same file matched by multiple extensions)
    edf_files = list(dict.fromkeys(edf_files))
    
    logger.info(f"Found {len(edf_files)} EDF files across {len(found_patients)} patients")
    
    return edf_files

def process_edf_file_production(edf_path: Path, patient_id: str, seizure_intervals: Dict[str, List[List[float]]],
                                batch_writer: ProductionParquetWriter, checkpoint: ProcessingCheckpoint,
                                memory_monitor: MemoryMonitor) -> Tuple[int, int, bool]:
    """Process a single EDF file with retry logic"""
    
    for attempt in range(RETRY_ATTEMPTS):
        try:
            memory_monitor.wait_if_needed()
            
            # Load EDF
            raw = load_edf_production(edf_path)
            if raw is None:
                return 0, 0, False
            
            # Get seizure intervals for this file
            file_intervals = seizure_intervals.get(edf_path.name, [])
            
            # Generate windows
            windows = generate_windows_from_edf(raw, file_intervals, patient_id, edf_path.name)
            
            seizure_count = 0
            background_count = 0
            
            # Add to batch writer - creates safe copies
            for features, label in windows:
                # Build row dict without modifying any original data
                row = {
                    **features,  # Unpack features (creates new dict)
                    'label': label,
                    'patient': patient_id,
                    'edf': edf_path.name
                }
                batch_writer.add_row(row)
                
                if label == 1:
                    seizure_count += 1
                else:
                    background_count += 1
            
            # Cleanup
            del raw
            gc.collect()
            
            # Update checkpoint
            checkpoint.processed_files.add(str(edf_path))
            checkpoint.seizure_windows += seizure_count
            checkpoint.background_windows += background_count
            checkpoint.total_rows = batch_writer.row_count
            checkpoint.save(CHECKPOINT_DIR)
            
            return seizure_count, background_count, True
            
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{RETRY_ATTEMPTS} failed for {edf_path.name}: {str(e)}")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY_SEC * (attempt + 1))
            else:
                logger.error(f"Failed to process {edf_path.name} after {RETRY_ATTEMPTS} attempts")
                traceback.print_exc()
                return 0, 0, False
    
    return 0, 0, False

def validate_output_dataset(output_path: Path) -> bool:
    """Validate the final output dataset"""
    logger.info("Validating output dataset...")
    
    try:
        df = pd.read_parquet(output_path)
        
        # Check shape
        expected_cols = EXPECTED_FEATURE_COUNT + 3
        if df.shape[1] != expected_cols:
            logger.error(f"Column count mismatch: {df.shape[1]} vs {expected_cols}")
            logger.error(f"Expected {expected_cols} columns, got {df.shape[1]}")
            return False
        
        # Check for NaN values
        nan_cols = df.columns[df.isna().any()].tolist()
        if nan_cols:
            logger.error(f"NaN values found in columns: {nan_cols[:10]}")
            # Fill NaN with 0 as fallback
            df[nan_cols] = df[nan_cols].fillna(0)
            logger.info(f"Filled NaN values in {len(nan_cols)} columns with 0")
        
        # Check for infinite values
        inf_cols = []
        for col in df.select_dtypes(include=[np.number]).columns:
            if np.isinf(df[col]).any():
                inf_cols.append(col)
                df[col] = df[col].replace([np.inf, -np.inf], 0)
        
        if inf_cols:
            logger.warning(f"Infinite values found in columns: {inf_cols[:10]}, replaced with 0")
        
        # Check label distribution
        label_counts = df['label'].value_counts()
        logger.info(f"Label distribution: Background={label_counts.get(0, 0):,}, Seizure={label_counts.get(1, 0):,}")
        
        if label_counts.get(1, 0) < 100:
            logger.error("Insufficient seizure windows detected")
            return False
        
        # Check for data leakage (duplicate patient-edf-label combinations)
        duplicates = df.duplicated(subset=['patient', 'edf']).sum()
        if duplicates > 0:
            logger.warning(f"Found {duplicates} duplicate patient-edf entries")
        
        # Save validation report
        with open(VALIDATION_LOG, 'w') as f:
            f.write(f"Validation Report - {datetime.now()}\n")
            f.write(f"=" * 60 + "\n")
            f.write(f"Total rows: {len(df):,}\n")
            f.write(f"Total columns: {df.shape[1]}\n")
            f.write(f"Feature columns: {EXPECTED_FEATURE_COUNT}\n")
            f.write(f"Background windows: {label_counts.get(0, 0):,}\n")
            f.write(f"Seizure windows: {label_counts.get(1, 0):,}\n")
            f.write(f"Ratio (seizure/background): {label_counts.get(1, 0) / max(1, label_counts.get(0, 0)):.4f}\n")
            f.write(f"NaN columns (filled): {len(nan_cols)}\n")
            f.write(f"Inf columns (filled): {len(inf_cols)}\n")
            f.write(f"Duplicates: {duplicates}\n")
        
        # Save cleaned dataframe if fixes were applied
        if nan_cols or inf_cols:
            df.to_parquet(output_path)
            logger.info("Saved cleaned dataset with NaN/Inf fixes")
        
        return True
        
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        return False

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Production main execution with checkpointing and fault tolerance"""
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("NeuroVision Omega - Phase 4 Production Pipeline")
    logger.info("Channel-Aware Aggregated Features (ULTIMATE PRODUCTION VERSION v3)")
    logger.info(f"Window: {WINDOW_LENGTH_SEC}s, Stride: {STRIDE_SEC}s (matches V1-V3)")
    logger.info("=" * 80)
    
    # Create necessary directories
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Load and validate seizure database
    logger.info(f"Loading seizure interval database from: {SEIZURE_DB_PATH}")
    try:
        if not SEIZURE_DB_PATH.exists():
            logger.error(f"Seizure database not found at: {SEIZURE_DB_PATH}")
            logger.error("Expected location: E:\\Project\\neurovision_ai\\SEIZURE_INTERVAL_DATABASE.json")
            return
        
        with open(SEIZURE_DB_PATH, 'r') as f:
            seizure_db = json.load(f)
        logger.info(f"Loaded database for {len(seizure_db)} patients")
    except Exception as e:
        logger.error(f"Failed to load seizure database: {e}")
        return
    
    # Validate database
    logger.info("Validating seizure intervals...")
    is_valid, issues = validate_seizure_database(seizure_db)
    if not is_valid:
        logger.error(f"Seizure database validation failed with {len(issues)} issues")
        for issue in issues[:10]:  # Show first 10 issues
            logger.error(f"  {issue}")
        return
    
    logger.info("Seizure database validation passed")
    
    # Scan EDF files
    logger.info(f"Scanning for EDF files in: {DATASET_ROOT}")
    edf_files = scan_edf_files_production(DATASET_ROOT)
    logger.info(f"Found {len(edf_files)} EDF files")
    
    if len(edf_files) == 0:
        logger.error("No EDF files found. Check DATASET_ROOT path.")
        logger.error(f"Current DATASET_ROOT: {DATASET_ROOT}")
        return
    
    # Load checkpoint
    checkpoint = ProcessingCheckpoint()
    checkpoint.load(CHECKPOINT_DIR)
    
    # Filter already processed files
    pending_files = [(path, pid) for path, pid in edf_files if str(path) not in checkpoint.processed_files]
    logger.info(f"Resuming: {len(pending_files)} files pending out of {len(edf_files)} total")
    
    if not pending_files:
        logger.info("All files already processed!")
        # Still validate output
        if OUTPUT_PATH.exists():
            validate_output_dataset(OUTPUT_PATH)
        return
    
    # Initialize components
    batch_writer = ProductionParquetWriter(OUTPUT_PATH, BATCH_SIZE)
    memory_monitor = MemoryMonitor()
    
    # Statistics
    total_seizure_windows = checkpoint.seizure_windows
    total_background_windows = checkpoint.background_windows
    processed_count = len(checkpoint.processed_files)
    failed_files = []
    
    # Process each file
    for idx, (edf_path, patient_id) in enumerate(pending_files, 1):
        logger.info(f"[{idx}/{len(pending_files)}] Processing {edf_path.name} (Patient: {patient_id})")
        
        # Get file-specific intervals
        patient_intervals = seizure_db.get(patient_id, {})
        file_intervals = patient_intervals.get(edf_path.name, [])
        
        # Process file
        seizure_count, background_count, success = process_edf_file_production(
            edf_path, patient_id, {edf_path.name: file_intervals},
            batch_writer, checkpoint, memory_monitor
        )
        
        if success:
            processed_count += 1
            total_seizure_windows += seizure_count
            total_background_windows += background_count
            
            logger.info(f"  ✓ Seizure windows: {seizure_count}, Background: {background_count}")
            logger.info(f"  Running totals - Seizures: {total_seizure_windows:,}, Background: {total_background_windows:,}")
            logger.info(f"  Total rows written: {batch_writer.row_count:,}")
            
            # Log entropy failure rates
            for feature in ['sample_entropy', 'perm_entropy', 'spectral_entropy']:
                rate = entropy_monitor.get_failure_rate(feature)
                if rate > 0.01:  # >1% failure rate
                    logger.warning(f"  {feature} failure rate: {rate:.2%}")
        else:
            failed_files.append(edf_path.name)
            checkpoint.failed_files.add(str(edf_path))
            logger.error(f"  ✗ Failed to process {edf_path.name}")
        
        # Progress logging every 10 files
        if idx % 10 == 0:
            elapsed = time.time() - start_time
            mem = psutil.virtual_memory()
            logger.info(f"Progress: {idx}/{len(pending_files)} files, "
                       f"Rows: {batch_writer.row_count:,}, "
                       f"Time: {elapsed/60:.1f} min, "
                       f"Memory: {mem.percent:.0f}%")
    
    # Finalize
    logger.info("Finalizing batch writer...")
    batch_writer.close()
    
    # Write failed files log
    if failed_files:
        with open(FAILED_EDF_LOG, 'w') as f:
            f.write(f"Failed EDF files - {datetime.now()}\n")
            f.write("=" * 60 + "\n")
            f.write("\n".join(failed_files))
        logger.warning(f"Failed EDF files logged to {FAILED_EDF_LOG}")
    
    # Validate output
    if OUTPUT_PATH.exists():
        validation_passed = validate_output_dataset(OUTPUT_PATH)
        if not validation_passed:
            logger.error("Output dataset validation FAILED!")
            return
    else:
        logger.error(f"Output file not created: {OUTPUT_PATH}")
        return
    
    # Final statistics
    total_rows = batch_writer.row_count
    execution_time = time.time() - start_time
    output_size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024) if OUTPUT_PATH.exists() else 0
    
    logger.info("=" * 80)
    logger.info("PROCESSING COMPLETE")
    logger.info("=" * 80)
    logger.info(f"EDF processed successfully: {processed_count}")
    logger.info(f"EDF failed: {len(failed_files)}")
    logger.info(f"Total rows: {total_rows:,}")
    logger.info(f"Seizure windows: {total_seizure_windows:,}")
    logger.info(f"Background windows: {total_background_windows:,}")
    logger.info(f"Feature count: {EXPECTED_FEATURE_COUNT}")
    logger.info(f"Output file: {OUTPUT_PATH}")
    logger.info(f"Output size: {output_size_mb:.2f} MB")
    logger.info(f"Execution time: {execution_time/60:.2f} minutes")
    logger.info(f"Processing rate: {total_rows / max(1, execution_time):.1f} rows/second")
    
    # Entropy failure summary
    logger.info("\nEntropy Computation Statistics:")
    for feature in ['sample_entropy', 'perm_entropy', 'spectral_entropy']:
        rate = entropy_monitor.get_failure_rate(feature)
        total = entropy_monitor.total_attempts.get(feature, 0)
        failures = entropy_monitor.failure_counts.get(feature, 0)
        logger.info(f"  {feature}: {failures:,}/{total:,} failures ({rate:.2%})")
    
    logger.info("=" * 80)
    logger.info("Phase 4 Production Build Complete!")
    logger.info(f"Dataset ready for training at: {OUTPUT_PATH}")
    
    # Final checkpoint save
    checkpoint.save(CHECKPOINT_DIR)
    logger.info(f"Final checkpoint saved to {CHECKPOINT_DIR}")

if __name__ == "__main__":
    main()