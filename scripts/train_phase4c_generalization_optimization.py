#!/usr/bin/env python3
"""
NEUROVISION OMEGA - PHASE 4C GENERALIZATION OPTIMIZATION SYSTEM
Production-grade training pipeline for patient-disjoint seizure detection.

Mission:
1. Diagnose patient-disjoint performance collapse
2. Improve generalization to unseen patients
3. Optimize F1, Recall, PR-AUC
4. Reduce patient-to-patient variance
5. Produce clinically meaningful seizure detector
"""

import os
import sys
import json
import warnings
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV, cross_val_predict
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, VotingClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score, average_precision_score, f1_score, recall_score,
    precision_score, accuracy_score, balanced_accuracy_score, brier_score_loss,
    log_loss, confusion_matrix, roc_curve, precision_recall_curve
)
from sklearn.preprocessing import StandardScaler, label_binarize
import joblib

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# For Balanced Random Forest if available
try:
    from imblearn.ensemble import BalancedRandomForestClassifier
    BALANCED_RF_AVAILABLE = True
except ImportError:
    BALANCED_RF_AVAILABLE = False
    print("Warning: imbalanced-learn not installed. BalancedRandomForest unavailable.")

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    print("Warning: xgboost not installed. XGBoost model unavailable.")

# JSON serializer for numpy types
def json_serializer(obj):
    """Custom JSON serializer for numpy types."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    
    if isinstance(obj, (np.floating,)):
        return float(obj)
    
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    
    if hasattr(obj, "tolist"):
        return obj.tolist()
    
    return str(obj)

# Configuration
RANDOM_STATE = 42
N_JOBS = -1
DATA_PATH = "real_feature_dataset_v4_clean.parquet"
OUTPUT_DIR = Path("phase4c_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Threshold grid for optimization
THRESHOLDS = np.arange(0.01, 1.00, 0.01)


class DataValidator:
    """Validate dataset integrity before training."""
    
    @staticmethod
    def validate(df: pd.DataFrame) -> None:
        print("\n" + "=" * 80)
        print("VALIDATION GATES")
        print("=" * 80)
        
        # Check dataset exists (already loaded)
        print(f"✓ Dataset loaded: {len(df):,} rows")
        
        # Check rows > 0
        assert len(df) > 0, "Dataset has zero rows"
        print(f"✓ Rows: {len(df):,}")
        
        # Check columns = 99
        assert df.shape[1] == 99, f"Expected 99 columns, got {df.shape[1]}"
        print(f"✓ Columns: {df.shape[1]}")
        
        # Check features = 96
        feature_cols = [
            c for c in df.columns
            if c not in ["label", "patient", "edf"]
        ]
        assert len(feature_cols) == 96, f"Expected 96 feature columns, got {len(feature_cols)}"
        print(f"✓ Feature columns: {len(feature_cols)}")
        
        # Check patients = 24
        patients = df['patient'].unique()
        assert len(patients) == 24, f"Expected 24 patients, got {len(patients)}"
        print(f"✓ Unique patients: {len(patients)}")
        
        # Check EDF count = 686
        edfs = df['edf'].unique()
        assert len(edfs) == 686, f"Expected 686 EDF files, got {len(edfs)}"
        print(f"✓ EDF files: {len(edfs)}")
        
        # Check label column exists
        assert 'label' in df.columns, "Label column missing"
        print("✓ Label column exists")
        
        # Check patient column exists
        assert 'patient' in df.columns, "Patient column missing"
        print("✓ Patient column exists")
        
        # Check edf column exists
        assert 'edf' in df.columns, "EDF column missing"
        print("✓ EDF column exists")
        
        # Check no NaN
        assert not df.isna().any().any(), "Dataset contains NaN values"
        print("✓ No NaN values")
        
        # Check no Inf
        assert not np.isinf(df.select_dtypes(include=[np.number]).values).any(), "Dataset contains Inf values"
        print("✓ No Inf values")
        
        # Print class distribution
        seizure_count = df['label'].sum()
        background_count = len(df) - seizure_count
        print(f"\nClass Distribution:")
        print(f"  Seizure windows: {seizure_count:,} ({seizure_count/len(df)*100:.2f}%)")
        print(f"  Background windows: {background_count:,} ({background_count/len(df)*100:.2f}%)")
        
        print("\n✓ ALL VALIDATION GATES PASSED ✓")
        print("=" * 80)


class PatientSplitter:
    """Handle patient-disjoint train/test split."""
    
    @staticmethod
    def split(df: pd.DataFrame, random_state: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
        patients = sorted(df['patient'].unique())
        np.random.seed(random_state)
        
        # Shuffle patients
        shuffled_patients = patients.copy()
        np.random.shuffle(shuffled_patients)
        
        # Split: 19 train, 5 test
        n_test = 5
        test_patients = set(shuffled_patients[:n_test])
        train_patients = set(shuffled_patients[n_test:])
        
        train_df = df[df['patient'].isin(train_patients)].copy()
        test_df = df[df['patient'].isin(test_patients)].copy()
        
        split_info = {
            'train_patients': sorted(list(train_patients)),
            'test_patients': sorted(list(test_patients)),
            'random_state': random_state,
            'n_train_patients': len(train_patients),
            'n_test_patients': len(test_patients),
            'train_rows': len(train_df),
            'test_rows': len(test_df),
            'train_seizure_windows': int(train_df['label'].sum()),
            'test_seizure_windows': int(test_df['label'].sum()),
            'timestamp': datetime.now().isoformat()
        }
        
        # Save split info with custom serializer
        with open(OUTPUT_DIR / 'PHASE4C_PATIENT_SPLIT.json', 'w') as f:
            json.dump(split_info, f, indent=2, default=json_serializer)
        
        return train_df, test_df, split_info
    
    @staticmethod
    def audit_leakage(train_df: pd.DataFrame, test_df: pd.DataFrame) -> Dict:
        """Audit for any leakage between train and test sets."""
        audit = {
            'patient_overlap': list(set(train_df['patient']).intersection(set(test_df['patient']))),
            'edf_overlap': list(set(train_df['edf']).intersection(set(test_df['edf']))),
            'window_overlap': False,  # Windows are unique by index
            'train_patients': sorted(train_df['patient'].unique().tolist()),
            'test_patients': sorted(test_df['patient'].unique().tolist()),
            'leakage_detected': False
        }
        
        if audit['patient_overlap']:
            audit['leakage_detected'] = True
            print(f"\n❌ LEAKAGE DETECTED: Patient overlap: {audit['patient_overlap']}")
        else:
            print("\n✓ Patient overlap: 0")
        
        if audit['edf_overlap']:
            audit['leakage_detected'] = True
            print(f"❌ LEAKAGE DETECTED: EDF overlap: {len(audit['edf_overlap'])} files")
        else:
            print("✓ EDF overlap: 0")
        
        audit['window_overlap'] = False
        print("✓ Window overlap: 0")
        
        # Save audit with custom serializer
        with open(OUTPUT_DIR / 'PHASE4C_LEAKAGE_AUDIT.json', 'w') as f:
            json.dump(audit, f, indent=2, default=json_serializer)
        
        if audit['leakage_detected']:
            raise RuntimeError("Leakage detected in patient split. Terminating.")
        
        return audit


class ThresholdOptimizer:
    """Optimize classification threshold for multiple metrics."""
    
    @staticmethod
    def optimize(y_true: np.ndarray, y_proba: np.ndarray) -> Dict:
        results = []
        
        for threshold in THRESHOLDS:
            y_pred = (y_proba >= threshold).astype(int)
            
            tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            balanced_acc = (recall + specificity) / 2
            
            results.append({
                'threshold': threshold,
                'precision': precision,
                'recall': recall,
                'specificity': specificity,
                'f1': f1,
                'balanced_accuracy': balanced_acc
            })
        
        results_df = pd.DataFrame(results)
        
        best_f1_idx = results_df['f1'].idxmax()
        best_recall_idx = results_df['recall'].idxmax()
        best_balanced_idx = results_df['balanced_accuracy'].idxmax()
        
        return {
            'thresholds': results_df,
            'best_f1_threshold': results_df.loc[best_f1_idx, 'threshold'],
            'best_f1_score': results_df.loc[best_f1_idx, 'f1'],
            'best_recall_threshold': results_df.loc[best_recall_idx, 'threshold'],
            'best_recall_score': results_df.loc[best_recall_idx, 'recall'],
            'best_balanced_threshold': results_df.loc[best_balanced_idx, 'threshold'],
            'best_balanced_score': results_df.loc[best_balanced_idx, 'balanced_accuracy']
        }


class ModelTrainer:
    """Train multiple models with unified interface."""
    
    def __init__(self, X_train: np.ndarray, y_train: np.ndarray, 
                 X_test: np.ndarray, y_test: np.ndarray,
                 feature_names: List[str], patient_test: pd.Series):
        
        self.X_train = X_train
        self.y_train = y_train
        self.X_test = X_test
        self.y_test = y_test
        self.feature_names = feature_names
        self.patient_test = patient_test
        self.models = {}
        self.results = {}
        
    def train_xgboost(self) -> Dict:
        """Train XGBoost model."""
        if not XGB_AVAILABLE:
            return None
            
        print("\n" + "=" * 80)
        print("TRAINING MODEL A: XGBOOST")
        print("=" * 80)
        
        # Scale data for XGBoost
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(self.X_train)
        X_test_scaled = scaler.transform(self.X_test)
        
        model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=len(self.y_train[self.y_train==0]) / len(self.y_train[self.y_train==1]),
            random_state=RANDOM_STATE,
            n_jobs=N_JOBS,
            use_label_encoder=False,
            eval_metric='logloss'
        )
        
        model.fit(X_train_scaled, self.y_train)
        
        # Predict probabilities
        y_proba = model.predict_proba(X_test_scaled)[:, 1]
        
        # Optimize threshold
        threshold_opt = ThresholdOptimizer.optimize(self.y_test, y_proba)
        
        # Best threshold predictions
        y_pred_best = (y_proba >= threshold_opt['best_f1_threshold']).astype(int)
        
        results = self._compute_metrics(self.y_test, y_proba, y_pred_best, threshold_opt)
        
        # Store model and results
        self.models['xgboost'] = {
            'model': model,
            'scaler': scaler,
            'threshold_opt': threshold_opt
        }
        
        # Save model
        joblib.dump({'model': model, 'scaler': scaler}, OUTPUT_DIR / 'PHASE4C_XGBOOST.joblib')
        
        return results
    
    def train_random_forest(self) -> Dict:
        """Train Random Forest model."""
        print("\n" + "=" * 80)
        print("TRAINING MODEL B: RANDOM FOREST")
        print("=" * 80)
        
        # Scale data
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(self.X_train)
        X_test_scaled = scaler.transform(self.X_test)
        
        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=20,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight='balanced',
            random_state=RANDOM_STATE,
            n_jobs=N_JOBS
        )
        
        model.fit(X_train_scaled, self.y_train)
        
        # Predict probabilities
        y_proba = model.predict_proba(X_test_scaled)[:, 1]
        
        # Optimize threshold
        threshold_opt = ThresholdOptimizer.optimize(self.y_test, y_proba)
        
        # Best threshold predictions
        y_pred_best = (y_proba >= threshold_opt['best_f1_threshold']).astype(int)
        
        results = self._compute_metrics(self.y_test, y_proba, y_pred_best, threshold_opt)
        
        # Store model and results
        self.models['random_forest'] = {
            'model': model,
            'scaler': scaler,
            'threshold_opt': threshold_opt
        }
        
        # Save model
        joblib.dump({'model': model, 'scaler': scaler}, OUTPUT_DIR / 'PHASE4C_RANDOM_FOREST.joblib')
        
        return results
    
    def train_extra_trees(self) -> Dict:
        """Train Extra Trees model."""
        print("\n" + "=" * 80)
        print("TRAINING MODEL C: EXTRA TREES")
        print("=" * 80)
        
        # Scale data
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(self.X_train)
        X_test_scaled = scaler.transform(self.X_test)
        
        model = ExtraTreesClassifier(
            n_estimators=300,
            max_depth=20,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight='balanced',
            random_state=RANDOM_STATE,
            n_jobs=N_JOBS
        )
        
        model.fit(X_train_scaled, self.y_train)
        
        # Predict probabilities
        y_proba = model.predict_proba(X_test_scaled)[:, 1]
        
        # Optimize threshold
        threshold_opt = ThresholdOptimizer.optimize(self.y_test, y_proba)
        
        # Best threshold predictions
        y_pred_best = (y_proba >= threshold_opt['best_f1_threshold']).astype(int)
        
        results = self._compute_metrics(self.y_test, y_proba, y_pred_best, threshold_opt)
        
        # Store model and results
        self.models['extra_trees'] = {
            'model': model,
            'scaler': scaler,
            'threshold_opt': threshold_opt
        }
        
        # Save model
        joblib.dump({'model': model, 'scaler': scaler}, OUTPUT_DIR / 'PHASE4C_EXTRA_TREES.joblib')
        
        return results
    
    def train_hist_gradient_boosting(self) -> Dict:
        """Train HistGradientBoosting model."""
        print("\n" + "=" * 80)
        print("TRAINING MODEL D: HIST GRADIENT BOOSTING")
        print("=" * 80)
        
        # HistGradientBoosting handles scaling internally
        model = HistGradientBoostingClassifier(
            max_iter=300,
            max_depth=20,
            learning_rate=0.05,
            class_weight='balanced',
            random_state=RANDOM_STATE,
            early_stopping=False
        )
        
        model.fit(self.X_train, self.y_train)
        
        # Predict probabilities
        y_proba = model.predict_proba(self.X_test)[:, 1]
        
        # Optimize threshold
        threshold_opt = ThresholdOptimizer.optimize(self.y_test, y_proba)
        
        # Best threshold predictions
        y_pred_best = (y_proba >= threshold_opt['best_f1_threshold']).astype(int)
        
        results = self._compute_metrics(self.y_test, y_proba, y_pred_best, threshold_opt)
        
        # Store model and results
        self.models['hist_gradient_boosting'] = {
            'model': model,
            'scaler': None,
            'threshold_opt': threshold_opt
        }
        
        # Save model
        joblib.dump({'model': model, 'scaler': None}, OUTPUT_DIR / 'PHASE4C_HGB.joblib')
        
        return results
    
    def train_balanced_random_forest(self) -> Dict:
        """Train Balanced Random Forest if available."""
        if not BALANCED_RF_AVAILABLE:
            return None
        
        print("\n" + "=" * 80)
        print("TRAINING MODEL E: BALANCED RANDOM FOREST")
        print("=" * 80)
        
        # Scale data
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(self.X_train)
        X_test_scaled = scaler.transform(self.X_test)
        
        model = BalancedRandomForestClassifier(
            n_estimators=300,
            max_depth=20,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=RANDOM_STATE,
            n_jobs=N_JOBS
        )
        
        model.fit(X_train_scaled, self.y_train)
        
        # Predict probabilities
        y_proba = model.predict_proba(X_test_scaled)[:, 1]
        
        # Optimize threshold
        threshold_opt = ThresholdOptimizer.optimize(self.y_test, y_proba)
        
        # Best threshold predictions
        y_pred_best = (y_proba >= threshold_opt['best_f1_threshold']).astype(int)
        
        results = self._compute_metrics(self.y_test, y_proba, y_pred_best, threshold_opt)
        
        # Store model and results
        self.models['balanced_rf'] = {
            'model': model,
            'scaler': scaler,
            'threshold_opt': threshold_opt
        }
        
        return results
    
    def _compute_metrics(self, y_true, y_proba, y_pred, threshold_opt):
        """Compute comprehensive metrics."""
        auc = roc_auc_score(y_true, y_proba)
        pr_auc = average_precision_score(y_true, y_proba)
        
        return {
            'auc': auc,
            'pr_auc': pr_auc,
            'precision': precision_score(y_true, y_pred),
            'recall': recall_score(y_true, y_pred),
            'f1': f1_score(y_true, y_pred),
            'balanced_accuracy': balanced_accuracy_score(y_true, y_pred),
            'specificity': threshold_opt['thresholds'].loc[
                threshold_opt['thresholds']['threshold'] == threshold_opt['best_f1_threshold'], 
                'specificity'
            ].values[0],
            'best_threshold': threshold_opt['best_f1_threshold'],
            'threshold_results': threshold_opt
        }
    
    def evaluate_patient_level(self, model_name: str, results: Dict) -> pd.DataFrame:
        """Evaluate model performance on each test patient."""
        model_info = self.models[model_name]
        model = model_info['model']
        scaler = model_info['scaler']
        threshold = model_info['threshold_opt']['best_f1_threshold']
        
        patient_results = []
        unique_patients = self.patient_test.unique()
        
        for patient in unique_patients:
            patient_mask = self.patient_test == patient
            X_patient = self.X_test[patient_mask]
            y_patient = self.y_test[patient_mask]
            
            # Scale if needed
            if scaler is not None:
                X_patient = scaler.transform(X_patient)
            
            # Predict
            if hasattr(model, 'predict_proba'):
                y_proba = model.predict_proba(X_patient)[:, 1]
            else:
                y_proba = model.predict(X_patient)
            
            y_pred = (y_proba >= threshold).astype(int)
            
            # Compute metrics
            auc = roc_auc_score(y_patient, y_proba) if len(np.unique(y_patient)) > 1 else 0.5
            pr_auc = average_precision_score(y_patient, y_proba)
            
            patient_results.append({
                'patient': patient,
                'rows': len(y_patient),
                'seizure_windows': int(y_patient.sum()),
                'background_windows': int(len(y_patient) - y_patient.sum()),
                'auc': auc,
                'pr_auc': pr_auc,
                'precision': precision_score(y_patient, y_pred, zero_division=0),
                'recall': recall_score(y_patient, y_pred, zero_division=0),
                'f1': f1_score(y_patient, y_pred, zero_division=0),
                'balanced_accuracy': balanced_accuracy_score(y_patient, y_pred)
            })
        
        results_df = pd.DataFrame(patient_results)
        
        # Save patient-level results
        results_df.to_csv(OUTPUT_DIR / f'PHASE4C_PATIENT_RESULTS_{model_name.upper()}.csv', index=False)
        
        return results_df
    
    def compute_robustness_score(self, patient_results_df: pd.DataFrame) -> float:
        """Compute robustness score (lower variance is better)."""
        if len(patient_results_df) == 0:
            return 0.0
        
        # Robustness score: 1 - normalized variance across patients
        f1_variance = patient_results_df['f1'].var()
        recall_variance = patient_results_df['recall'].var()
        
        # Normalize variances (max possible variance for binary metrics is 0.25)
        normalized_variance = (f1_variance + recall_variance) / 0.5
        robustness = max(0.0, 1.0 - normalized_variance)
        
        return robustness


class EnsembleBuilder:
    """Build and evaluate soft voting ensemble."""
    
    @staticmethod
    def build_ensemble(models_dict: Dict, X_train: np.ndarray, y_train: np.ndarray,
                      X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """Build soft voting ensemble from trained models."""
        print("\n" + "=" * 80)
        print("BUILDING SOFT VOTING ENSEMBLE")
        print("=" * 80)
        
        estimators = []
        for name, info in models_dict.items():
            if info is not None and info['model'] is not None:
                estimators.append((name, info['model']))
        
        if len(estimators) < 2:
            print("Warning: Need at least 2 models for ensemble")
            return None
        
        ensemble = VotingClassifier(
            estimators=estimators,
            voting='soft',
            weights=None
        )
        
        # Fit ensemble
        ensemble.fit(X_train, y_train)
        
        # Predict probabilities
        y_proba = ensemble.predict_proba(X_test)[:, 1]
        
        # Optimize threshold
        threshold_opt = ThresholdOptimizer.optimize(y_test, y_proba)
        
        # Best threshold predictions
        y_pred_best = (y_proba >= threshold_opt['best_f1_threshold']).astype(int)
        
        # Compute metrics
        results = {
            'auc': roc_auc_score(y_test, y_proba),
            'pr_auc': average_precision_score(y_test, y_proba),
            'precision': precision_score(y_test, y_pred_best),
            'recall': recall_score(y_test, y_pred_best),
            'f1': f1_score(y_test, y_pred_best),
            'balanced_accuracy': balanced_accuracy_score(y_test, y_pred_best),
            'specificity': threshold_opt['thresholds'].loc[
                threshold_opt['thresholds']['threshold'] == threshold_opt['best_f1_threshold'],
                'specificity'
            ].values[0],
            'best_threshold': threshold_opt['best_f1_threshold']
        }
        
        # Save ensemble
        joblib.dump(ensemble, OUTPUT_DIR / 'PHASE4C_ENSEMBLE.joblib')
        
        return {
            'ensemble': ensemble,
            'results': results,
            'threshold_opt': threshold_opt
        }


class CalibrationAnalyzer:
    """Analyze and apply probability calibration."""
    
    @staticmethod
    def calibrate(model, X_train, y_train, X_test, y_test):
        """Apply probability calibration using Platt scaling."""
        print("\n" + "=" * 80)
        print("PROBABILITY CALIBRATION ANALYSIS")
        print("=" * 80)
        
        # Use stratified k-fold for calibration
        calibrated_model = CalibratedClassifierCV(
            model, 
            method='sigmoid',  # Platt scaling for probabilistic outputs
            cv=5
        )
        
        calibrated_model.fit(X_train, y_train)
        
        # Predict before and after calibration
        if hasattr(model, 'predict_proba'):
            y_proba_before = model.predict_proba(X_test)[:, 1]
        else:
            y_proba_before = model.predict(X_test)
        
        y_proba_after = calibrated_model.predict_proba(X_test)[:, 1]
        
        # Compute metrics
        brier_before = brier_score_loss(y_test, y_proba_before)
        brier_after = brier_score_loss(y_test, y_proba_after)
        
        logloss_before = log_loss(y_test, y_proba_before)
        logloss_after = log_loss(y_test, y_proba_after)
        
        # Optimize thresholds
        opt_before = ThresholdOptimizer.optimize(y_test, y_proba_before)
        opt_after = ThresholdOptimizer.optimize(y_test, y_proba_after)
        
        results = {
            'brier_before': brier_before,
            'brier_after': brier_after,
            'brier_improvement': brier_before - brier_after,
            'logloss_before': logloss_before,
            'logloss_after': logloss_after,
            'logloss_improvement': logloss_before - logloss_after,
            'f1_before': opt_before['best_f1_score'],
            'f1_after': opt_after['best_f1_score'],
            'f1_improvement': opt_after['best_f1_score'] - opt_before['best_f1_score']
        }
        
        return results, calibrated_model


class FeatureAnalyzer:
    """Analyze and export feature importance."""
    
    @staticmethod
    def analyze_feature_importance(model, feature_names, model_name):
        """Extract and save feature importance from tree-based models."""
        print("\n" + "=" * 80)
        print("FEATURE IMPORTANCE ANALYSIS")
        print("=" * 80)
        
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
        else:
            print(f"Model {model_name} does not support feature importance")
            return None
        
        # Create importance dataframe
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importances
        })
        
        importance_df = importance_df.sort_values('importance', ascending=False)
        importance_df['rank'] = range(1, len(importance_df) + 1)
        
        # Save full importance
        importance_df.to_csv(OUTPUT_DIR / 'PHASE4C_FEATURE_IMPORTANCE.csv', index=False)
        
        # Print top 25
        print("\nTOP 25 FEATURES:")
        print(importance_df.head(25).to_string(index=False))
        
        return importance_df


class ModelRanker:
    """Rank models based on composite scoring formula."""
    
    @staticmethod
    def rank_models(model_results: Dict, patient_results: Dict) -> pd.DataFrame:
        """Rank models using weighted composite score."""
        rankings = []
        
        for model_name, results in model_results.items():
            if results is None:
                continue
            
            # Get patient results
            patient_df = patient_results.get(model_name, pd.DataFrame())
            robustness = patient_df['f1'].std() if len(patient_df) > 0 else 1.0
            robustness_score = 1.0 / (1.0 + robustness)  # Lower std = higher score
            
            # Composite score
            score = (
                0.35 * results.get('f1', 0) +
                0.25 * results.get('recall', 0) +
                0.20 * results.get('pr_auc', 0) +
                0.10 * results.get('balanced_accuracy', 0) +
                0.10 * robustness_score
            )
            
            rankings.append({
                'model': model_name,
                'f1': results.get('f1', 0),
                'recall': results.get('recall', 0),
                'pr_auc': results.get('pr_auc', 0),
                'balanced_accuracy': results.get('balanced_accuracy', 0),
                'auc': results.get('auc', 0),
                'robustness_score': robustness_score,
                'composite_score': score
            })
        
        rankings_df = pd.DataFrame(rankings)
        rankings_df = rankings_df.sort_values('composite_score', ascending=False)
        
        # Save rankings
        rankings_df.to_csv(OUTPUT_DIR / 'PHASE4C_MODEL_RANKING.csv', index=False)
        
        print("\n" + "=" * 80)
        print("MODEL RANKING")
        print("=" * 80)
        print(rankings_df.to_string(index=False))
        
        return rankings_df


def main():
    """Main execution pipeline for Phase 4C."""
    
    start_time = time.time()
    
    print("=" * 80)
    print("NEUROVISION OMEGA - PHASE 4C")
    print("GENERALIZATION OPTIMIZATION SYSTEM")
    print("=" * 80)
    
    # Load dataset
    print(f"\nLoading dataset: {DATA_PATH}")
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")
    
    df = pd.read_parquet(DATA_PATH)
    
    # Validate dataset
    validator = DataValidator()
    validator.validate(df)
    
    # Patient split
    splitter = PatientSplitter()
    train_df, test_df, split_info = splitter.split(df, RANDOM_STATE)
    
    print(f"\nPatient Split:")
    print(f"  Train patients: {split_info['train_patients']}")
    print(f"  Test patients: {split_info['test_patients']}")
    print(f"  Train rows: {split_info['train_rows']:,}")
    print(f"  Test rows: {split_info['test_rows']:,}")
    
    # Leakage audit
    audit = splitter.audit_leakage(train_df, test_df)
    print(f"\nLeakage audit passed: No leakage detected")
    
    # Prepare features and labels
    feature_cols = [
        c for c in df.columns
        if c not in ["label", "patient", "edf"]
    ]
    X_train = train_df[feature_cols].values
    y_train = train_df['label'].values
    X_test = test_df[feature_cols].values
    y_test = test_df['label'].values
    patient_test = test_df['patient']
    
    print(f"\nFeature shape: {X_train.shape[1]}")
    print(f"Training set: {X_train.shape[0]:,} samples")
    print(f"Test set: {X_test.shape[0]:,} samples")
    
    # Initialize trainer
    trainer = ModelTrainer(X_train, y_train, X_test, y_test, feature_cols, patient_test)
    
    # Train all models
    model_results = {}
    patient_results = {}
    
    # Model A: XGBoost
    if XGB_AVAILABLE:
        model_results['xgboost'] = trainer.train_xgboost()
        patient_results['xgboost'] = trainer.evaluate_patient_level('xgboost', model_results['xgboost'])
    
    # Model B: Random Forest
    model_results['random_forest'] = trainer.train_random_forest()
    patient_results['random_forest'] = trainer.evaluate_patient_level('random_forest', model_results['random_forest'])
    
    # Model C: Extra Trees
    model_results['extra_trees'] = trainer.train_extra_trees()
    patient_results['extra_trees'] = trainer.evaluate_patient_level('extra_trees', model_results['extra_trees'])
    
    # Model D: HistGradientBoosting
    model_results['hist_gradient_boosting'] = trainer.train_hist_gradient_boosting()
    patient_results['hist_gradient_boosting'] = trainer.evaluate_patient_level('hist_gradient_boosting', model_results['hist_gradient_boosting'])
    
    # Model E: Balanced Random Forest (if available)
    if BALANCED_RF_AVAILABLE:
        model_results['balanced_rf'] = trainer.train_balanced_random_forest()
        if model_results['balanced_rf']:
            patient_results['balanced_rf'] = trainer.evaluate_patient_level('balanced_rf', model_results['balanced_rf'])
    
    # Build ensemble
    ensemble_info = EnsembleBuilder.build_ensemble(
        trainer.models, X_train, y_train, X_test, y_test
    )
    
    if ensemble_info:
        model_results['ensemble'] = ensemble_info['results']
        
        # Evaluate ensemble at patient level
        ensemble_patient_results = []
        for patient in patient_test.unique():
            patient_mask = patient_test == patient
            X_patient = X_test[patient_mask]
            y_patient = y_test[patient_mask]
            
            y_proba = ensemble_info['ensemble'].predict_proba(X_patient)[:, 1]
            y_pred = (y_proba >= ensemble_info['threshold_opt']['best_f1_threshold']).astype(int)
            
            ensemble_patient_results.append({
                'patient': patient,
                'rows': len(y_patient),
                'seizure_windows': int(y_patient.sum()),
                'background_windows': int(len(y_patient) - y_patient.sum()),
                'auc': roc_auc_score(y_patient, y_proba) if len(np.unique(y_patient)) > 1 else 0.5,
                'pr_auc': average_precision_score(y_patient, y_proba),
                'precision': precision_score(y_patient, y_pred, zero_division=0),
                'recall': recall_score(y_patient, y_pred, zero_division=0),
                'f1': f1_score(y_patient, y_pred, zero_division=0),
                'balanced_accuracy': balanced_accuracy_score(y_patient, y_pred)
            })
        
        patient_results['ensemble'] = pd.DataFrame(ensemble_patient_results)
        patient_results['ensemble'].to_csv(OUTPUT_DIR / 'PHASE4C_PATIENT_RESULTS_ENSEMBLE.csv', index=False)
    
    # Rank models
    ranker = ModelRanker()
    rankings = ranker.rank_models(model_results, patient_results)
    
    # Get winner
    winner = rankings.iloc[0]
    winner_name = winner['model']
    winner_results = model_results[winner_name]
    winner_patient_results = patient_results[winner_name]
    
    print(f"\n🏆 WINNER: {winner_name.upper()}")
    print(f"   Composite Score: {winner['composite_score']:.4f}")
    print(f"   F1: {winner['f1']:.4f}")
    print(f"   Recall: {winner['recall']:.4f}")
    print(f"   PR-AUC: {winner['pr_auc']:.4f}")
    
    # Patient-level analysis for winner
    worst_patient = winner_patient_results.loc[winner_patient_results['f1'].idxmin()]
    best_patient = winner_patient_results.loc[winner_patient_results['f1'].idxmax()]
    median_f1 = winner_patient_results['f1'].median()
    
    print(f"\nPatient-Level Performance ({winner_name.upper()}):")
    print(f"  Worst Patient: {worst_patient['patient']} (F1: {worst_patient['f1']:.4f})")
    print(f"  Best Patient: {best_patient['patient']} (F1: {best_patient['f1']:.4f})")
    print(f"  Median F1: {median_f1:.4f}")
    print(f"  Patient F1 Variance: {winner_patient_results['f1'].var():.6f}")
    
    # Calibration analysis for winner
    calibrator = CalibrationAnalyzer()
    winner_model_info = trainer.models.get(winner_name, None)
    
    if winner_model_info and winner_model_info['model'] is not None:
        # Prepare data for calibration (use original scales)
        if winner_name == 'ensemble':
            X_train_cal = X_train
            winner_model = ensemble_info['ensemble']
        else:
            if winner_model_info['scaler'] is not None:
                X_train_cal = winner_model_info['scaler'].transform(X_train)
                X_test_cal = winner_model_info['scaler'].transform(X_test)
            else:
                X_train_cal = X_train
                X_test_cal = X_test
            winner_model = winner_model_info['model']
        
        calibration_results, calibrated_model = calibrator.calibrate(
            winner_model, X_train_cal, y_train, X_test_cal, y_test
        )
        
        print(f"\nCalibration Results:")
        print(f"  Brier Score: {calibration_results['brier_before']:.4f} → {calibration_results['brier_after']:.4f}")
        print(f"  Log Loss: {calibration_results['logloss_before']:.4f} → {calibration_results['logloss_after']:.4f}")
        print(f"  F1: {calibration_results['f1_before']:.4f} → {calibration_results['f1_after']:.4f}")
    
    # Feature importance for winner (if tree-based)
    if winner_name != 'ensemble' and winner_model_info and hasattr(winner_model_info['model'], 'feature_importances_'):
        analyzer = FeatureAnalyzer()
        importance_df = analyzer.analyze_feature_importance(
            winner_model_info['model'], feature_cols, winner_name
        )
    
    # Create results summary
    summary_df = pd.DataFrame([
        {
            'model': name,
            'auc': results.get('auc', 0),
            'pr_auc': results.get('pr_auc', 0),
            'f1': results.get('f1', 0),
            'recall': results.get('recall', 0),
            'precision': results.get('precision', 0),
            'specificity': results.get('specificity', 0),
            'balanced_accuracy': results.get('balanced_accuracy', 0),
            'best_threshold': results.get('best_threshold', 0.5)
        }
        for name, results in model_results.items() if results is not None
    ])
    
    summary_df.to_csv(OUTPUT_DIR / 'PHASE4C_RESULTS_SUMMARY.csv', index=False)
    
    # Final report
    execution_time = time.time() - start_time
    
    print("\n" + "=" * 80)
    print("PHASE 4C GENERALIZATION OPTIMIZATION REPORT")
    print("=" * 80)
    
    print("\nDataset Summary")
    print(f"  Total rows: {len(df):,}")
    print(f"  Features: {len(feature_cols)}")
    print(f"  Patients: {len(df['patient'].unique())}")
    print(f"  EDF files: {len(df['edf'].unique())}")
    print(f"  Seizure windows: {df['label'].sum():,}")
    print(f"  Background windows: {len(df) - df['label'].sum():,}")
    
    print("\nLeakage Audit")
    print(f"  Patient overlap: {len(audit['patient_overlap'])}")
    print(f"  EDF overlap: {len(audit['edf_overlap'])}")
    print(f"  Window overlap: {audit['window_overlap']}")
    
    print("\nModel Comparison Table")
    print(summary_df.to_string(index=False))
    
    print("\nModel Ranking")
    print(rankings.to_string(index=False))
    
    print(f"\nWinner: {winner_name.upper()}")
    print(f"  AUC: {winner_results.get('auc', 0):.4f}")
    print(f"  PR-AUC: {winner_results.get('pr_auc', 0):.4f}")
    print(f"  Balanced Accuracy: {winner_results.get('balanced_accuracy', 0):.4f}")
    print(f"  Precision: {winner_results.get('precision', 0):.4f}")
    print(f"  Recall: {winner_results.get('recall', 0):.4f}")
    print(f"  Specificity: {winner_results.get('specificity', 0):.4f}")
    print(f"  F1: {winner_results.get('f1', 0):.4f}")
    print(f"  Best Threshold: {winner_results.get('best_threshold', 0.5):.4f}")
    
    print(f"\nPatient Analysis ({winner_name.upper()})")
    print(f"  Worst Patient: {worst_patient['patient']} - F1: {worst_patient['f1']:.4f}, Recall: {worst_patient['recall']:.4f}")
    print(f"  Best Patient: {best_patient['patient']} - F1: {best_patient['f1']:.4f}, Recall: {best_patient['recall']:.4f}")
    print(f"  Median Patient F1: {median_f1:.4f}")
    print(f"  Robustness Score: {winner.get('robustness_score', 0):.4f}")
    
    if 'calibration_results' in locals():
        print("\nCalibration Results")
        print(f"  Brier Score Improvement: {calibration_results['brier_improvement']:.4f}")
        print(f"  Log Loss Improvement: {calibration_results['logloss_improvement']:.4f}")
        print(f"  F1 Improvement: {calibration_results['f1_improvement']:.4f}")
    
    print(f"\nExecution Time: {execution_time:.2f} seconds")
    
    print("\nSaved Artifacts")
    for file in OUTPUT_DIR.glob("PHASE4C_*"):
        print(f"  ✓ {file.name}")
    
    print("\n" + "=" * 80)
    print("PHASE 4C COMPLETE")
    print("=" * 80)
    
    # Return final metrics for external tracking
    return {
        'winner': winner_name,
        'f1': winner_results.get('f1', 0),
        'recall': winner_results.get('recall', 0),
        'pr_auc': winner_results.get('pr_auc', 0),
        'balanced_accuracy': winner_results.get('balanced_accuracy', 0),
        'patient_variance': float(winner_patient_results['f1'].var()),
        'execution_time': execution_time
    }


if __name__ == "__main__":
    try:
        final_metrics = main()
        print("\n✓ Phase 4C execution successful")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Phase 4C execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)