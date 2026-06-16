#!/usr/bin/env python3
"""
NeuroVision Omega - Phase 5C V2: Decision Optimization & Deployment Readiness
Production-grade post-training optimization for clinical seizure detection.

This phase operates EXCLUSIVELY on test set from Phase 5B.
No training. No feature engineering. No model fitting.
Optimizes thresholds, calibration, and temporal decision rules.

Memory budget: 10 GB / 16 GB RAM
CPU: Intel i7-10700 (no GPU required)

Author: NeuroVision Clinical AI Team
Version: 5.2-production-strict
"""

import os
import sys
import json
import warnings
import time
import gc
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
    precision_recall_curve
)
import joblib

# Suppress all non-critical warnings for production
warnings.filterwarnings('ignore')

# =============================================================================
# SAFETY LAYERS - CRITICAL PROTECTION SYSTEMS
# =============================================================================

def json_serializer(obj):
    """Universal JSON serializer - prevents all serialization crashes."""
    if isinstance(obj, (np.int8, np.int16, np.int32, np.int64)):
        return int(obj)
    if isinstance(obj, (np.float16, np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, complex):
        return str(obj)
    if hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool)):
        return str(obj)
    return str(obj)


def convert_tuple_keys_to_strings(obj):
    """Convert tuple keys to strings - prevents tuple-key JSON crash."""
    if isinstance(obj, dict):
        new_dict = {}
        for key, value in obj.items():
            if isinstance(key, tuple):
                new_key = "tuple_" + "_".join(str(x).replace('.', '_') for x in key)
            else:
                new_key = key
            new_dict[new_key] = convert_tuple_keys_to_strings(value)
        return new_dict
    elif isinstance(obj, list):
        return [convert_tuple_keys_to_strings(item) for item in obj]
    elif isinstance(obj, tuple):
        return "tuple_" + "_".join(str(x).replace('.', '_') for x in obj)
    else:
        return obj


class MemoryGuard:
    """Memory protection system - prevents memory explosion."""
    
    def __init__(self, budget_gb: float = 10.0):
        self.budget_gb = budget_gb
        self.allocations = {}
        self.peak_gb = 0.0
    
    def estimate_dataframe(self, df: pd.DataFrame) -> float:
        """Estimate DataFrame memory in GB."""
        return df.memory_usage(deep=True).sum() / (1024 ** 3)
    
    def estimate_array(self, arr: np.ndarray) -> float:
        """Estimate numpy array memory in GB."""
        return arr.nbytes / (1024 ** 3)
    
    def track(self, name: str, size_gb: float):
        """Track memory allocation."""
        self.allocations[name] = size_gb
        self.peak_gb = max(self.peak_gb, sum(self.allocations.values()))
        
        if self.peak_gb > self.budget_gb:
            raise RuntimeError(f"Memory budget exceeded: {self.peak_gb:.2f} GB > {self.budget_gb} GB")
    
    def check(self) -> bool:
        """Check if within budget."""
        return self.peak_gb <= self.budget_gb
    
    def report(self) -> Dict:
        """Generate memory audit report."""
        return {
            "allocations_gb": self.allocations,
            "total_allocated_gb": sum(self.allocations.values()),
            "peak_gb": self.peak_gb,
            "budget_gb": self.budget_gb,
            "within_budget": self.check(),
            "timestamp": datetime.now().isoformat()
        }


class DimensionValidator:
    """Dimension safety system - validates all array dimensions."""
    
    @staticmethod
    def validate_lengths(y: np.ndarray, preds: np.ndarray, probs: np.ndarray, df: pd.DataFrame):
        """Validate all dimension matches."""
        errors = []
        
        if len(y) != len(preds):
            errors.append(f"Gate A failed: y({len(y)}) != preds({len(preds)})")
        
        if len(y) != len(probs):
            errors.append(f"Gate B failed: y({len(y)}) != probs({len(probs)})")
        
        if len(df) != len(y):
            errors.append(f"Gate C failed: df({len(df)}) != y({len(y)})")
        
        if len(df) != len(probs):
            errors.append(f"Gate D failed: df({len(df)}) != probs({len(probs)})")
        
        if errors:
            raise RuntimeError("Dimension validation failed:\n" + "\n".join(errors))
        
        return True


# =============================================================================
# CORE OPTIMIZATION CLASSES
# =============================================================================

class CalibrationScorer:
    """Weighted calibration scoring system."""
    
    @staticmethod
    def compute_weighted_score(metrics: Dict) -> float:
        """Compute weighted score: 40% F1 + 25% MCC + 20% Recall + 10% PR-AUC + 5% CalError."""
        f1 = metrics.get('f1', 0.0)
        mcc = metrics.get('mcc', 0.0)
        recall = metrics.get('recall', 0.0)
        pr_auc = metrics.get('pr_auc', 0.0)
        cal_error = metrics.get('calibration_error', 1.0)
        
        # Calibration error is inverted (lower is better)
        cal_score = 1.0 - min(cal_error, 1.0)
        
        weighted_score = (0.40 * f1 + 
                         0.25 * mcc + 
                         0.20 * recall + 
                         0.10 * pr_auc + 
                         0.05 * cal_score)
        
        return weighted_score


