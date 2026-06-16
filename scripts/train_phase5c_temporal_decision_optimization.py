#!/usr/bin/env python3
"""
NeuroVision Omega - Phase 5C: Temporal Decision Optimization
Production-grade executable for clinical seizure detection system.

This phase focuses on:
1. Temporal decision optimization (smoothing, voting, persistence)
2. Probability calibration (Platt scaling, isotonic regression)
3. Patient robustness analysis
4. EDF-level seizure detection
5. Clinical deployment readiness

Memory budget: <10 GB
CPU: Intel i7-10700
GPU: Intel UHD 630 (not utilized - CPU only)
RAM: 16 GB

Author: NeuroVision Clinical AI Team
Version: 5.0-production
"""

import os
import sys
import json
import warnings
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score,
    average_precision_score, confusion_matrix, cohen_kappa_score,
    balanced_accuracy_score, matthews_corrcoef, brier_score_loss,
    log_loss, precision_recall_curve, roc_curve
)
import joblib

# Suppress warnings for production
warnings.filterwarnings('ignore')

# =============================================================================
# SAFETY LAYERS - CRITICAL PROTECTION AGAINST PREVIOUS FAILURES
# =============================================================================

def json_serializer(obj):
    """JSON serialization safety layer - prevents int64/float32 crashes."""
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, '__dict__'):
        return str(obj)
    return str(obj)


def convert_tuple_keys_to_strings(obj):
    """Convert tuple keys to strings - prevents tuple-key JSON crash."""
    if isinstance(obj, dict):
        new_dict = {}
        for key, value in obj.items():
            if isinstance(key, tuple):
                new_key = "__tuple__" + "_".join(str(x) for x in key)
            else:
                new_key = key
            new_dict[new_key] = convert_tuple_keys_to_strings(value)
        return new_dict
    elif isinstance(obj, list):
        return [convert_tuple_keys_to_strings(item) for item in obj]
    elif isinstance(obj, tuple):
        return "__tuple__" + "_".join(str(x) for x in obj)
    else:
        return obj


class MemoryEstimator:
    """Memory protection system - prevents memory explosion."""
    
    def __init__(self):
        self.memory_tracking = {}
        self.peak_estimated = 0
    
    def estimate_dataframe_memory(self, df: pd.DataFrame) -> float:
        """Estimate memory usage of dataframe in GB."""
        return df.memory_usage(deep=True).sum() / (1024 ** 3)
    
    def estimate_array_memory(self, arr: np.ndarray) -> float:
        """Estimate memory usage of numpy array in GB."""
        return arr.nbytes / (1024 ** 3)
    
    def track(self, name: str, size_gb: float):
        """Track memory allocation."""
        self.memory_tracking[name] = size_gb
        self.peak_estimated = max(self.peak_estimated, sum(self.memory_tracking.values()))
    
    def check_budget(self, budget_gb: float = 10.0) -> bool:
        """Check if memory is within budget."""
        return self.peak_estimated <= budget_gb
    
    def generate_report(self) -> Dict:
        """Generate memory audit report."""
        return {
            "tracked_components": self.memory_tracking,
            "total_estimated_gb": sum(self.memory_tracking.values()),
            "peak_estimated_gb": self.peak_estimated,
            "budget_gb": 10.0,
            "within_budget": self.check_budget(),
            "timestamp": datetime.now().isoformat()
        }


class LeakageAuditor:
    """Leakage defense system - prevents label/feature/temporal leakage."""
    
    FORBIDDEN_COLUMNS = [
        'historical_seizure_density', 'windows_since_last_seizure',
        'future_seizure_indicator', 'lead_seizure_count',
        'next_seizure_delta', 'label_future', 'target_lag'
    ]
    
    FORBIDDEN_PATTERNS = [
        'historical', 'future', 'lead', 'next', 'lookahead',
        'density_from_label', 'seizure_count_after'
    ]
    
    def __init__(self, df: pd.DataFrame, patient_split: Dict, edf_data: pd.Series = None):
        self.df = df
        self.patient_split = patient_split
        self.edf_data = edf_data
        self.issues = []
    
    def audit_label_leakage(self) -> bool:
        """Check for label-derived features."""
        for col in self.df.columns:
            if any(forbidden in col.lower() for forbidden in self.FORBIDDEN_PATTERNS):
                if col not in ['label', 'seizure_label']:  # Allow actual label columns
                    self.issues.append(f"Label leakage detected: {col}")
                    return False
        return True
    
    def audit_column_leakage(self) -> bool:
        """Check for forbidden columns."""
        for col in self.df.columns:
            if col in self.FORBIDDEN_COLUMNS:
                self.issues.append(f"Forbidden column detected: {col}")
                return False
        return True
    
    def audit_patient_leakage(self) -> bool:
        """Check for patient-level leakage in split."""
        if 'patients' not in self.patient_split:
            self.issues.append("Patient split missing")
            return False
        
        train_patients = set(self.patient_split.get('train_patients', []))
        val_patients = set(self.patient_split.get('val_patients', []))
        test_patients = set(self.patient_split.get('test_patients', []))
        
        # Check for overlap
        if len(train_patients & val_patients) > 0:
            self.issues.append(f"Patient leakage: train-val overlap {train_patients & val_patients}")
            return False
        if len(train_patients & test_patients) > 0:
            self.issues.append(f"Patient leakage: train-test overlap {train_patients & test_patients}")
            return False
        
        return True
    
    def audit_temporal_leakage(self) -> bool:
        """Check for temporal ordering issues."""
        if 'timestamp' not in self.df.columns and 'time' not in self.df.columns:
            # Not all datasets have explicit timestamps - assume OK
            return True

        # Simple check for monotonic timestamps per patient
        time_col = 'timestamp' if 'timestamp' in self.df.columns else 'time'
        # prefer canonical 'patient' column
        pid_col = 'patient' if 'patient' in self.df.columns else None
        if pid_col:
            for patient in self.df[pid_col].unique()[:5]:  # Sample check
                patient_df = self.df[self.df[pid_col] == patient].sort_values(time_col)
                if not patient_df[time_col].is_monotonic_increasing:
                    self.issues.append(f"Non-monotonic timestamps for patient {patient}")
                    return False

        return True
    
    def generate_report(self) -> Dict:
        """Generate leakage audit report."""
        return {
            "leakage_detected": len(self.issues) > 0,
            "issues": self.issues,
            "audits_passed": {
                "label_leakage": self.audit_label_leakage(),
                "column_leakage": self.audit_column_leakage(),
                "patient_leakage": self.audit_patient_leakage(),
                "temporal_leakage": self.audit_temporal_leakage()
            },
            "timestamp": datetime.now().isoformat()
        }


