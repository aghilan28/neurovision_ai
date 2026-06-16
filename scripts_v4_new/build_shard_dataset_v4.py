#!/usr/bin/env python3
"""
NeuroVision Omega - Phase 4 Production Dataset Builder
SHARD-BASED ARCHITECTURE - CRASH RECOVERY GUARANTEED
================================================================================
DESIGN PRINCIPLES:
1. One EDF = One Parquet shard
2. Source of truth = shard files, NOT checkpoint
3. Validation BEFORE marking complete
4. Automatic crash recovery via directory scan
5. No data loss on interruption or restart
================================================================================
"""

import json
import gc
import time
import warnings
import logging
import traceback
import shutil
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
from scipy.integrate import trapezoid
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import pyarrow as pa
import pyarrow.parquet as pq

# Suppress warnings
warnings.filterwarnings("ignore")
mne.set_log_level("ERROR")

# ============================================================================
# PRODUCTION CONSTANTS
# ============================================================================

PROJECT_ROOT = Path(r"E:\Project\neurovision_ai")
DATASET_ROOT = Path(r"E:\NeuroVision\datasets\chbmit")
SEIZURE_DB_PATH = PROJECT_ROOT / "SEIZURE_INTERVAL_DATABASE.json"

# SHARD STORAGE - SOURCE OF TRUTH
SHARD_DIR = PROJECT_ROOT / "real_feature_dataset_v4_shards"
SHARD_DIR.mkdir(parents=True, exist_ok=True)

# Checkpoint is SECONDARY (only for resuming partial EDF processing)
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints_v4"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

# Logs
LOG_FILE = PROJECT_ROOT / "v4_production.log"
FAILED_EDF_LOG = PROJECT_ROOT / "FAILED_EDF_LOG_v4.txt"
VALIDATION_LOG = PROJECT_ROOT / "VALIDATION_LOG_v4.txt"
CORRUPTED_LOG = PROJECT_ROOT / "CORRUPTED_SHARDS_v4.txt"

# Window configuration - MATCHES V1-V3 EXACTLY
WINDOW_LENGTH_SEC = 4.0
STRIDE_SEC = 2.0

# Production settings
MAX_WORKERS = 4
RETRY_ATTEMPTS = 3
RETRY_DELAY_SEC = 2
MEMORY_THRESHOLD_PERCENT = 85.0

# Frequency bands
FREQ_BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 45.0)
}

WAVELET_NAME = "db4"
WAVELET_LEVEL = 5
MIN_WAVELET_SAMPLES = 2 ** WAVELET_LEVEL

# Base features (per channel)
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
EXPECTED_FEATURE_COUNT = len(BASE_FEATURES) * len(AGGREGATIONS)  # 96
EXPECTED_TOTAL_COLUMNS = EXPECTED_FEATURE_COUNT + 3  # + label, patient, edf = 99

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Configure production logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [%(levelname)s] - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, mode='a'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================================
# ENTROPY MONITORING
# ============================================================================

class EntropyFailureMonitor:
    """Monitor entropy computation failures"""
    def __init__(self):
        self.failure_counts = defaultdict(int)
        self.total_attempts = defaultdict(int)
    
    def record_failure(self, feature_name: str):
        self.failure_counts[feature_name] += 1
    
    def record_attempt(self, feature_name: str):
        self.total_attempts[feature_name] += 1
    
    def get_failure_rate(self, feature_name: str) -> float:
        total = self.total_attempts.get(feature_name, 1)
        return self.failure_counts.get(feature_name, 0) / total

entropy_monitor = EntropyFailureMonitor()

def safe_entropy_func(func, data, feature_name: str, *args, **kwargs) -> float:
    """Safely compute entropy with monitoring"""
    entropy_monitor.record_attempt(feature_name)
    try:
        result = func(data, *args, **kwargs)
        if np.isnan(result) or np.isinf(result):
            entropy_monitor.record_failure(feature_name)
            return 0.0
        return float(result)
    except Exception:
        entropy_monitor.record_failure(feature_name)
        return 0.0

# ============================================================================
# FEATURE EXTRACTION FUNCTIONS
# ============================================================================