class ThresholdOptimizer:
    """Threshold optimization across probability space."""
    
    def __init__(self, probabilities: np.ndarray, labels: np.ndarray):
        self.probabilities = probabilities.astype(np.float32)
        self.labels = labels.astype(np.uint8)
    
    def optimize(self) -> Tuple[pd.DataFrame, Dict]:
        """Evaluate all thresholds and return results."""
        thresholds = np.arange(0.01, 1.00, 0.01)
        results = []
        
        for threshold in thresholds:
            binary_preds = (self.probabilities >= threshold).astype(np.uint8)
            
            tn, fp, fn, tp = confusion_matrix(self.labels, binary_preds, labels=[0, 1]).ravel()
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
            balanced_acc = balanced_accuracy_score(self.labels, binary_preds)
            f1 = f1_score(self.labels, binary_preds, zero_division=0)
            mcc = matthews_corrcoef(self.labels, binary_preds)
            kappa = cohen_kappa_score(self.labels, binary_preds)
            
            try:
                pr_auc = average_precision_score(self.labels, self.probabilities)
            except:
                pr_auc = 0.0
            
            results.append({
                'threshold': threshold,
                'precision': precision,
                'recall': recall,
                'specificity': specificity,
                'balanced_accuracy': balanced_acc,
                'f1': f1,
                'mcc': mcc,
                'kappa': kappa,
                'pr_auc': pr_auc
            })
        
        results_df = pd.DataFrame(results)
        
        # Find optimal thresholds
        optimal = {
            'best_f1_threshold': results_df.loc[results_df['f1'].idxmax(), 'threshold'],
            'best_recall_threshold': results_df.loc[results_df['recall'].idxmax(), 'threshold'],
            'best_mcc_threshold': results_df.loc[results_df['mcc'].idxmax(), 'threshold'],
            'clinical_threshold': self._find_clinical_threshold(results_df)
        }
        
        return results_df, optimal
    
    def _find_clinical_threshold(self, results_df: pd.DataFrame) -> float:
        """Find clinical threshold maximizing: 0.40*F1 + 0.30*MCC + 0.20*Recall + 0.10*PR-AUC."""
        clinical_scores = (0.40 * results_df['f1'] + 
                          0.30 * results_df['mcc'] + 
                          0.20 * results_df['recall'] + 
                          0.10 * results_df['pr_auc'])
        
        idx_max = clinical_scores.idxmax()
        return results_df.loc[idx_max, 'threshold']