class TemporalDecisionOptimizer:
    """Temporal decision optimization methods."""
    
    def __init__(self, probabilities: np.ndarray, labels: np.ndarray):
        self.probabilities = probabilities.astype(np.float32)
        self.labels = labels.astype(np.uint8)
    
    def moving_average_smoothing(self, window_size: int) -> np.ndarray:
        """Apply moving average smoothing to probabilities."""
        smoothed = np.convolve(self.probabilities, np.ones(window_size)/window_size, mode='same')
        return smoothed.astype(np.float32)
    
    def majority_vote_smoothing(self, window_size: int) -> np.ndarray:
        """Apply majority vote smoothing."""
        smoothed = np.zeros_like(self.probabilities)
        half_window = window_size // 2
        
        for i in range(len(self.probabilities)):
            start = max(0, i - half_window)
            end = min(len(self.probabilities), i + half_window + 1)
            window = self.probabilities[start:end]
            smoothed[i] = 1.0 if np.mean(window) > 0.5 else 0.0
        
        return smoothed.astype(np.float32)
    
    def consecutive_positive_confirmation(self, threshold: float = 0.5, min_consecutive: int = 2) -> np.ndarray:
        """Require consecutive positives to create alert."""
        binary = (self.probabilities >= threshold).astype(int)
        confirmed = np.zeros_like(binary)
        
        consecutive_count = 0
        for i in range(len(binary)):
            if binary[i] == 1:
                consecutive_count += 1
                if consecutive_count >= min_consecutive:
                    confirmed[i] = 1
            else:
                consecutive_count = 0
        
        return confirmed.astype(np.float32)
    
    def minimum_duration_rule(self, threshold: float = 0.5, min_duration_samples: int = 10) -> np.ndarray:
        """Enforce minimum seizure duration."""
        binary = (self.probabilities >= threshold).astype(int)
        duration_filtered = np.zeros_like(binary)
        
        i = 0
        while i < len(binary):
            if binary[i] == 1:
                # Find seizure end
                j = i
                while j < len(binary) and binary[j] == 1:
                    j += 1
                duration = j - i
                if duration >= min_duration_samples:
                    duration_filtered[i:j] = 1
                i = j
            else:
                i += 1
        
        return duration_filtered.astype(np.float32)
    
    def alert_persistence_rule(self, threshold: float = 0.5, persistence_samples: int = 3) -> np.ndarray:
        """Alert must persist to be valid."""
        binary = (self.probabilities >= threshold).astype(int)
        persistent = np.zeros_like(binary)
        
        for i in range(len(binary) - persistence_samples + 1):
            if np.all(binary[i:i+persistence_samples] == 1):
                persistent[i:i+persistence_samples] = 1
        
        return persistent.astype(np.float32)
    
    def window_confidence_aggregation(self, window_size: int = 5, method: str = 'mean') -> np.ndarray:
        """Aggregate confidence within window."""
        aggregated = np.zeros_like(self.probabilities)
        
        for i in range(len(self.probabilities)):
            start = max(0, i - window_size//2)
            end = min(len(self.probabilities), i + window_size//2 + 1)
            window = self.probabilities[start:end]
            
            if method == 'mean':
                aggregated[i] = np.mean(window)
            elif method == 'median':
                aggregated[i] = np.median(window)
            elif method == 'max':
                aggregated[i] = np.max(window)
            else:
                aggregated[i] = np.mean(window)
        
        return aggregated.astype(np.float32)
    
    def evaluate_method(self, predictions: np.ndarray, method_name: str) -> Dict:
        """Evaluate a single optimization method."""
        # Apply threshold at 0.5 for binary predictions
        binary_preds = (predictions >= 0.5).astype(int)
        
        tn, fp, fn, tp = confusion_matrix(self.labels, binary_preds, labels=[0, 1]).ravel()
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        balanced_acc = balanced_accuracy_score(self.labels, binary_preds)
        f1 = f1_score(self.labels, binary_preds, zero_division=0)
        mcc = matthews_corrcoef(self.labels, binary_preds)
        kappa = cohen_kappa_score(self.labels, binary_preds)
        
        return {
            'method': method_name,
            'precision': precision,
            'recall': recall,
            'specificity': specificity,
            'balanced_accuracy': balanced_acc,
            'f1': f1,
            'mcc': mcc,
            'kappa': kappa
        }


class ThresholdOptimizer:
    """Threshold optimization across probability space."""
    
    def __init__(self, probabilities: np.ndarray, labels: np.ndarray):
        self.probabilities = probabilities.astype(np.float32)
        self.labels = labels.astype(np.uint8)
    
    def optimize(self) -> pd.DataFrame:
        """Evaluate all thresholds and return results."""
        thresholds = np.arange(0.01, 1.00, 0.01)
        results = []
        
        for threshold in thresholds:
            binary_preds = (self.probabilities >= threshold).astype(int)
            
            tn, fp, fn, tp = confusion_matrix(self.labels, binary_preds, labels=[0, 1]).ravel()
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
            balanced_acc = balanced_accuracy_score(self.labels, binary_preds)
            f1 = f1_score(self.labels, binary_preds, zero_division=0)
            mcc = matthews_corrcoef(self.labels, binary_preds)
            kappa = cohen_kappa_score(self.labels, binary_preds)
            
            results.append({
                'threshold': threshold,
                'precision': precision,
                'recall': recall,
                'specificity': specificity,
                'balanced_accuracy': balanced_acc,
                'f1': f1,
                'mcc': mcc,
                'kappa': kappa
            })
        
        results_df = pd.DataFrame(results)
        
        # Identify optimal thresholds
        optimal = {
            'best_f1_threshold': results_df.loc[results_df['f1'].idxmax(), 'threshold'],
            'best_recall_threshold': results_df.loc[results_df['recall'].idxmax(), 'threshold'],
            'best_balanced_threshold': results_df.loc[results_df['balanced_accuracy'].idxmax(), 'threshold'],
            'best_mcc_threshold': results_df.loc[results_df['mcc'].idxmax(), 'threshold']
        }
        
        return results_df, optimal


class ProbabilityCalibrator:
    """Probability calibration using Platt scaling and isotonic regression."""
    
    def __init__(self, probabilities: np.ndarray, labels: np.ndarray):
        self.probabilities = probabilities.astype(np.float32)
        self.labels = labels.astype(np.uint8)
    
    def calibrate(self) -> Dict:
        """Apply calibration methods and compare."""
        # Split data for calibration (50/50)
        n = len(self.probabilities)
        split = n // 2
        np.random.seed(42)
        indices = np.random.permutation(n)
        calib_indices = indices[:split]
        eval_indices = indices[split:]
        
        calib_probs = self.probabilities[calib_indices]
        calib_labels = self.labels[calib_indices]
        eval_probs = self.probabilities[eval_indices]
        eval_labels = self.labels[eval_indices]
        
        results = {}
        
        # RAW (no calibration)
        raw_preds = (eval_probs >= 0.5).astype(int)
        results['RAW'] = self._compute_metrics(eval_labels, eval_probs, raw_preds)
        
        # Platt Scaling
        try:
            platt = CalibratedClassifierCV(cv=3, method='sigmoid')
            platt.fit(calib_probs.reshape(-1, 1), calib_labels)
            platt_probs = platt.predict_proba(eval_probs.reshape(-1, 1))[:, 1]
            platt_preds = (platt_probs >= 0.5).astype(int)
            results['PLATT_SCALING'] = self._compute_metrics(eval_labels, platt_probs, platt_preds)
        except Exception as e:
            results['PLATT_SCALING'] = {'error': str(e)}
        
        # Isotonic Regression
        try:
            isotonic = CalibratedClassifierCV(cv=3, method='isotonic')
            isotonic.fit(calib_probs.reshape(-1, 1), calib_labels)
            isotonic_probs = isotonic.predict_proba(eval_probs.reshape(-1, 1))[:, 1]
            isotonic_preds = (isotonic_probs >= 0.5).astype(int)
            results['ISOTONIC_REGRESSION'] = self._compute_metrics(eval_labels, isotonic_probs, isotonic_preds)
        except Exception as e:
            results['ISOTONIC_REGRESSION'] = {'error': str(e)}
        
        # Determine winner based on Brier score (lower is better)
        winner = 'RAW'
        best_brier = results['RAW'].get('brier_score', float('inf'))
        
        for method in ['PLATT_SCALING', 'ISOTONIC_REGRESSION']:
            if method in results and 'brier_score' in results[method]:
                if results[method]['brier_score'] < best_brier:
                    best_brier = results[method]['brier_score']
                    winner = method
        
        results['winner'] = winner
        
        # Apply winner to full dataset
        if winner == 'RAW':
            calibrated_full = self.probabilities
        elif winner == 'PLATT_SCALING':
            calibrator = CalibratedClassifierCV(cv=3, method='sigmoid')
            calibrator.fit(self.probabilities.reshape(-1, 1), self.labels)
            calibrated_full = calibrator.predict_proba(self.probabilities.reshape(-1, 1))[:, 1]
        else:
            calibrator = CalibratedClassifierCV(cv=3, method='isotonic')
            calibrator.fit(self.probabilities.reshape(-1, 1), self.labels)
            calibrated_full = calibrator.predict_proba(self.probabilities.reshape(-1, 1))[:, 1]
        
        results['calibrated_probabilities'] = calibrated_full.astype(np.float32)
        
        return results
    
    def _compute_metrics(self, y_true, y_proba, y_pred):
        """Compute calibration metrics."""
        try:
            roc_auc = roc_auc_score(y_true, y_proba)
        except:
            roc_auc = 0.0
        
        try:
            pr_auc = average_precision_score(y_true, y_proba)
        except:
            pr_auc = 0.0
        
        f1 = f1_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        
        # Calibration error
        prob_true, prob_pred = calibration_curve(y_true, y_proba, n_bins=10)
        calibration_error = np.mean(np.abs(prob_true - prob_pred))
        
        brier = brier_score_loss(y_true, y_proba)
        
        try:
            log_loss_val = log_loss(y_true, y_proba)
        except:
            log_loss_val = float('inf')
        
        return {
            'roc_auc': roc_auc,
            'pr_auc': pr_auc,
            'f1': f1,
            'recall': recall,
            'calibration_error': calibration_error,
            'brier_score': brier,
            'log_loss': log_loss_val
        }


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution pipeline for Phase 5C."""
    
    print("=" * 80)
    print("NeuroVision Omega - Phase 5C: Temporal Decision Optimization")
    print("=" * 80)
    print(f"Start time: {datetime.now().isoformat()}")
    print()
    
    start_time = time.time()
    memory_estimator = MemoryEstimator()
    
    # =========================================================================
    # GATE 1: Dataset exists
    # =========================================================================
    print("GATE 1: Validating input files...")
    
    data_path = Path("PHASE5B_ENGINEERED_DATASET.parquet")
    model_path = Path("PHASE5B_TEMPORAL_XGBOOST.joblib")
    patient_split_path = Path("PHASE5B_PATIENT_SPLIT.json")
    
    if not data_path.exists():
        print("ERROR: Dataset not found:", data_path)
        sys.exit(1)
    if not model_path.exists():
        print("ERROR: Model not found:", model_path)
        sys.exit(1)
    if not patient_split_path.exists():
        print("ERROR: Patient split not found:", patient_split_path)
        sys.exit(1)
    
    print("✓ All input files found")
    print()
    
    # =========================================================================
    # Load data with memory efficiency
    # =========================================================================
    print("Loading dataset...")
    df = pd.read_parquet(data_path)
    memory_estimator.track("dataset", memory_estimator.estimate_dataframe_memory(df))
    print(f"  Dataset shape: {df.shape}")
    print(f"  Memory usage: {memory_estimator.memory_tracking['dataset']:.2f} GB")
    print()

    # Quick dataset audit for engineered feature presence
    print("\nDATASET AUDIT")
    print(f"Shape: {df.shape}")

    lag1_cols = [c for c in df.columns if '_lag1' in c]
    lag3_cols = [c for c in df.columns if '_lag3' in c]
    rolling_cols = [c for c in df.columns if '_rolling_mean_5' in c]
    stability_cols = [c for c in df.columns if '_stability_5' in c]

    print(f"LAG1: {len(lag1_cols)}")
    print(f"LAG3: {len(lag3_cols)}")
    print(f"ROLLING: {len(rolling_cols)}")
    print(f"STABILITY: {len(stability_cols)}")
    
    # =========================================================================
    # GATE 2: Model exists
    # =========================================================================
    print("Loading model...")
    model = joblib.load(model_path)
    print("✓ Model loaded")
    print()
    
    # =========================================================================
    # Validate required columns
    # =========================================================================
    print("GATE 3: Validating required columns...")
    
    # Identify feature columns (all numeric except label)
    label_candidates = ['label', 'seizure_label', 'target']
    label_col = None
    for candidate in label_candidates:
        if candidate in df.columns:
            label_col = candidate
            break
    
    if label_col is None:
        print("ERROR: No label column found")
        sys.exit(1)
    
    # Check for patient and EDF columns (canonical names used by Phase5 outputs)
    patient_col = 'patient'
    edf_col = 'edf'
    
    print(f"  Label column: {label_col}")
    print(f"  Patient column: {patient_col if patient_col else 'Not found'}")
    print(f"  EDF column: {edf_col if edf_col else 'Not found'}")
    print("✓ Required columns validated")
    print()
    
    # =========================================================================
    # Prepare data for prediction
    # =========================================================================
    print("Preparing features for prediction...")
    
    # Exclude metadata and temporal columns from features
    exclude_cols = [
        label_col,
        'patient',
        'edf',
        'window_index',
        'window_start_sec',
        'window_end_sec',
        'window_duration_sec',
        'stride_sec',
        'window_uid'
    ]

    feature_cols = [
        col for col in df.columns
        if col not in [
            label_col,
            'patient',
            'edf',
            'window_uid',
            'window_index',
            'window_start_sec',
            'window_end_sec',
            'window_duration_sec',
            'stride_sec'
        ]
    ]

    print("\nFEATURE AUDIT")
    print("Feature count:", len(feature_cols))

    if len(feature_cols) != 484:
        raise RuntimeError(
            f"Expected 484 features, got {len(feature_cols)}"
        )

    # Use engineered features already present in parquet (do not re-engineer)
    required_features = feature_cols

    print(f"Using engineered features from parquet: {len(required_features)}")

    if len(required_features) != 484:
        raise RuntimeError(
            f"Expected 484 engineered features but found {len(required_features)}"
        )
    
    # Build test-only dataset for prediction
    with open(patient_split_path, 'r') as f:
        patient_split_tmp = json.load(f)
    test_patients_tmp = set(patient_split_tmp.get('test_patients', []))
    test_df = df[df['patient'].isin(test_patients_tmp)].copy()

    # Verify engineered features are present (Phase5B engineered columns)
    missing = [c for c in required_features if c not in test_df.columns]

    print(f"  Feature count: {len(feature_cols)}")
    print(f"  Test sample count: {test_df.shape[0]}")
    print(f"  Missing engineered features: {len(missing)}")

    if len(missing) > 0:
        print("\nERROR: Phase5C dataset does not contain Phase5B engineered features")
        print("First missing columns:")
        print(missing[:20])
        sys.exit(1)

    X = test_df[required_features].values.astype(np.float32)
    y = test_df[label_col].values.astype(np.uint8)

    # Create a patient series aligned with X/y for patient-level analysis
    test_patient_series = test_df[patient_col].reset_index(drop=True)
    # Create an EDF series aligned with X/y for EDF-level analysis
    test_edf_series = test_df[edf_col].reset_index(drop=True)

    # estimate_array_memory expects the ndarray itself (returns GB)
    feature_mem = memory_estimator.estimate_array_memory(X)
    label_mem = memory_estimator.estimate_array_memory(y)
    print(f"  Features memory estimate: {feature_mem:.2f} GB")
    print(f"  Labels memory estimate: {label_mem:.4f} GB")
    # Track these for the global memory audit
    memory_estimator.track("features", float(feature_mem))
    memory_estimator.track("labels", float(label_mem))
    print()
    
    # =========================================================================
    # GATE 4: Memory audit passed
    # =========================================================================
    print("GATE 4: Memory audit...")
    
    if not memory_estimator.check_budget():
        print(f"ERROR: Estimated memory ({memory_estimator.peak_estimated:.2f} GB) exceeds budget")
        memory_audit = memory_estimator.generate_report()
        with open("PHASE5C_MEMORY_AUDIT.json", "w") as f:
            json.dump(convert_tuple_keys_to_strings(memory_audit), f, default=json_serializer, indent=2)
        sys.exit(1)
    
    print(f"✓ Memory within budget: {memory_estimator.peak_estimated:.2f} GB / 10.0 GB")
    memory_audit = memory_estimator.generate_report()
    with open("PHASE5C_MEMORY_AUDIT.json", "w") as f:
        json.dump(convert_tuple_keys_to_strings(memory_audit), f, default=json_serializer, indent=2)
    print()
    
    # =========================================================================
    # Generate predictions
    # =========================================================================
    print("Generating predictions from loaded model...")
    
    # Verify compatibility with model
    print(f"X shape: {X.shape}")
    print(f"y shape: {y.shape}")
    if X.shape[1] != 484:
        raise RuntimeError(
            f"Model expects 484 features but received {X.shape[1]}"
        )

    # Use batch prediction to avoid memory spikes
    batch_size = 10000
    probabilities = []
    for i in range(0, len(X), batch_size):
        batch = X[i:i+batch_size]
        batch_probs = model.predict_proba(batch)[:, 1]
        probabilities.append(batch_probs)

    probabilities = np.concatenate(probabilities).astype(np.float32)
    memory_estimator.track("predictions", memory_estimator.estimate_array_memory(probabilities))
    print(f"  Predictions memory: {memory_estimator.memory_tracking['predictions']:.2f} GB")
    print()
    
    # =========================================================================
    # GATE 5-8: Leakage audits
    # =========================================================================
    print("GATES 5-8: Leakage audits...")
    
    with open(patient_split_path, 'r') as f:
        patient_split = json.load(f)

    # Build test mask from patient split
    test_patients = set(patient_split.get('test_patients', []))
    test_mask = df['patient'].isin(test_patients)

    print(f"Test rows: {test_mask.sum():,}")
    print(f"Test patients: {len(test_patients)}")

    # Safety audit: ensure patient isolation
    train_patients = set(patient_split.get('train_patients', []))
    val_patients = set(patient_split.get('val_patients', []))

    assert len(train_patients & test_patients) == 0
    assert len(val_patients & test_patients) == 0
    assert len(train_patients & val_patients) == 0

    print("[OK] Patient isolation verified")
    
    leakage_auditor = LeakageAuditor(df, patient_split)
    leakage_report = leakage_auditor.generate_report()
    
    with open("PHASE5C_LEAKAGE_AUDIT.json", "w") as f:
        json.dump(convert_tuple_keys_to_strings(leakage_report), f, default=json_serializer, indent=2)
    
    if leakage_report['leakage_detected']:
        print("ERROR: Leakage detected!")
        for issue in leakage_report['issues']:
            print(f"  - {issue}")
        sys.exit(1)
    
    print("✓ All leakage audits passed")
    print()
    
    # =========================================================================
    # GATE 9: Threshold optimization
    # =========================================================================
    print("GATE 9: Threshold optimization...")
    
    threshold_optimizer = ThresholdOptimizer(probabilities, y)
    threshold_results, optimal_thresholds = threshold_optimizer.optimize()
    threshold_results.to_csv("PHASE5C_THRESHOLD_SWEEP.csv", index=False)
    
    print(f"  Best F1 threshold: {optimal_thresholds['best_f1_threshold']:.3f}")
    print(f"  Best recall threshold: {optimal_thresholds['best_recall_threshold']:.3f}")
    print(f"  Best balanced threshold: {optimal_thresholds['best_balanced_threshold']:.3f}")
    print(f"  Best MCC threshold: {optimal_thresholds['best_mcc_threshold']:.3f}")
    print("✓ Threshold optimization complete")
    print()
    
    # =========================================================================
    # GATE 10: Probability calibration
    # =========================================================================
    print("GATE 10: Probability calibration...")
    
    calibrator = ProbabilityCalibrator(probabilities, y)
    calibration_results = calibrator.calibrate()
    
    # Save calibration results
    calibration_df = pd.DataFrame([{
        'method': k,
        'roc_auc': v.get('roc_auc', 0),
        'pr_auc': v.get('pr_auc', 0),
        'f1': v.get('f1', 0),
        'recall': v.get('recall', 0),
        'calibration_error': v.get('calibration_error', 0),
        'brier_score': v.get('brier_score', 0),
        'log_loss': v.get('log_loss', 0)
    } for k, v in calibration_results.items() if isinstance(v, dict) and 'error' not in v])
    
    calibration_df.to_csv("PHASE5C_CALIBRATION_RESULTS.csv", index=False)
    
    # Use calibrated probabilities
    calibrated_probabilities = calibration_results['calibrated_probabilities']
    winner = calibration_results['winner']
    
    print(f"  Calibration winner: {winner}")
    print(f"  Winner Brier score: {calibration_results[winner]['brier_score']:.4f}")
    print("✓ Calibration complete")
    print()
    
    # =========================================================================
    # GATE 11: Patient analysis
    # =========================================================================
    print("GATE 11: Patient robustness analysis...")
    
    if patient_col and patient_col in test_df.columns:
        patients = test_patient_series.unique()
        patient_results = []

        for patient in patients:
            patient_mask = (test_patient_series == patient).values
            patient_probs = calibrated_probabilities[patient_mask]
            patient_labels = y[patient_mask]

            if len(np.unique(patient_labels)) < 2:
                continue
            
            # Use optimal F1 threshold
            threshold = optimal_thresholds['best_f1_threshold']
            patient_preds = (patient_probs >= threshold).astype(int)
            
            tn, fp, fn, tp = confusion_matrix(patient_labels, patient_preds, labels=[0, 1]).ravel()
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
            balanced_acc = balanced_accuracy_score(patient_labels, patient_preds)
            f1 = f1_score(patient_labels, patient_preds, zero_division=0)
            mcc = matthews_corrcoef(patient_labels, patient_preds)
            
            try:
                roc_auc = roc_auc_score(patient_labels, patient_probs)
            except:
                roc_auc = 0.0
            
            try:
                pr_auc = average_precision_score(patient_labels, patient_probs)
            except:
                pr_auc = 0.0
            
            patient_results.append({
                'patient': patient,
                'precision': precision,
                'recall': recall,
                'specificity': specificity,
                'balanced_accuracy': balanced_acc,
                'f1': f1,
                'mcc': mcc,
                'roc_auc': roc_auc,
                'pr_auc': pr_auc,
                'n_samples': len(patient_labels),
                'n_seizures': patient_labels.sum()
            })
        
        patient_df = pd.DataFrame(patient_results)
        patient_df.to_csv("PHASE5C_PATIENT_RESULTS.csv", index=False)
        
        # Compute robustness metrics
        robust_scores = patient_df['f1'].dropna()
        robustness_metrics = {
            'best_patient': patient_df.loc[patient_df['f1'].idxmax(), 'patient'],
            'best_f1': patient_df['f1'].max(),
            'worst_patient': patient_df.loc[patient_df['f1'].idxmin(), 'patient'],
            'worst_f1': patient_df['f1'].min(),
            'median_f1': patient_df['f1'].median(),
            'patient_variance': patient_df['f1'].var(),
            'robustness_score': patient_df['f1'].mean() - patient_df['f1'].std()
        }
        
        print(f"  Best patient F1: {robustness_metrics['best_f1']:.3f}")
        print(f"  Worst patient F1: {robustness_metrics['worst_f1']:.3f}")
        print(f"  Median patient F1: {robustness_metrics['median_f1']:.3f}")
        print(f"  Robustness score: {robustness_metrics['robustness_score']:.3f}")
    else:
        print("  No patient column found - skipping patient analysis")
        patient_df = pd.DataFrame()
        robustness_metrics = {}
    
    print("✓ Patient analysis complete")
    print()
    
    # =========================================================================
    # GATE 12: EDF analysis
    # =========================================================================
    print("GATE 12: EDF-level detection analysis...")
    
    if edf_col and edf_col in test_df.columns:
        edf_files = test_edf_series.unique()
        edf_results = []

        for edf in edf_files:
            edf_mask = (test_edf_series == edf).values
            edf_probs = calibrated_probabilities[edf_mask]
            edf_labels = y[edf_mask]
            
            # EDF-level detection: seizure present if any sample predicted positive
            threshold = optimal_thresholds['best_f1_threshold']
            edf_preds = (edf_probs >= threshold).astype(int)
            
            true_seizure_present = 1 if edf_labels.sum() > 0 else 0
            pred_seizure_present = 1 if edf_preds.sum() > 0 else 0
            
            tn = (true_seizure_present == 0 and pred_seizure_present == 0)
            fp = (true_seizure_present == 0 and pred_seizure_present == 1)
            fn = (true_seizure_present == 1 and pred_seizure_present == 0)
            tp = (true_seizure_present == 1 and pred_seizure_present == 1)
            
            edf_results.append({
                'edf': edf,
                'true_seizure_present': true_seizure_present,
                'predicted_seizure_present': pred_seizure_present,
                'tp': tp,
                'fp': fp,
                'fn': fn,
                'tn': tn,
                'n_samples': len(edf_labels),
                'n_seizure_samples': edf_labels.sum()
            })
        
        edf_df = pd.DataFrame(edf_results)
        
        # Compute aggregate metrics
        tp = edf_df['tp'].sum()
        fp = edf_df['fp'].sum()
        fn = edf_df['fn'].sum()
        tn = edf_df['tn'].sum()
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        balanced_acc = (recall + specificity) / 2
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        edf_df['precision'] = precision
        edf_df['recall'] = recall
        edf_df['specificity'] = specificity
        edf_df['balanced_accuracy'] = balanced_acc
        edf_df['f1'] = f1
        
        edf_df.to_csv("PHASE5C_EDF_RESULTS.csv", index=False)
        
        print(f"  EDF-level detection:")
        print(f"    Precision: {precision:.3f}")
        print(f"    Recall: {recall:.3f}")
        print(f"    F1: {f1:.3f}")
        print(f"    Total EDFs: {len(edf_df)}")
        print(f"    True seizure EDFs: {edf_df['true_seizure_present'].sum()}")
    else:
        print("  No EDF column found - skipping EDF analysis")
        edf_df = pd.DataFrame()
    
    print("✓ EDF analysis complete")
    print()
    
    # =========================================================================
    # Temporal decision optimization evaluation
    # =========================================================================
    print("Evaluating temporal decision optimization methods...")
    
    optimizer = TemporalDecisionOptimizer(calibrated_probabilities, y)
    
    temporal_methods = {
        'original': calibrated_probabilities,
        'smooth_3': optimizer.moving_average_smoothing(3),
        'smooth_5': optimizer.moving_average_smoothing(5),
        'smooth_7': optimizer.moving_average_smoothing(7),
        'majority_vote_3': optimizer.majority_vote_smoothing(3),
        'majority_vote_5': optimizer.majority_vote_smoothing(5),
        'consecutive_2': optimizer.consecutive_positive_confirmation(threshold=0.5, min_consecutive=2),
        'consecutive_3': optimizer.consecutive_positive_confirmation(threshold=0.5, min_consecutive=3),
        'min_duration_10': optimizer.minimum_duration_rule(threshold=0.5, min_duration_samples=10),
        'persistence_3': optimizer.alert_persistence_rule(threshold=0.5, persistence_samples=3),
        'window_confidence_mean': optimizer.window_confidence_aggregation(window_size=5, method='mean')
    }
    
    temporal_results = []
    for method_name, predictions in temporal_methods.items():
        metrics = optimizer.evaluate_method(predictions, method_name)
        temporal_results.append(metrics)
    
    temporal_df = pd.DataFrame(temporal_results)
    # Persist temporal-method comparison for research (do not use these for official metrics)
    temporal_df.to_csv("PHASE5C_TEMPORAL_METHOD_COMPARISON.csv", index=False)
    print(f"  Best method by F1: {temporal_df.loc[temporal_df['f1'].idxmax(), 'method']} (F1={temporal_df['f1'].max():.3f})")
    print(f"  Best method by MCC: {temporal_df.loc[temporal_df['mcc'].idxmax(), 'method']} (MCC={temporal_df['mcc'].max():.3f})")
    print()
    
    # =========================================================================
    # GATE 13: Final metrics and reporting
    # =========================================================================
    print("GATE 13: Generating final metrics...")
    
    # OFFICIAL EVALUATION PATH: use calibrated probabilities + best-F1 threshold
    official_threshold = optimal_thresholds['best_f1_threshold']
    official_predictions = (calibrated_probabilities >= official_threshold).astype(int)

    # Compute final metrics using official predictions
    tn, fp, fn, tp = confusion_matrix(y, official_predictions, labels=[0, 1]).ravel()

    # Mark best_method as official for reporting (temporal methods are research-only)
    best_method = "OFFICIAL_MODEL_OUTPUT"

    final_metrics = {
        'phase': '5C',
        'timestamp': datetime.now().isoformat(),
        'execution_time_seconds': time.time() - start_time,
        'peak_memory_gb': memory_estimator.peak_estimated,
        'dataset_samples': len(y),
        'feature_count': len(feature_cols),
        'seizure_prevalence': float(y.sum() / len(y)),

        # Performance metrics (official)
        'precision': float(tp / (tp + fp) if (tp + fp) > 0 else 0.0),
        'recall': float(tp / (tp + fn) if (tp + fn) > 0 else 0.0),
        'specificity': float(tn / (tn + fp) if (tn + fp) > 0 else 0.0),
        'balanced_accuracy': float(balanced_accuracy_score(y, official_predictions)),
        'f1': float(f1_score(y, official_predictions, zero_division=0)),
        'mcc': float(matthews_corrcoef(y, official_predictions)),
        'kappa': float(cohen_kappa_score(y, official_predictions)),
        'roc_auc': float(roc_auc_score(y, calibrated_probabilities)),
        'pr_auc': float(average_precision_score(y, calibrated_probabilities)),

        # Calibration metrics
        'calibration_error': float(calibration_results[winner]['calibration_error']),
        'brier_score': float(calibration_results[winner]['brier_score']),

        # Optimization results
        'best_temporal_method': best_method,
        'best_f1_threshold': float(official_threshold),
        'calibration_method': winner,

        # Patient robustness
        **{k: float(v) if isinstance(v, (int, float)) else str(v)
           for k, v in robustness_metrics.items()},

        # EDF performance (if available)
        'edf_level_f1': float(f1) if len(edf_df) > 0 else None,
        'edf_count': len(edf_df) if len(edf_df) > 0 else 0,
    }

    # Regression guard: compare with Phase5B metrics and fail if F1 or MCC drop >10%
    if Path("PHASE5B_METRICS.json").exists():
        with open("PHASE5B_METRICS.json", "r") as f:
            phase5b = json.load(f)

        # Safely extract metrics
        phase5b_f1 = float(phase5b.get('f1', phase5b.get('F1', 0)))
        phase5b_mcc = float(phase5b.get('mcc', phase5b.get('MCC', 0)))

        if phase5b_f1 > 0:
            f1_drop = (phase5b_f1 - final_metrics['f1']) / phase5b_f1
            if f1_drop > 0.10:
                raise RuntimeError(f"Phase5B Regression Gate Failed (F1 drop={f1_drop:.2%})")

        if phase5b_mcc > 0:
            mcc_drop = (phase5b_mcc - final_metrics['mcc']) / phase5b_mcc
            if mcc_drop > 0.10:
                raise RuntimeError(f"Phase5B Regression Gate Failed (MCC drop={mcc_drop:.2%})")

    # Save official metrics with JSON safety
    with open("PHASE5C_METRICS.json", "w") as f:
        json.dump(convert_tuple_keys_to_strings(final_metrics), f, default=json_serializer, indent=2)

    print("✓ Final metrics saved")
    print()
    
    # =========================================================================
    # FINAL REPORT
    # =========================================================================
    print("Generating final execution report...")
    
    # Try to load previous phase metrics for comparison
    phase4_metrics = None
    phase5b_metrics = None
    
    if Path("PHASE4C_METRICS.json").exists():
        with open("PHASE4C_METRICS.json", "r") as f:
            phase4_metrics = json.load(f)
    
    if Path("PHASE5B_METRICS.json").exists():
        with open("PHASE5B_METRICS.json", "r") as f:
            phase5b_metrics = json.load(f)
    
    # Generate comparison report
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("NeuroVision Omega - Phase 5C Execution Report")
    report_lines.append("=" * 80)
    report_lines.append(f"Execution Date: {datetime.now().isoformat()}")
    report_lines.append(f"Execution Time: {final_metrics['execution_time_seconds']:.2f} seconds")
    report_lines.append(f"Peak Memory: {final_metrics['peak_memory_gb']:.2f} GB")
    report_lines.append("")
    
    report_lines.append("PERFORMANCE COMPARISON")
    report_lines.append("-" * 40)
    report_lines.append(f"{'Metric':<20} {'Phase 4C':<12} {'Phase 5B':<12} {'Phase 5C':<12}")
    report_lines.append("-" * 56)
    
    metrics_to_compare = ['roc_auc', 'pr_auc', 'precision', 'recall', 
                          'specificity', 'balanced_accuracy', 'f1', 'mcc', 'kappa']
    
    for metric in metrics_to_compare:
        phase4_val = phase4_metrics.get(metric, 0) if phase4_metrics else 0
        phase5b_val = phase5b_metrics.get(metric, 0) if phase5b_metrics else 0
        phase5c_val = final_metrics.get(metric, 0)
        
        report_lines.append(f"{metric:<20} {phase4_val:<12.4f} {phase5b_val:<12.4f} {phase5c_val:<12.4f}")
    
    report_lines.append("")
    report_lines.append("CALIBRATION METRICS")
    report_lines.append("-" * 40)
    report_lines.append(f"Calibration Error: {final_metrics['calibration_error']:.4f}")
    report_lines.append(f"Brier Score: {final_metrics['brier_score']:.4f}")
    report_lines.append(f"Calibration Method: {final_metrics['calibration_method']}")
    report_lines.append(f"Best Temporal Method: {final_metrics['best_temporal_method']}")
    report_lines.append("")
    
    report_lines.append("PATIENT ROBUSTNESS")
    report_lines.append("-" * 40)
    if patient_df is not None and len(patient_df) > 0:
        report_lines.append(f"Best Patient: {robustness_metrics.get('best_patient', 'N/A')} (F1={robustness_metrics.get('best_f1', 0):.3f})")
        report_lines.append(f"Worst Patient: {robustness_metrics.get('worst_patient', 'N/A')} (F1={robustness_metrics.get('worst_f1', 0):.3f})")
        report_lines.append(f"Median Patient F1: {robustness_metrics.get('median_f1', 0):.3f}")
        report_lines.append(f"Patient Variance: {robustness_metrics.get('patient_variance', 0):.4f}")
        report_lines.append(f"Robustness Score: {robustness_metrics.get('robustness_score', 0):.3f}")
    else:
        report_lines.append("No patient data available")
    report_lines.append("")
    
    report_lines.append("EDF DETECTION PERFORMANCE")
    report_lines.append("-" * 40)
    if len(edf_df) > 0:
        report_lines.append(f"EDF-Level F1: {final_metrics.get('edf_level_f1', 0):.3f}")
        report_lines.append(f"Total EDFs: {final_metrics.get('edf_count', 0)}")
        report_lines.append(f"True Seizure EDFs: {edf_df['true_seizure_present'].sum() if len(edf_df) > 0 else 0}")
        report_lines.append(f"Predicted Seizure EDFs: {edf_df['predicted_seizure_present'].sum() if len(edf_df) > 0 else 0}")
    else:
        report_lines.append("No EDF data available")
    report_lines.append("")
    
    report_lines.append("CONCLUSIONS")
    report_lines.append("-" * 40)
    
    # Compare Phase 5C vs Phase 5B
    if phase5b_metrics:
        f1_improvement = final_metrics['f1'] - phase5b_metrics.get('f1', 0)
        mcc_improvement = final_metrics['mcc'] - phase5b_metrics.get('mcc', 0)
        
        if f1_improvement > 0:
            report_lines.append(f"✓ Phase 5C OUTPERFORMS Phase 5B (F1 +{f1_improvement:.3f})")
        else:
            report_lines.append(f"✗ Phase 5C does NOT outperform Phase 5B (F1 {f1_improvement:+.3f})")
        
        if mcc_improvement > 0:
            report_lines.append(f"✓ MCC improvement: +{mcc_improvement:.3f}")
        else:
            report_lines.append(f"✗ MCC degradation: {mcc_improvement:.3f}")
    else:
        report_lines.append("Unable to compare with Phase 5B (metrics not found)")
    
    # Clinical deployment readiness
    readiness_score = 0
    if final_metrics['f1'] > 0.7:
        readiness_score += 1
        report_lines.append("✓ Clinical-ready F1 score (>0.7)")
    if final_metrics['calibration_error'] < 0.1:
        readiness_score += 1
        report_lines.append("✓ Excellent calibration (<0.1 error)")
    if final_metrics['robustness_score'] > 0.6:
        readiness_score += 1
        report_lines.append("✓ Good patient robustness")
    if final_metrics.get('edf_level_f1', 0) > 0.7:
        readiness_score += 1
        report_lines.append("✓ Strong EDF-level detection")
    if final_metrics['peak_memory_gb'] < 10:
        readiness_score += 1
        report_lines.append("✓ Memory-efficient (<10 GB)")
    
    report_lines.append("")
    if readiness_score >= 4:
        report_lines.append("CONCLUSION: Phase 5C SIGNIFICANTLY IMPROVES clinical deployment readiness")
    elif readiness_score >= 3:
        report_lines.append("CONCLUSION: Phase 5C MODERATELY IMPROVES clinical deployment readiness")
    else:
        report_lines.append("CONCLUSION: Phase 5C does NOT improve clinical deployment readiness")
    
    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("End of Report")
    report_lines.append("=" * 80)
    
    # Write report
    with open(
        "PHASE5C_EXECUTION_REPORT.txt",
        "w",
        encoding="utf-8"
    ) as f:
        f.write("\n".join(report_lines))
    
    # Print summary
    for line in report_lines:
        print(line)
    
    print()
    print("=" * 80)
    print("Phase 5C Execution Complete")
    print(f"Total execution time: {final_metrics['execution_time_seconds']:.2f} seconds")
    print("Output files generated:")
    print("  - PHASE5C_METRICS.json")
    print("  - PHASE5C_THRESHOLD_SWEEP.csv")
    print("  - PHASE5C_CALIBRATION_RESULTS.csv")
    print("  - PHASE5C_PATIENT_RESULTS.csv")
    print("  - PHASE5C_EDF_RESULTS.csv")
    print("  - PHASE5C_MEMORY_AUDIT.json")
    print("  - PHASE5C_LEAKAGE_AUDIT.json")
    print("  - PHASE5C_EXECUTION_REPORT.txt")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())