def compute_time_features(signal: np.ndarray) -> Dict[str, float]:
    """Extract time-domain features"""
    signal_f32 = signal.astype(np.float32)
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
    
    signal_f64 = signal_f32.astype(np.float64)
    percentiles = np.percentile(signal_f64, [25, 75])
    features["iqr"] = float(percentiles[1] - percentiles[0])
    features["mad"] = float(np.median(np.abs(signal_f64 - np.median(signal_f64))))
    
    return features

def compute_entropy_features(signal: np.ndarray, sfreq: float) -> Dict[str, float]:
    """Extract entropy-based features"""
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

def compute_wavelet_features(signal: np.ndarray) -> Dict[str, float]:
    """Extract wavelet energy with adaptive level selection"""
    features = {}
    signal_length = len(signal)
    max_level = int(np.log2(signal_length)) - 1 if signal_length > 4 else 1
    actual_level = min(WAVELET_LEVEL, max_level)
    
    if actual_level < 1 or signal_length < MIN_WAVELET_SAMPLES:
        for i in range(WAVELET_LEVEL + 1):
            features[f"wavelet_energy_{i}"] = 0.0
        return features
    
    try:
        coeffs = pywt.wavedec(signal, WAVELET_NAME, level=actual_level)
        for i, coeff in enumerate(coeffs):
            energy = np.sum(coeff ** 2)
            features[f"wavelet_energy_{i}"] = float(energy) if not np.isnan(energy) else 0.0
        for i in range(actual_level + 1, WAVELET_LEVEL + 1):
            features[f"wavelet_energy_{i}"] = 0.0
    except Exception:
        for i in range(WAVELET_LEVEL + 1):
            features[f"wavelet_energy_{i}"] = 0.0
    
    return features

def compute_spectral_features(signal: np.ndarray, sfreq: float) -> Dict[str, float]:
    """Extract spectral features"""
    signal_f32 = signal.astype(np.float32)
    n = len(signal_f32)
    window = np.hanning(n)
    signal_windowed = signal_f32 * window
    
    nperseg = min(256, n // 2)
    if nperseg < 4:
        nperseg = n
    
    freqs, psd = welch(signal_windowed, fs=sfreq, nperseg=nperseg, noverlap=None)
    
    features = {}
    band_powers = {}
    total_power = 1e-12
    
    for band_name, (low, high) in FREQ_BANDS.items():
        mask = (freqs >= low) & (freqs < high)
        if np.any(mask):
            band_power = trapezoid(psd[mask], freqs[mask])
        else:
            band_power = 0.0
        band_powers[band_name] = band_power
        features[f"{band_name}_power"] = float(np.log1p(band_power))
        total_power += band_power
    
    for band_name in FREQ_BANDS.keys():
        power = band_powers[band_name]
        relative = power / total_power if total_power > 1e-10 else 0.0
        features[f"{band_name}_relative"] = float(np.clip(relative, 0.0, 1.0))
    
    return features

def extract_channel_features(signal: np.ndarray, sfreq: float) -> Dict[str, float]:
    """Extract all features from a single channel"""
    features = {}
    features.update(compute_time_features(signal))
    signal_f64 = signal.astype(np.float64)
    features.update(compute_entropy_features(signal_f64, sfreq))
    features.update(compute_fractal_features(signal_f64))
    features.update(compute_wavelet_features(signal_f64))
    features.update(compute_spectral_features(signal_f64, sfreq))
    
    for base_feature in BASE_FEATURES:
        if base_feature not in features:
            features[base_feature] = 0.0
    
    return features

def aggregate_channel_features(channel_features_list: List[Dict[str, float]]) -> Dict[str, float]:
    """Aggregate features across channels"""
    if not channel_features_list:
        aggregated = {}
        for feature_name in BASE_FEATURES:
            for agg in AGGREGATIONS:
                aggregated[f"{feature_name}_{agg}"] = 0.0
        return aggregated
    
    aggregated = {}
    for feature_name in BASE_FEATURES:
        values = [ch.get(feature_name, 0.0) for ch in channel_features_list if feature_name in ch]
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
# EDF LOADING
# ============================================================================

def load_edf_safe(edf_path: Path) -> Optional[mne.io.Raw]:
    """Production-grade EDF loading with comprehensive error handling"""
    try:
        if not edf_path.exists():
            logger.error(f"EDF file not found: {edf_path}")
            return None
        
        if edf_path.stat().st_size == 0:
            logger.error(f"EDF file is empty: {edf_path}")
            return None
        
        raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False, stim_channel='auto')
        
        # Identify EEG channels
        eeg_keywords = ['EEG', 'C', 'F', 'P', 'O', 'T', 'FP', 'FZ', 'CZ', 'PZ', 'OZ']
        eeg_channels = []
        
        for ch in raw.ch_names:
            ch_upper = ch.upper()
            if any(keyword in ch_upper for keyword in eeg_keywords):
                eeg_channels.append(ch)
            elif ch_upper.startswith('EKG') or ch_upper.startswith('ECG'):
                continue
            elif ch_upper.startswith('EOG'):
                continue
            else:
                if len(ch) <= 4 and ch_upper.isalnum():
                    eeg_channels.append(ch)
        
        if len(eeg_channels) < 2:
            logger.warning(f"Less than 2 EEG channels found in {edf_path.name}, using all channels")
            eeg_channels = raw.ch_names
        
        if len(eeg_channels) < len(raw.ch_names):
            raw.pick_channels(eeg_channels)
        
        # Handle duplicate channel names
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
        
        # Quick validation check
        data_check = raw.get_data()[:5, :100]
        if np.any(np.isnan(data_check)) or np.any(np.isinf(data_check)):
            logger.error(f"Data contains NaN or Inf values in {edf_path.name}")
            return None
        
        return raw
        
    except Exception as e:
        logger.error(f"Failed to load {edf_path.name}: {str(e)}")
        return None