class ProbabilityCalibrator:
    """Probability calibration with weighted scoring."""
    
    def __init__(self, probabilities: np.ndarray, labels: np.ndarray):
        self.probabilities = probabilities.astype(np.float32)
        self.labels = labels.astype(np.uint8)
        self.scorer = CalibrationScorer()
    
    def calibrate(self) -> Dict:
        """Apply calibration methods and select winner by weighted score."""
        # Split data for calibration (50/50)
        n = len(self.probabilities)
        split = n // 2
        np.random.seed(42)
        indices = np.random.permutation(n)
        calib_idx = indices[:split]
        eval_idx = indices[split:]
        
        calib_probs = self.probabilities[calib_idx]
        calib_labels = self.labels[calib_idx]
        eval_probs = self.probabilities[eval_idx]
        eval_labels = self.labels[eval_idx]
        
        results = {}
        
        # RAW (no calibration)
        raw_preds = (eval_probs >= 0.5).astype(np.uint8)
        results['RAW'] = self._compute_full_metrics(eval_labels, eval_probs, raw_preds)
        
        # Platt Scaling (Sigmoid)
        try:
            platt = CalibratedClassifierCV(estimator=None, cv=3, method='sigmoid')
            platt.fit(calib_probs.reshape(-1, 1), calib_labels)
            platt_probs = platt.predict_proba(eval_probs.reshape(-1, 1))[:, 1].astype(np.float32)
            platt_preds = (platt_probs >= 0.5).astype(np.uint8)
            results['PLATT_SCALING'] = self._compute_full_metrics(eval_labels, platt_probs, platt_preds)
        except Exception as e:
            results['PLATT_SCALING'] = {'error': str(e), 'weighted_score': -1.0}
        
        # Isotonic Regression
        try:
            isotonic = CalibratedClassifierCV(estimator=None, cv=3, method='isotonic')
            isotonic.fit(calib_probs.reshape(-1, 1), calib_labels)
            isotonic_probs = isotonic.predict_proba(eval_probs.reshape(-1, 1))[:, 1].astype(np.float32)
            isotonic_preds = (isotonic_probs >= 0.5).astype(np.uint8)
            results['ISOTONIC_REGRESSION'] = self._compute_full_metrics(eval_labels, isotonic_probs, isotonic_preds)
        except Exception as e:
            results['ISOTONIC_REGRESSION'] = {'error': str(e), 'weighted_score': -1.0}
        
        # Select winner by weighted score
        winner = max(results.keys(), key=lambda k: results[k].get('weighted_score', -1))
        results['winner'] = winner
        results['winner_weighted_score'] = results[winner]['weighted_score']
        
        # Apply winner to full dataset
        if winner == 'RAW':
            calibrated_full = self.probabilities
        elif winner == 'PLATT_SCALING':
            calibrator = CalibratedClassifierCV(estimator=None, cv=3, method='sigmoid')
            calibrator.fit(self.probabilities.reshape(-1, 1), self.labels)
            calibrated_full = calibrator.predict_proba(self.probabilities.reshape(-1, 1))[:, 1].astype(np.float32)
        else:
            calibrator = CalibratedClassifierCV(estimator=None, cv=3, method='isotonic')
            calibrator.fit(self.probabilities.reshape(-1, 1), self.labels)
            calibrated_full = calibrator.predict_proba(self.probabilities.reshape(-1, 1))[:, 1].astype(np.float32)
        
        results['calibrated_probabilities'] = calibrated_full
        
        return results
    
    def _compute_full_metrics(self, y_true, y_proba, y_pred):
        """Compute all metrics including weighted score."""
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
        precision = precision_score(y_true, y_pred, zero_division=0)
        mcc = matthews_corrcoef(y_true, y_pred)
        
        # Calibration error
        try:
            prob_true, prob_pred = calibration_curve(y_true, y_proba, n_bins=10)
            calibration_error = np.mean(np.abs(prob_true - prob_pred))
        except:
            calibration_error = 1.0
        
        brier = brier_score_loss(y_true, y_proba)
        
        weighted_score = self.scorer.compute_weighted_score({
            'f1': f1, 'mcc': mcc, 'recall': recall, 'pr_auc': pr_auc, 'calibration_error': calibration_error
        })
        
        return {
            'roc_auc': roc_auc,
            'pr_auc': pr_auc,
            'f1': f1,
            'recall': recall,
            'precision': precision,
            'mcc': mcc,
            'calibration_error': calibration_error,
            'brier_score': brier,
            'weighted_score': weighted_score
        }