# ============================================================================
# WINDOW GENERATION
# ============================================================================

def overlaps_with_seizure(window_start: float, window_end: float, 
                          seizure_intervals: List[List[float]], epsilon: float = 1e-9) -> bool:
    """Clinical labeling: Window is positive if ANY portion overlaps seizure"""
    for s, e in seizure_intervals:
        if s >= e:
            continue
        if (window_start + epsilon) < e and (window_end - epsilon) > s:
            return True
        if abs(window_end - s) < epsilon:
            return True
        if abs(window_start - e) < epsilon:
            return True
    return False

def process_window(window_data: np.ndarray, sfreq: float) -> Dict[str, float]:
    """Process a single window and extract features"""
    n_channels = window_data.shape[0]
    channel_features = []
    
    for ch_idx in range(n_channels):
        try:
            features = extract_channel_features(window_data[ch_idx, :], sfreq)
            if features:
                channel_features.append(features)
        except Exception as e:
            logger.debug(f"Channel {ch_idx} failed: {str(e)[:50]}")
            continue
    
    if not channel_features:
        return {}
    
    return aggregate_channel_features(channel_features)

def generate_windows_from_edf(raw: mne.io.Raw, seizure_intervals: List[List[float]],
                              patient_id: str, edf_name: str) -> pd.DataFrame:
    """Generate windows and return as DataFrame"""
    sfreq = raw.info['sfreq']
    duration = raw.times[-1]
    
    window_length_samples = int(WINDOW_LENGTH_SEC * sfreq)
    stride_samples = int(STRIDE_SEC * sfreq)
    
    data = raw.get_data().astype(np.float32)
    n_samples = data.shape[1]
    
    rows = []
    
    for start_sample in range(0, n_samples - window_length_samples + 1, stride_samples):
        end_sample = start_sample + window_length_samples
        window_data = data[:, start_sample:end_sample]
        
        window_start_sec = start_sample / sfreq
        window_end_sec = end_sample / sfreq
        
        if window_start_sec >= window_end_sec or window_start_sec < 0 or window_end_sec > duration:
            continue
        
        features = process_window(window_data, sfreq)
        if not features:
            continue
        
        label = 1 if overlaps_with_seizure(window_start_sec, window_end_sec, seizure_intervals) else 0
        
        row = {
            **features,
            'label': label,
            'patient': patient_id,
            'edf': edf_name
        }
        rows.append(row)
    
    if not rows:
        return pd.DataFrame()
    
    return pd.DataFrame(rows)