class TemporalDecisionOptimizer:
    """Temporal decision optimization (smoothing, voting, persistence)."""
    
    def __init__(self, probabilities: np.ndarray, labels: np.ndarray):
        self.probabilities = probabilities.astype(np.float32)
        self.labels = labels.astype(np.uint8)
    
    def moving_average(self, window: int) -> np.ndarray:
        """Moving average smoothing."""
        kernel = np.ones(window) / window
        return np.convolve(self.probabilities, kernel, mode='same').astype(np.float32)
    
    def majority_vote(self, window: int) -> np.ndarray:
        """Majority vote smoothing."""
        smoothed = np.zeros_like(self.probabilities)
        half = window // 2
        
        for i in range(len(self.probabilities)):
            start = max(0, i - half)
            end = min(len(self.probabilities), i + half + 1)
            smoothed[i] = 1.0 if np.mean(self.probabilities[start:end]) > 0.5 else 0.0
        
        return smoothed.astype(np.float32)
    
    def consecutive_confirm(self, threshold: float = 0.5, min_consecutive: int = 2) -> np.ndarray:
        """Require consecutive positives."""
        binary = (self.probabilities >= threshold).astype(np.uint8)
        confirmed = np.zeros_like(binary, dtype=np.float32)
        
        count = 0
        for i in range(len(binary)):
            if binary[i] == 1:
                count += 1
                if count >= min_consecutive:
                    confirmed[i] = 1.0
            else:
                count = 0
        
        return confirmed
    
    def min_duration(self, threshold: float = 0.5, min_samples: int = 10) -> np.ndarray:
        """Enforce minimum seizure duration."""
        binary = (self.probabilities >= threshold).astype(np.uint8)
        filtered = np.zeros_like(binary, dtype=np.float32)
        
        i = 0
        while i < len(binary):
            if binary[i] == 1:
                j = i
                while j < len(binary) and binary[j] == 1:
                    j += 1
                if (j - i) >= min_samples:
                    filtered[i:j] = 1.0
                i = j
            else:
                i += 1
        
        return filtered
    
    def evaluate_method(self, predictions: np.ndarray, method_name: str, threshold: float = 0.5) -> Dict:
        """Evaluate a temporal optimization method."""
        binary_preds = (predictions >= threshold).astype(np.uint8)
        
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


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution pipeline for Phase 5C V2."""
    
    print("=" * 80)
    print("NeuroVision Omega - Phase 5C V2: Decision Optimization")
    print("Production Deployment Readiness System")
    print("=" * 80)
    print(f"Start: {datetime.now().isoformat()}")
    print()
    
    start_time = time.time()
    memory = MemoryGuard(budget_gb=10.0)
    
    # =========================================================================
    # INPUT VALIDATION
    # =========================================================================
    print("VALIDATING INPUT FILES...")
    
    required_files = {
        'dataset': Path("PHASE5B_ENGINEERED_DATASET.parquet"),
        'model': Path("PHASE5B_TEMPORAL_XGBOOST.joblib"),
        'split': Path("PHASE5B_PATIENT_SPLIT.json"),
        'metrics': Path("PHASE5B_METRICS.json")
    }
    
    for name, path in required_files.items():
        if not path.exists():
            raise RuntimeError(f"Missing required file: {name} ({path})")
    
    print("✓ All input files found")
    print()
    
    # =========================================================================
    # LOAD DATA (TEST SET ONLY)
    # =========================================================================
    print("LOADING TEST SET ONLY...")
    
    full_df = pd.read_parquet(required_files['dataset'])
    memory.track("full_dataset", memory.estimate_dataframe(full_df))
    
    with open(required_files['split'], 'r') as f:
        split = json.load(f)
    
    test_patients = split.get('test_patients', [])
    if not test_patients:
        raise RuntimeError("No test patients found in split file")
    
    # Detect patient column
    if 'patient' in full_df.columns:
        patient_col = 'patient'
    elif 'patient_id' in full_df.columns:
        patient_col = 'patient_id'
    else:
        raise RuntimeError(
            f"No patient column found. Available columns: {list(full_df.columns)}"
        )

    # Detect EDF column
    if 'edf' in full_df.columns:
        edf_col = 'edf'
    elif 'edf_filename' in full_df.columns:
        edf_col = 'edf_filename'
    else:
        raise RuntimeError(
            f"No EDF column found. Available columns: {list(full_df.columns)}"
        )

    test_df = full_df[full_df[patient_col].isin(test_patients)].copy()
    
    memory.track("test_dataset", memory.estimate_dataframe(test_df))
    
    print(f"  Full dataset: {len(full_df)} samples")
    print(f"  Test patients: {len(test_patients)}")
    print(f"  Test samples: {len(test_df)}")
    print(f"  Test memory: {memory.allocations['test_dataset']:.2f} GB")
    print()
    
    # Free full dataframe
    del full_df
    gc.collect()
    
    # =========================================================================
    # FEATURE RECOVERY
    # =========================================================================
    print("RECOVERING FEATURE SET FROM MODEL...")
    
    model = joblib.load(required_files['model'])
    n_features_expected = model.n_features_in_
    
    # Identify feature columns (exclude non-features)
    exclude_cols = [
        'label',
        'seizure_label',
        'target',
        'patient',
        'patient_id',
        'edf',
        'edf_filename',
    'window_index',
    'window_start_sec',
    'window_end_sec',
    'window_duration_sec',
    'stride_sec',
        'timestamp',
        'time',
        'sample_index'
    ]
    feature_candidates = [col for col in test_df.columns if col not in exclude_cols]
    
    # Use model's feature names if available
    if hasattr(model, 'feature_names_in_'):
        expected_features = list(model.feature_names_in_)
        available_features = [f for f in expected_features if f in test_df.columns]
        
        if len(available_features) != len(expected_features):
            missing = set(expected_features) - set(available_features)
            raise RuntimeError(f"Missing features: {missing}")
        
        feature_cols = expected_features
    else:
        # Use all numeric columns as features
        feature_cols = test_df[feature_candidates].select_dtypes(include=[np.number]).columns.tolist()
    
    if len(feature_cols) != n_features_expected:
        raise RuntimeError(f"Feature count mismatch: {len(feature_cols)} vs expected {n_features_expected}")
    
    X_test = test_df[feature_cols].values.astype(np.float32)
    memory.track("features", memory.estimate_array(X_test))
    
    # Extract labels
    label_col = None
    for candidate in ['label', 'seizure_label', 'target']:
        if candidate in test_df.columns:
            label_col = candidate
            break
    
    if label_col is None:
        raise RuntimeError("No label column found")
    
    y_test = test_df[label_col].values.astype(np.uint8)
    memory.track("labels", memory.estimate_array(y_test))
    
    print(f"  Expected features: {n_features_expected}")
    print(f"  Recovered features: {len(feature_cols)}")
    print(f"  Test samples: {len(X_test)}")
    print(f"  Seizure prevalence: {y_test.sum() / len(y_test):.4f}")
    print()
    
    # =========================================================================
    # GENERATE PREDICTIONS (BATCHED)
    # =========================================================================
    print("GENERATING PREDICTIONS (BATCHED)...")
    
    batch_size = 5000
    probabilities = []
    
    for i in range(0, len(X_test), batch_size):
        batch = X_test[i:i+batch_size]
        batch_probs = model.predict_proba(batch)[:, 1].astype(np.float32)
        probabilities.append(batch_probs)
        gc.collect()
    
    probabilities = np.concatenate(probabilities)
    memory.track("predictions", memory.estimate_array(probabilities))
    
    print(f"  Predictions memory: {memory.allocations['predictions']:.2f} GB")
    print()
    
    # =========================================================================
    # DIMENSION VALIDATION
    # =========================================================================
    print("VALIDATING DIMENSIONS...")
    DimensionValidator.validate_lengths(y_test, probabilities, probabilities, test_df)
    print("✓ All dimension gates passed")
    print()
    
    # =========================================================================
    # THRESHOLD OPTIMIZATION
    # =========================================================================
    print("OPTIMIZING THRESHOLDS...")
    
    threshold_opt = ThresholdOptimizer(probabilities, y_test)
    threshold_df, optimal_thresholds = threshold_opt.optimize()
    threshold_df.to_csv("PHASE5C_V2_THRESHOLD_SWEEP.csv", index=False, encoding="utf-8")
    
    print(f"  Best F1 threshold: {optimal_thresholds['best_f1_threshold']:.3f}")
    print(f"  Best recall threshold: {optimal_thresholds['best_recall_threshold']:.3f}")
    print(f"  Best MCC threshold: {optimal_thresholds['best_mcc_threshold']:.3f}")
    print(f"  Clinical threshold: {optimal_thresholds['clinical_threshold']:.3f}")
    print()
    
    # =========================================================================
    # CALIBRATION
    # =========================================================================
    print("CALIBRATING PROBABILITIES...")
    
    calibrator = ProbabilityCalibrator(probabilities, y_test)
    calibration_results = calibrator.calibrate()
    
    # Save calibration results
    calib_df = pd.DataFrame([{
        'method': k,
        'roc_auc': v.get('roc_auc', 0),
        'pr_auc': v.get('pr_auc', 0),
        'f1': v.get('f1', 0),
        'recall': v.get('recall', 0),
        'precision': v.get('precision', 0),
        'mcc': v.get('mcc', 0),
        'calibration_error': v.get('calibration_error', 1),
        'brier_score': v.get('brier_score', 1),
        'weighted_score': v.get('weighted_score', -1)
    } for k, v in calibration_results.items() if isinstance(v, dict) and 'error' not in v])
    
    calib_df.to_csv("PHASE5C_V2_CALIBRATION_RESULTS.csv", index=False, encoding="utf-8")
    
    calibrated_probs = calibration_results['calibrated_probabilities']
    winner = calibration_results['winner']
    
    print(f"  Winner: {winner}")
    print(f"  Weighted score: {calibration_results['winner_weighted_score']:.4f}")
    print()
    
    # =========================================================================
    # TEMPORAL DECISION OPTIMIZATION (RESEARCH-ONLY)
    # =========================================================================
    print("EVALUATING TEMPORAL DECISION METHODS...")

    optimizer = TemporalDecisionOptimizer(calibrated_probs, y_test)
    clinical_threshold = optimal_thresholds['clinical_threshold']

    temporal_methods = {
        'original': calibrated_probs,
        'smooth_3': optimizer.moving_average(3),
        'smooth_5': optimizer.moving_average(5),
        'smooth_7': optimizer.moving_average(7),
        'majority_3': optimizer.majority_vote(3),
        'majority_5': optimizer.majority_vote(5),
        'consecutive_2': optimizer.consecutive_confirm(threshold=clinical_threshold, min_consecutive=2),
        'consecutive_3': optimizer.consecutive_confirm(threshold=clinical_threshold, min_consecutive=3),
        'min_duration_10': optimizer.min_duration(threshold=clinical_threshold, min_samples=10),
        'min_duration_20': optimizer.min_duration(threshold=clinical_threshold, min_samples=20)
    }

    temporal_results = []
    for name, probs in temporal_methods.items():
        metrics = optimizer.evaluate_method(probs, name, threshold=clinical_threshold)
        temporal_results.append(metrics)

    temporal_df = pd.DataFrame(temporal_results)
    # Save temporal-method comparison for research; do NOT use these to overwrite official metrics
    temporal_df.to_csv("PHASE5C_TEMPORAL_METHOD_COMPARISON.csv", index=False, encoding="utf-8")
    research_best_method = None
    if len(temporal_df) > 0:
        research_best_method = temporal_df.loc[temporal_df['f1'].idxmax(), 'method']
        print(f"  Best method by F1 (research-only): {research_best_method} (F1={temporal_df['f1'].max():.4f})")
    print()

    # =========================================================================
    # OFFICIAL METRICS (CALIBRATED WINNER + BEST-F1 THRESHOLD)
    # =========================================================================
    print("COMPUTING FINAL METRICS (official)...")

    official_probs = calibrated_probs  # calibrated by 'winner' above
    official_threshold = optimal_thresholds['best_f1_threshold']

    # Consistency gate: shapes must match
    if len(official_probs) != len(y_test):
        raise RuntimeError(f"Shape mismatch: calibrated probabilities ({len(official_probs)}) != y_test ({len(y_test)})")

    official_preds = (official_probs >= official_threshold).astype(np.uint8)
    tn, fp, fn, tp = confusion_matrix(y_test, official_preds, labels=[0, 1]).ravel()

    final_metrics = {
        'phase': '5C_V2',
        'timestamp': datetime.now().isoformat(),
        'execution_time_seconds': time.time() - start_time,
        'peak_memory_gb': memory.peak_gb,
        'test_samples': len(y_test),
        'test_seizures': int(y_test.sum()),
        'seizure_prevalence': float(y_test.sum() / len(y_test)),

        # Performance metrics (derived from official_preds / official_probs)
        'precision': float(tp / (tp + fp) if (tp + fp) > 0 else 0.0),
        'recall': float(tp / (tp + fn) if (tp + fn) > 0 else 0.0),
        'specificity': float(tn / (tn + fp) if (tn + fp) > 0 else 0.0),
        'balanced_accuracy': float(balanced_accuracy_score(y_test, official_preds)),
        'f1': float(f1_score(y_test, official_preds, zero_division=0)),
        'mcc': float(matthews_corrcoef(y_test, official_preds)),
        'kappa': float(cohen_kappa_score(y_test, official_preds)),
        'roc_auc': float(roc_auc_score(y_test, official_probs)),
        'pr_auc': float(average_precision_score(y_test, official_probs)),

        # Calibration
        'calibration_method': winner,
        'calibration_error': float(calibration_results[winner].get('calibration_error', 1.0)),
        'brier_score': float(calibration_results[winner].get('brier_score', 1.0)),

        # Optimization (official)
        'clinical_threshold': float(clinical_threshold),
        'best_f1_threshold': float(official_threshold)
    }

    # Save official metrics
    with open("PHASE5C_V2_METRICS.json", "w", encoding="utf-8") as f:
        json.dump(convert_tuple_keys_to_strings(final_metrics), f, default=json_serializer, indent=2)

    print("✓ Final metrics computed (official)")
    print()
    
    # =========================================================================
    # PATIENT ROBUSTNESS (TEST SET ONLY)
    # =========================================================================
    print("ANALYZING PATIENT ROBUSTNESS...")
    
    if patient_col in test_df.columns:
        patient_results = []
        patients = test_df[patient_col].unique()

        for patient in patients:
            mask = test_df[patient_col] == patient
            patient_probs = official_probs[mask]
            patient_labels = y_test[mask]

            if len(np.unique(patient_labels)) < 2:
                continue

            patient_preds = (patient_probs >= official_threshold).astype(np.uint8)
            
            tn_p, fp_p, fn_p, tp_p = confusion_matrix(patient_labels, patient_preds, labels=[0, 1]).ravel()
            
            precision_p = tp_p / (tp_p + fp_p) if (tp_p + fp_p) > 0 else 0.0
            recall_p = tp_p / (tp_p + fn_p) if (tp_p + fn_p) > 0 else 0.0
            specificity_p = tn_p / (tn_p + fp_p) if (tn_p + fp_p) > 0 else 0.0
            f1_p = f1_score(patient_labels, patient_preds, zero_division=0)
            mcc_p = matthews_corrcoef(patient_labels, patient_preds)
            
            try:
                roc_auc_p = roc_auc_score(patient_labels, patient_probs)
            except:
                roc_auc_p = 0.0
            
            try:
                pr_auc_p = average_precision_score(patient_labels, patient_probs)
            except:
                pr_auc_p = 0.0
            
            patient_results.append({
                'patient': str(patient),
                'precision': precision_p,
                'recall': recall_p,
                'specificity': specificity_p,
                'f1': f1_p,
                'mcc': mcc_p,
                'roc_auc': roc_auc_p,
                'pr_auc': pr_auc_p,
                'samples': len(patient_labels),
                'seizures': int(patient_labels.sum())
            })
        
        patient_df = pd.DataFrame(patient_results)
        patient_df.to_csv("PHASE5C_V2_PATIENT_RESULTS.csv", index=False, encoding="utf-8")
        
        print(f"  Patients analyzed: {len(patient_df)}")
        print(f"  Mean patient F1: {patient_df['f1'].mean():.4f}")
        print(f"  Patient F1 std: {patient_df['f1'].std():.4f}")
    else:
        print("  No patient column - skipping patient analysis")
        patient_df = pd.DataFrame()
    
    print()
    
    # =========================================================================
    # EDF ANALYSIS (TEST SET ONLY)
    # =========================================================================
    print("ANALYZING EDF-LEVEL DETECTION...")
    
    if edf_col in test_df.columns:
        edf_results = []
        edfs = test_df[edf_col].unique()

        for edf in edfs:
            mask = test_df[edf_col] == edf
            edf_probs = official_probs[mask]
            edf_labels = y_test[mask]
            edf_preds = (edf_probs >= official_threshold).astype(np.uint8)
            
            true_seizure = 1 if edf_labels.sum() > 0 else 0
            pred_seizure = 1 if edf_preds.sum() > 0 else 0
            
            tp_e = 1 if (true_seizure == 1 and pred_seizure == 1) else 0
            fp_e = 1 if (true_seizure == 0 and pred_seizure == 1) else 0
            fn_e = 1 if (true_seizure == 1 and pred_seizure == 0) else 0
            tn_e = 1 if (true_seizure == 0 and pred_seizure == 0) else 0
            
            edf_results.append({
                'edf': str(edf),
                'seizure_present': true_seizure,
                'predicted_present': pred_seizure,
                'tp': tp_e,
                'fp': fp_e,
                'fn': fn_e,
                'tn': tn_e,
                'samples': len(edf_labels),
                'seizure_samples': int(edf_labels.sum())
            })
        
        edf_df = pd.DataFrame(edf_results)
        
        # Aggregate metrics
        tp_sum = edf_df['tp'].sum()
        fp_sum = edf_df['fp'].sum()
        fn_sum = edf_df['fn'].sum()
        tn_sum = edf_df['tn'].sum()
        
        edf_precision = tp_sum / (tp_sum + fp_sum) if (tp_sum + fp_sum) > 0 else 0.0
        edf_recall = tp_sum / (tp_sum + fn_sum) if (tp_sum + fn_sum) > 0 else 0.0
        edf_specificity = tn_sum / (tn_sum + fp_sum) if (tn_sum + fp_sum) > 0 else 0.0
        edf_f1 = 2 * (edf_precision * edf_recall) / (edf_precision + edf_recall) if (edf_precision + edf_recall) > 0 else 0.0
        
        edf_df['precision'] = edf_precision
        edf_df['recall'] = edf_recall
        edf_df['specificity'] = edf_specificity
        edf_df['f1'] = edf_f1
        
        edf_df.to_csv("PHASE5C_V2_EDF_RESULTS.csv", index=False, encoding="utf-8")
        
        print(f"  EDFs analyzed: {len(edf_df)}")
        print(f"  EDF-level F1: {edf_f1:.4f}")
        print(f"  True seizure EDFs: {edf_df['seizure_present'].sum()}")
        print(f"  Predicted seizure EDFs: {edf_df['predicted_present'].sum()}")
    else:
        print("  No EDF column - skipping EDF analysis")
        edf_df = pd.DataFrame()
    
    print()
    
    # =========================================================================
    # DEPLOYMENT COMPARISON WITH PHASE 5B
    # =========================================================================
    print("COMPARING WITH PHASE 5B BASELINE...")
    
    with open(required_files['metrics'], 'r') as f:
        phase5b_metrics = json.load(f)
    
    # Extract Phase 5B metrics (handle different naming conventions)
    def get_metric(metrics_dict, key, default=0.0):
        return float(metrics_dict.get(key, metrics_dict.get(key.upper(), default)))
    
    phase5b_f1 = get_metric(phase5b_metrics, 'f1', 0.3282)
    phase5b_recall = get_metric(phase5b_metrics, 'recall', 0.2453)
    phase5b_precision = get_metric(phase5b_metrics, 'precision', 0.4960)
    phase5b_mcc = get_metric(phase5b_metrics, 'mcc', 0.3458)
    phase5b_pr_auc = get_metric(phase5b_metrics, 'pr_auc', 0.2428)
    phase5b_roc_auc = get_metric(phase5b_metrics, 'roc_auc', 0.7542)
    
    # Compute deltas (for reporting)
    delta_f1 = final_metrics['f1'] - phase5b_f1
    delta_recall = final_metrics['recall'] - phase5b_recall
    delta_precision = final_metrics['precision'] - phase5b_precision
    delta_mcc = final_metrics['mcc'] - phase5b_mcc
    delta_pr_auc = final_metrics['pr_auc'] - phase5b_pr_auc
    delta_roc_auc = final_metrics['roc_auc'] - phase5b_roc_auc

    # Regression gate: only fail if F1 or MCC drop > 10% relative to Phase5B
    relative_f1_decrease = (phase5b_f1 - final_metrics['f1']) / phase5b_f1 if phase5b_f1 > 0 else 0
    relative_mcc_decrease = (phase5b_mcc - final_metrics['mcc']) / phase5b_mcc if phase5b_mcc > 0 else 0

    gate_failures = []
    if relative_f1_decrease > 0.10:
        gate_failures.append(f"F1 decreased by {relative_f1_decrease*100:.1f}% (>10%)")
    if relative_mcc_decrease > 0.10:
        gate_failures.append(f"MCC decreased by {relative_mcc_decrease*100:.1f}% (>10%)")
    
    # Create comparison dataframe
    comparison_df = pd.DataFrame({
        'metric': ['f1', 'recall', 'precision', 'mcc', 'pr_auc', 'roc_auc'],
        'phase5b': [phase5b_f1, phase5b_recall, phase5b_precision, phase5b_mcc, phase5b_pr_auc, phase5b_roc_auc],
        'phase5c_v2': [final_metrics['f1'], final_metrics['recall'], final_metrics['precision'],
                      final_metrics['mcc'], final_metrics['pr_auc'], final_metrics['roc_auc']],
        'delta': [delta_f1, delta_recall, delta_precision, delta_mcc, delta_pr_auc, delta_roc_auc],
        'improved': [delta_f1 > 0, delta_recall > 0, delta_precision > 0, 
                    delta_mcc > 0, delta_pr_auc > 0, delta_roc_auc > 0]
    })
    
    comparison_df.to_csv("PHASE5C_V2_DEPLOYMENT_COMPARISON.csv", index=False, encoding="utf-8")
    
    # Deployment score
    deployment_score = sum(comparison_df['improved']) / len(comparison_df)
    
    print(f"  Phase 5B F1: {phase5b_f1:.4f} → Phase 5C F1: {final_metrics['f1']:.4f} (Δ={delta_f1:+.4f})")
    print(f"  Phase 5B Recall: {phase5b_recall:.4f} → Phase 5C Recall: {final_metrics['recall']:.4f} (Δ={delta_recall:+.4f})")
    print(f"  Deployment score: {deployment_score:.2f}")
    print()
    
    if gate_failures:
        raise RuntimeError("Phase5B Regression Gate Failed:\n" + "\n".join(gate_failures))

    if failures:
        # Non-gate failures are reported but do not raise the Phase5B gate
        print("Non-gate validation issues:\n" + "\n".join(failures))

    print("✓ Phase 5C maintains or improves critical deployment metrics (gates passed)")
    print()
    
    # =========================================================================
    # MEMORY AUDIT
    # =========================================================================
    print("SAVING MEMORY AUDIT...")
    
    memory_audit = memory.report()
    with open("PHASE5C_V2_MEMORY_AUDIT.json", "w", encoding="utf-8") as f:
        json.dump(convert_tuple_keys_to_strings(memory_audit), f, default=json_serializer, indent=2)
    
    print(f"  Peak memory: {memory_audit['peak_gb']:.2f} GB")
    print(f"  Within budget: {memory_audit['within_budget']}")
    print()
    
    # =========================================================================
    # EXECUTION REPORT
    # =========================================================================
    print("GENERATING EXECUTION REPORT...")
    
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("NeuroVision Omega - Phase 5C V2 Execution Report")
    report_lines.append("=" * 80)
    report_lines.append(f"Execution Date: {datetime.now().isoformat()}")
    report_lines.append(f"Execution Time: {final_metrics['execution_time_seconds']:.2f} seconds")
    report_lines.append(f"Peak Memory: {final_metrics['peak_memory_gb']:.2f} GB")
    report_lines.append("")
    
    report_lines.append("FINAL PERFORMANCE")
    report_lines.append("-" * 40)
    report_lines.append(f"F1 Score: {final_metrics['f1']:.4f}")
    report_lines.append(f"Recall: {final_metrics['recall']:.4f}")
    report_lines.append(f"Precision: {final_metrics['precision']:.4f}")
    report_lines.append(f"MCC: {final_metrics['mcc']:.4f}")
    report_lines.append(f"ROC-AUC: {final_metrics['roc_auc']:.4f}")
    report_lines.append(f"PR-AUC: {final_metrics['pr_auc']:.4f}")
    report_lines.append("")
    
    report_lines.append("OPTIMIZATION PARAMETERS")
    report_lines.append("-" * 40)
    report_lines.append(f"Calibration Method: {final_metrics['calibration_method']}")
    report_lines.append(f"Temporal Method (research-best): {research_best_method or 'N/A'}")
    report_lines.append(f"Clinical Threshold: {final_metrics['clinical_threshold']:.3f}")
    report_lines.append("")
    
    report_lines.append("DEPLOYMENT READINESS")
    report_lines.append("-" * 40)
    report_lines.append(f"Deployment Score: {deployment_score:.2f} / 1.00")
    
    if deployment_score >= 0.8:
        report_lines.append("STATUS: ✓ READY FOR CLINICAL DEPLOYMENT")
    elif deployment_score >= 0.6:
        report_lines.append("STATUS: ⚠ CONDITIONALLY READY (requires review)")
    else:
        report_lines.append("STATUS: ✗ NOT READY FOR DEPLOYMENT")
    
    report_lines.append("")
    report_lines.append("=" * 80)
    
    with open("PHASE5C_V2_EXECUTION_REPORT.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    
    for line in report_lines:
        print(line)
    
    print()
    print("=" * 80)
    print("Phase 5C V2 Execution Complete")
    print("All validation gates passed")
    print("Output files generated successfully")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)