# ============================================================================
# SHARD VALIDATION
# ============================================================================

def validate_shard(shard_path: Path) -> Tuple[bool, str]:
    """
    Validate a shard file for integrity.
    Returns (is_valid, error_message)
    """
    try:
        # Check file exists
        if not shard_path.exists():
            return False, "File does not exist"
        
        # Check file size > 0
        if shard_path.stat().st_size == 0:
            return False, "File is empty"
        
        # Try to read the parquet
        df = pd.read_parquet(shard_path)
        
        # Check row count > 0
        if len(df) == 0:
            return False, "No rows in shard"
        
        # Check required columns exist
        required_cols = ['label', 'patient', 'edf']
        for col in required_cols:
            if col not in df.columns:
                return False, f"Missing required column: {col}"
        
        # Check feature count
        feature_cols = [c for c in df.columns if c not in required_cols]
        if len(feature_cols) != EXPECTED_FEATURE_COUNT:
            return False, f"Feature count mismatch: {len(feature_cols)} vs {EXPECTED_FEATURE_COUNT}"
        
        # Check total column count
        if len(df.columns) != EXPECTED_TOTAL_COLUMNS:
            return False, f"Column count mismatch: {len(df.columns)} vs {EXPECTED_TOTAL_COLUMNS}"
        
        # Check for NaN/Inf in numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isna().any():
                return False, f"NaN found in column: {col}"
            if np.isinf(df[col]).any():
                return False, f"Inf found in column: {col}"
        
        return True, "Valid"
        
    except Exception as e:
        return False, f"Validation exception: {str(e)}"

def repair_shard(shard_path: Path) -> None:
    """Delete corrupted shard so it can be reprocessed"""
    if shard_path.exists():
        logger.warning(f"Deleting corrupted shard: {shard_path}")
        shard_path.unlink()
        
        # Log corruption
        with open(CORRUPTED_LOG, 'a') as f:
            f.write(f"{datetime.now()} - {shard_path.name}\n")

# ============================================================================
# SHARD PROCESSING FOR SINGLE EDF
# ============================================================================

def get_shard_path(patient_id: str, edf_name: str) -> Path:
    """Generate shard path from patient and EDF name"""
    # Remove .edf extension and create clean name
    base_name = Path(edf_name).stem
    shard_name = f"{patient_id}_{base_name}.parquet"
    return SHARD_DIR / shard_name

def process_single_edf(edf_path: Path, patient_id: str, 
                       seizure_intervals: Dict[str, List[List[float]]],
                       checkpoint: Dict[str, Any]) -> Tuple[bool, int, int, str]:
    """
    Process a single EDF file and create shard.
    Returns: (success, seizure_count, background_count, error_message)
    """
    shard_path = get_shard_path(patient_id, edf_path.name)
    
    # Step 1: Load EDF
    raw = load_edf_safe(edf_path)
    if raw is None:
        return False, 0, 0, "Failed to load EDF"
    
    # Step 2: Get seizure intervals for this file
    file_intervals = seizure_intervals.get(edf_path.name, [])
    
    # Step 3: Generate windows and extract features
    try:
        df = generate_windows_from_edf(raw, file_intervals, patient_id, edf_path.name)
    except Exception as e:
        return False, 0, 0, f"Window generation failed: {str(e)}"
    finally:
        del raw
        gc.collect()
    
    if df.empty:
        return False, 0, 0, "No windows generated"
    
    # Step 4: Write shard
    try:
        df.to_parquet(shard_path, index=False)
    except Exception as e:
        return False, 0, 0, f"Failed to write shard: {str(e)}"
    
    # Step 5-8: Verify shard
    is_valid, error_msg = validate_shard(shard_path)
    if not is_valid:
        repair_shard(shard_path)
        return False, 0, 0, f"Shard validation failed: {error_msg}"
    
    # Count windows
    seizure_count = len(df[df['label'] == 1])
    background_count = len(df[df['label'] == 0])
    
    return True, seizure_count, background_count, ""

# ============================================================================
# DISCOVERY FUNCTIONS
# ============================================================================

def scan_edf_files() -> List[Tuple[Path, str]]:
    """Scan all EDF files in the dataset"""
    edf_files = []
    expected_patients = [f"chb{str(i).zfill(2)}" for i in range(1, 25)]
    
    for patient_id in expected_patients:
        patient_dir = DATASET_ROOT / patient_id
        if not patient_dir.exists():
            logger.warning(f"Patient folder not found: {patient_id}")
            continue
        
        for edf_file in sorted(patient_dir.glob("*.edf")):
            if 'summary' in edf_file.name.lower() or 'info' in edf_file.name.lower():
                continue
            edf_files.append((edf_file, patient_id))
        
        # Also check for uppercase EDF
        for edf_file in sorted(patient_dir.glob("*.EDF")):
            if 'summary' in edf_file.name.lower() or 'info' in edf_file.name.lower():
                continue
            if (edf_file, patient_id) not in edf_files:
                edf_files.append((edf_file, patient_id))
    
    return edf_files

def find_missing_shards(edf_files: List[Tuple[Path, str]]) -> List[Tuple[Path, str]]:
    """
    Source of truth: Shard directory.
    Returns list of EDF files that still need processing.
    """
    missing = []
    
    for edf_path, patient_id in edf_files:
        shard_path = get_shard_path(patient_id, edf_path.name)
        
        if shard_path.exists():
            # Verify existing shard is valid
            is_valid, _ = validate_shard(shard_path)
            if is_valid:
                continue  # Skip - already processed and valid
            else:
                # Corrupted shard - delete and reprocess
                logger.warning(f"Found corrupted shard: {shard_path.name}, will reprocess")
                repair_shard(shard_path)
                missing.append((edf_path, patient_id))
        else:
            missing.append((edf_path, patient_id))
    
    return missing

def load_seizure_database() -> Dict[str, Dict[str, List[List[float]]]]:
    """Load and validate seizure interval database"""
    if not SEIZURE_DB_PATH.exists():
        logger.error(f"Seizure database not found: {SEIZURE_DB_PATH}")
        return {}
    
    with open(SEIZURE_DB_PATH, 'r') as f:
        db = json.load(f)
    
    logger.info(f"Loaded seizure database for {len(db)} patients")
    return db

# ============================================================================
# MEMORY MONITOR
# ============================================================================

class MemoryMonitor:
    def __init__(self, threshold_percent: float = MEMORY_THRESHOLD_PERCENT):
        self.threshold = threshold_percent
    
    def is_safe(self) -> bool:
        try:
            memory = psutil.virtual_memory()
            if memory.percent > self.threshold:
                logger.warning(f"Memory high: {memory.percent:.1f}%")
                gc.collect()
                time.sleep(1)
                return False
            return True
        except Exception:
            return True

# ============================================================================
# MAIN PROCESSING LOOP
# ============================================================================

def main():
    """Main execution with shard-based crash recovery"""
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("NEUROVISION OMEGA - PHASE 4 SHARD-BASED DATASET BUILDER")
    logger.info(f"Window: {WINDOW_LENGTH_SEC}s, Stride: {STRIDE_SEC}s")
    logger.info(f"Shard directory: {SHARD_DIR}")
    logger.info("Source of truth = SHARD FILES (NOT checkpoint)")
    logger.info("=" * 80)
    
    # Load seizure database
    seizure_db = load_seizure_database()
    if not seizure_db:
        logger.error("Failed to load seizure database. Aborting.")
        return
    
    # Scan EDF files
    logger.info("Scanning for EDF files...")
    all_edf_files = scan_edf_files()
    logger.info(f"Found {len(all_edf_files)} EDF files total")
    
    # Find missing shards (source of truth)
    pending_files = find_missing_shards(all_edf_files)
    logger.info(f"Shards already valid: {len(all_edf_files) - len(pending_files)}")
    logger.info(f"Pending EDF files: {len(pending_files)}")
    
    if not pending_files:
        logger.info("=" * 80)
        logger.info("ALL EDF FILES ALREADY PROCESSED AND VALIDATED!")
        logger.info(f"Shard directory: {SHARD_DIR}")
        logger.info("Run merge_v4_shards.py to create final dataset.")
        logger.info("=" * 80)
        return
    
    # Statistics
    total_seizure_windows = 0
    total_background_windows = 0
    processed_count = 0
    failed_files = []
    memory_monitor = MemoryMonitor()
    
    # Process each missing file
    for idx, (edf_path, patient_id) in enumerate(pending_files, 1):
        logger.info(f"[{idx}/{len(pending_files)}] Processing: {patient_id}/{edf_path.name}")
        
        memory_monitor.is_safe()
        
        # Get patient-specific intervals
        patient_intervals = seizure_db.get(patient_id, {})
        file_intervals = {edf_path.name: patient_intervals.get(edf_path.name, [])}
        
        # Process with retry
        success = False
        seizure_count = 0
        background_count = 0
        error_msg = ""
        
        for attempt in range(RETRY_ATTEMPTS):
            try:
                success, seizure_count, background_count, error_msg = process_single_edf(
                    edf_path, patient_id, file_intervals, {}
                )
                if success:
                    break
                logger.warning(f"Attempt {attempt + 1}/{RETRY_ATTEMPTS} failed: {error_msg}")
                time.sleep(RETRY_DELAY_SEC * (attempt + 1))
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} exception: {str(e)}")
                time.sleep(RETRY_DELAY_SEC * (attempt + 1))
        
        if success:
            processed_count += 1
            total_seizure_windows += seizure_count
            total_background_windows += background_count
            logger.info(f"  ✓ Seizure: {seizure_count}, Background: {background_count}, Total: {seizure_count + background_count}")
        else:
            failed_files.append((edf_path.name, patient_id, error_msg))
            logger.error(f"  ✗ FAILED: {error_msg}")
            with open(FAILED_EDF_LOG, 'a') as f:
                f.write(f"{datetime.now()} - {patient_id}/{edf_path.name}: {error_msg}\n")
        
        # Periodic progress report
        if idx % 10 == 0:
            elapsed = time.time() - start_time
            mem = psutil.virtual_memory()
            logger.info(f"--- PROGRESS: {idx}/{len(pending_files)} files, "
                       f"Seizure windows: {total_seizure_windows:,}, "
                       f"Background: {total_background_windows:,}, "
                       f"Memory: {mem.percent:.0f}%, "
                       f"Time: {elapsed/60:.1f} min ---")
        
        gc.collect()
    
    # Final summary
    elapsed = time.time() - start_time
    logger.info("=" * 80)
    logger.info("PROCESSING COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Successfully processed: {processed_count}")
    logger.info(f"Failed: {len(failed_files)}")
    logger.info(f"Total seizure windows: {total_seizure_windows:,}")
    logger.info(f"Total background windows: {total_background_windows:,}")
    logger.info(f"Total rows: {total_seizure_windows + total_background_windows:,}")
    logger.info(f"Execution time: {elapsed/60:.2f} minutes")
    logger.info(f"Shard directory: {SHARD_DIR}")
    logger.info("")
    logger.info("NEXT STEPS:")
    logger.info("1. Run merge_v4_shards.py to create final dataset")
    logger.info("2. Run audit_v4_dataset.py to validate")
    logger.info("3. Run prepare_v4_training_dataset.py for training")
    logger.info("=" * 80)
    
    # Entropy statistics
    logger.info("\nEntropy Computation Statistics:")
    for feature in ['sample_entropy', 'perm_entropy', 'spectral_entropy']:
        rate = entropy_monitor.get_failure_rate(feature)
        total = entropy_monitor.total_attempts.get(feature, 0)
        failures = entropy_monitor.failure_counts.get(feature, 0)
        logger.info(f"  {feature}: {failures:,}/{total:,} failures ({rate:.2%})")

if __name__ == "__main__":
    main()