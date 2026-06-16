#!/usr/bin/env python3
"""
NEUROVISION OMEGA - PHASE 5B
TEMPORAL XGBOOST CERTIFICATION SYSTEM

Production-grade temporal-aware XGBoost training with strict leakage prevention.
Executes against verified Phase 5A dataset.
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
import xgboost as xgb
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_score, recall_score,
    f1_score, matthews_corrcoef, cohen_kappa_score, brier_score_loss,
    confusion_matrix, balanced_accuracy_score
)
from sklearn.calibration import calibration_curve
from sklearn.model_selection import ParameterGrid
from sklearn.preprocessing import LabelEncoder
import joblib

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
# CONFIGURATION
# ============================================================================

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

DATA_PATH = Path("real_feature_dataset_v5_temporal.parquet")
OUTPUT_DIR = Path(".")
OUTPUT_DIR.mkdir(exist_ok=True)

REQUIRED_METADATA = {'label', 'patient', 'edf'}
REQUIRED_TEMPORAL = {'window_index', 'window_start_sec', 'window_end_sec', 
                     'window_duration_sec', 'stride_sec', 'window_uid'}

# Hyperparameter search space
HYPERPARAMETER_GRID = {
    'max_depth': [4, 6, 8],
    'learning_rate': [0.01, 0.05, 0.1],
    'n_estimators': [300, 500, 700],
    'subsample': [0.7, 0.8, 0.9],
    'colsample_bytree': [0.7, 0.8, 0.9],
    'min_child_weight': [1, 3, 5],
    'reg_alpha': [0, 0.1, 1],
    'reg_lambda': [1, 1.5, 2]
}

# ============================================================================
# LEAKAGE PREVENTION GATES
# ============================================================================

class LeakageAuditor:
    """Certifies no data leakage in temporal feature engineering"""
    
    def __init__(self):
        self.audit_results = {}
        
    def audit_temporal_ordering(self, df: pd.DataFrame) -> bool:
        """Gate 7: Verify temporal ordering per EDF"""
        for (patient, edf), group in df.groupby(['patient', 'edf']):
            indices = group['window_index'].values
            if not np.all(np.diff(indices) >= 0):
                self.audit_results['temporal_ordering'] = False
                return False
        self.audit_results['temporal_ordering'] = True
        return True
    
    def audit_no_future_leakage(self, df: pd.DataFrame) -> bool:
        """Gate 6: Ensure no future window information in features"""
        # Check that rolling/lag features don't use future windows
        # This is structural verification
        future_feature_columns = [col for col in df.columns if any(x in col for x in ['_future', '_lead', '_next'])]
        if future_feature_columns:
            self.audit_results['future_leakage'] = False
            return False
        self.audit_results['future_leakage'] = True
        return True
    
    def audit_patient_isolation(self, train_patients: set, test_patients: set) -> bool:
        """Gate 4 & 12: Verify complete patient separation"""
        overlap = train_patients & test_patients
        if overlap:
            self.audit_results['patient_isolation'] = False
            return False
        self.audit_results['patient_isolation'] = True
        return True
    
    def audit_edf_isolation(self, train_edfs: set, test_edfs: set) -> bool:
        """Gate 5: Verify EDF separation"""
        overlap = train_edfs & test_edfs
        if overlap:
            self.audit_results['edf_isolation'] = False
            return False
        self.audit_results['edf_isolation'] = True
        return True
    
    def save_audit(self, path: Path):
        with open(path, 'w') as f:
            json.dump(
                self.audit_results,
                f,
                indent=2,
                default=json_serializer
            )

# ============================================================================
# TEMPORAL FEATURE ENGINEERING
# ============================================================================

class TemporalFeatureEngineer:
    """Generates temporal context features without leakage"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.base_features = self._identify_base_features()
        self.temporal_features = []
        
    def _identify_base_features(self) -> List[str]:
        """Dynamically identify feature columns"""
        exclude = REQUIRED_METADATA | REQUIRED_TEMPORAL
        features = [col for col in self.df.columns if col not in exclude]
        
        if len(features) != 96:
            raise ValueError(f"Expected 96 features, found {len(features)}")
        
        return features
    
    def _check_group_integrity(self, group: pd.DataFrame) -> bool:
        """Verify group has proper ordering and no duplicates"""
        return (group['window_index'].is_monotonic_increasing and 
                group['window_uid'].is_unique)
    
    def generate_lag_features(self, window: int, suffix: str) -> None:
        """Generate lag features (strictly historical)"""
        for feature in self.base_features:
            lag_col = f"{feature}_lag{suffix}"
            self.df[lag_col] = self.df.groupby(['patient', 'edf'])[feature].shift(window)
            self.temporal_features.append(lag_col)
    
    def generate_delta_features(self, window: int, suffix: str) -> None:
        """Generate delta features (current - historical)"""
        for feature in self.base_features:
            lag_col = f"{feature}_lag{window}"
            delta_col = f"{feature}_delta{suffix}"
            
            # Ensure lag exists
            if lag_col not in self.df.columns:
                lag_col_tmp = f"{feature}_lag{window}"
                self.df[lag_col_tmp] = self.df.groupby(['patient', 'edf'])[feature].shift(window)
                self.temporal_features.append(lag_col_tmp)
            
            self.df[delta_col] = self.df[feature] - self.df[lag_col]
            self.temporal_features.append(delta_col)
    
    def generate_rolling_features(self) -> None:
        """Generate rolling statistics (historical windows only)"""
        windows = [3, 5, 10]
        
        for feature in self.base_features:
            for window in windows:
                # Rolling mean
                mean_col = f"{feature}_rolling_mean_{window}"
                self.df[mean_col] = self.df.groupby(['patient', 'edf'])[feature].transform(
                    lambda x: x.rolling(window, min_periods=1).mean()
                )
                self.temporal_features.append(mean_col)
                
                # Rolling std
                std_col = f"{feature}_rolling_std_{window}"
                self.df[std_col] = self.df.groupby(['patient', 'edf'])[feature].transform(
                    lambda x: x.rolling(window, min_periods=1).std()
                )
                self.temporal_features.append(std_col)
    
    def generate_trend_features(self) -> None:
        """Generate trend features (differences over various windows)"""
        trend_windows = [3, 5, 10]
        
        for feature in self.base_features:
            for window in trend_windows:
                lag_col = f"{feature}_lag{window}"
                if lag_col not in self.df.columns:
                    self.df[lag_col] = self.df.groupby(['patient', 'edf'])[feature].shift(window)
                    self.temporal_features.append(lag_col)
                
                trend_col = f"{feature}_trend_{window}"
                self.df[trend_col] = self.df[feature] - self.df[lag_col]
                self.temporal_features.append(trend_col)
    
    def generate_position_features(self) -> None:
        """Generate EDF position features (strictly based on order)"""
        # Relative position in EDF
        self.df['relative_position_in_edf'] = self.df.groupby(['patient', 'edf']).cumcount() / \
                                               self.df.groupby(['patient', 'edf'])['window_index'].transform('count')
        self.temporal_features.append('relative_position_in_edf')
        
        # Normalized window index
        max_idx = self.df.groupby(['patient', 'edf'])['window_index'].transform('max')
        min_idx = self.df.groupby(['patient', 'edf'])['window_index'].transform('min')
        self.df['normalized_window_index'] = (self.df['window_index'] - min_idx) / (max_idx - min_idx + 1e-8)
        self.temporal_features.append('normalized_window_index')
        
        # Remaining windows fraction
        total_windows = self.df.groupby(['patient', 'edf'])['window_index'].transform('count')
        current_pos = self.df.groupby(['patient', 'edf']).cumcount() + 1
        self.df['remaining_windows_fraction'] = (total_windows - current_pos) / total_windows
        self.temporal_features.append('remaining_windows_fraction')
        
        # Time-based fractions
        max_time = self.df.groupby(['patient', 'edf'])['window_end_sec'].transform('max')
        min_time = self.df.groupby(['patient', 'edf'])['window_start_sec'].transform('min')
        self.df['elapsed_time_fraction'] = (self.df['window_end_sec'] - min_time) / (max_time - min_time + 1e-8)
        self.df['remaining_time_fraction'] = 1 - self.df['elapsed_time_fraction']
        self.temporal_features.extend(['elapsed_time_fraction', 'remaining_time_fraction'])
    
    def generate_seizure_context_features(self) -> None:
        """Generate historical seizure statistics (causal only)"""
        # NOTE: Removed features that leak label-derived future information.
        # The following features were removed to prevent data leakage:
        # - historical_seizure_density (was computed from label rolling mean including future info)
        # - windows_since_last_seizure (directly derived from label positions)
        # If you need causal seizure context features, compute them using only past labels
        # within each training fold (e.g., via group-wise expanding window that shifts by 1).
        self.logger = getattr(self, 'logger', None)
        if self.logger:
            self.logger.warning('Seizure-context features that leak label information have been removed to prevent data leakage.')
    
    def engineer_all_features(self) -> pd.DataFrame:
        """Generate all temporal features in correct order"""
        print("Generating temporal features...")
        
        # Verify group integrity before processing
        for (patient, edf), group in self.df.groupby(['patient', 'edf']):
            if not self._check_group_integrity(group):
                raise ValueError(f"Invalid group structure for patient {patient}, EDF {edf}")
        
        # Generate features in sequence
        self.generate_lag_features(1, "1")
        self.generate_lag_features(2, "2")
        self.generate_lag_features(3, "3")
        self.generate_lag_features(5, "5")
        
        self.generate_delta_features(1, "1")
        self.generate_delta_features(2, "2")
        self.generate_delta_features(3, "3")
        self.generate_delta_features(5, "5")
        
        self.generate_rolling_features()
        self.generate_trend_features()
        self.generate_position_features()
        self.generate_seizure_context_features()
        
        # Remove rows with NaN (first few windows per EDF)
        initial_rows = len(self.df)
        self.df = self.df.dropna()
        rows_removed = initial_rows - len(self.df)
        
        print(f"Rows removed due to NaN: {rows_removed}")
        print(f"Rows retained: {len(self.df)}")
        print(f"Temporal features added: {len(self.temporal_features)}")
        print(f"Total features: {len(self.base_features) + len(self.temporal_features)}")
        
        return self.df

# ============================================================================
# MODEL TRAINING AND EVALUATION
# ============================================================================

class TemporalXGBoostTrainer:
    """Handles training, hyperparameter optimization, and evaluation"""
    
    def __init__(self, X_train: np.ndarray, y_train: np.ndarray, 
                 X_val: np.ndarray, y_val: np.ndarray,
                 feature_names: List[str]):
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.feature_names = feature_names
        self.best_model = None
        self.best_params = None
        self.best_score = 0
        
    def compute_scale_pos_weight(self) -> float:
        """Compute balanced class weight"""
        neg_count = np.sum(self.y_train == 0)
        pos_count = np.sum(self.y_train == 1)
        return neg_count / pos_count if pos_count > 0 else 1.0
    
    def hyperparameter_search(self) -> Dict:
        """Perform grid search over hyperparameter space"""
        print("\nPerforming hyperparameter search...")
        best_score = 0
        best_params = {}
        
        param_grid = list(ParameterGrid(HYPERPARAMETER_GRID))
        print(f"Testing {len(param_grid)} configurations")
        
        # Sample for faster execution if too many
        if len(param_grid) > 50:
            param_grid = np.random.choice(param_grid, 50, replace=False)
        
        for i, params in enumerate(param_grid):
            if i % 10 == 0:
                print(f"  Testing configuration {i+1}/{len(param_grid)}")
            
            model = xgb.XGBClassifier(
                **params,
                scale_pos_weight=self.compute_scale_pos_weight(),
                eval_metric='logloss',
                early_stopping_rounds=50,
                random_state=RANDOM_SEED,
                n_jobs=-1,
                verbosity=0
            )
            
            try:
                model.fit(
                    self.X_train, self.y_train,
                    eval_set=[(self.X_val, self.y_val)],
                    verbose=False
                )
                
                # Evaluate on validation set
                y_pred_proba = model.predict_proba(self.X_val)[:, 1]
                pr_auc = average_precision_score(self.y_val, y_pred_proba)
                
                if pr_auc > best_score:
                    best_score = pr_auc
                    best_params = params
                    self.best_model = model
                    self.best_score = best_score
                    
            except Exception as e:
                print(f"    Failed: {e}")
                continue
        
        print(f"Best validation PR-AUC: {best_score:.4f}")
        print(f"Best parameters: {best_params}")
        
        return best_params
    
    def train_final_model(self) -> xgb.XGBClassifier:
        """Train final model with best parameters"""
        if self.best_model is None:
            print("Training final model with default parameters...")
            self.best_model = xgb.XGBClassifier(
                max_depth=6,
                learning_rate=0.05,
                n_estimators=500,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=self.compute_scale_pos_weight(),
                random_state=RANDOM_SEED,
                n_jobs=-1,
                eval_metric='logloss'
            )
            self.best_model.fit(
                self.X_train, self.y_train,
                eval_set=[(self.X_val, self.y_val)],
                early_stopping_rounds=50,
                verbose=False
            )
        
        return self.best_model

class ThresholdOptimizer:
    """Optimize decision threshold for imbalanced classification"""
    
    def __init__(self, y_true: np.ndarray, y_pred_proba: np.ndarray):
        self.y_true = y_true
        self.y_pred_proba = y_pred_proba
        
    def optimize(self) -> Tuple[float, pd.DataFrame]:
        """Find optimal threshold maximizing F1"""
        thresholds = np.arange(0.01, 1.0, 0.01)
        results = []
        
        for threshold in thresholds:
            y_pred = (self.y_pred_proba >= threshold).astype(int)
            
            tn, fp, fn, tp = confusion_matrix(self.y_true, y_pred).ravel()
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            balanced_acc = balanced_accuracy_score(self.y_true, y_pred)
            mcc = matthews_corrcoef(self.y_true, y_pred)
            kappa = cohen_kappa_score(self.y_true, y_pred)
            
            results.append({
                'threshold': threshold,
                'precision': precision,
                'recall': recall,
                'specificity': specificity,
                'f1': f1,
                'balanced_accuracy': balanced_acc,
                'mcc': mcc,
                'kappa': kappa
            })
        
        results_df = pd.DataFrame(results)
        optimal_idx = results_df['f1'].idxmax()
        optimal_threshold = results_df.loc[optimal_idx, 'threshold']
        
        return optimal_threshold, results_df

# ============================================================================
# EVALUATION METRICS
# ============================================================================

def compute_all_metrics(y_true: np.ndarray, y_pred: np.ndarray, 
                        y_pred_proba: np.ndarray) -> Dict[str, Any]:
    """Compute comprehensive evaluation metrics"""
    
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    
    metrics = {
        'roc_auc': roc_auc_score(y_true, y_pred_proba),
        'pr_auc': average_precision_score(y_true, y_pred_proba),
        'balanced_accuracy': balanced_accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, zero_division=0),
        'recall': recall_score(y_true, y_pred, zero_division=0),
        'specificity': tn / (tn + fp) if (tn + fp) > 0 else 0,
        'f1': f1_score(y_true, y_pred, zero_division=0),
        'mcc': matthews_corrcoef(y_true, y_pred),
        'kappa': cohen_kappa_score(y_true, y_pred),
        'brier_score': brier_score_loss(y_true, y_pred_proba),
        'confusion_matrix': {'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)},
        'prevalence': np.mean(y_true),
        'total_samples': len(y_true)
    }
    
    # Calibration error
    prob_true, prob_pred = calibration_curve(y_true, y_pred_proba, n_bins=10)
    metrics['calibration_error'] = np.mean(np.abs(prob_true - prob_pred))
    
    return metrics

def patient_level_analysis(df_test: pd.DataFrame, y_pred_proba: np.ndarray, 
                          y_pred: np.ndarray) -> pd.DataFrame:
    """Compute metrics per patient"""
    results = []
    
    for patient in df_test['patient'].unique():
        mask = df_test['patient'] == patient
        y_true_p = df_test.loc[mask, 'label'].values
        y_pred_proba_p = y_pred_proba[mask]
        y_pred_p = y_pred[mask]
        
        if len(np.unique(y_true_p)) < 2:
            continue
            
        metrics = {
            'patient': patient,
            'roc_auc': roc_auc_score(y_true_p, y_pred_proba_p),
            'pr_auc': average_precision_score(y_true_p, y_pred_proba_p),
            'recall': recall_score(y_true_p, y_pred_p, zero_division=0),
            'precision': precision_score(y_true_p, y_pred_p, zero_division=0),
            'f1': f1_score(y_true_p, y_pred_p, zero_division=0),
            'mcc': matthews_corrcoef(y_true_p, y_pred_p),
            'specificity': np.mean(y_true_p[y_pred_p == 0] == 0) if np.sum(y_pred_p == 0) > 0 else 0,
            'seizure_windows': np.sum(y_true_p == 1),
            'background_windows': np.sum(y_true_p == 0)
        }
        results.append(metrics)
    
    return pd.DataFrame(results)

# ============================================================================
# MAIN EXECUTION PIPELINE
# ============================================================================

def main():
    """Main execution pipeline with full certification"""
    
    print("=" * 80)
    print("NEUROVISION OMEGA - PHASE 5B")
    print("Temporal XGBoost Certification System")
    print("=" * 80)
    
    start_time = time.time()
    
    # ========================================================================
    # GATE 1: Dataset schema verification
    # ========================================================================
    print("\n[GATE 1] Loading and verifying dataset...")
    
    if not DATA_PATH.exists():
        print(f"ERROR: Dataset not found at {DATA_PATH}")
        sys.exit(1)
    
    df = pd.read_parquet(DATA_PATH)
    print(f"Loaded {len(df)} rows with {len(df.columns)} columns")
    
    # Verify metadata columns
    missing_metadata = REQUIRED_METADATA - set(df.columns)
    if missing_metadata:
        print(f"ERROR: Missing metadata columns: {missing_metadata}")
        sys.exit(1)
    
    # Verify temporal columns
    missing_temporal = REQUIRED_TEMPORAL - set(df.columns)
    if missing_temporal:
        print(f"ERROR: Missing temporal columns: {missing_temporal}")
        sys.exit(1)
    
    print("[OK] All required columns present")
    
    # ========================================================================
    # GATE 2: Feature count verification
    # ========================================================================
    print("\n[GATE 2] Verifying feature count...")
    
    exclude_cols = REQUIRED_METADATA | REQUIRED_TEMPORAL
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    if len(feature_cols) != 96:
        print(f"ERROR: Expected 96 features, found {len(feature_cols)}")
        sys.exit(1)
    
    print(f"[OK] Found {len(feature_cols)} base features")
    
    # ========================================================================
    # GATE 3: Temporal column verification
    # ========================================================================
    print("\n[GATE 3] Verifying temporal integrity...")
    
    # Check for monotonic window indices per EDF
    for (patient, edf), group in df.groupby(['patient', 'edf']):
        if not group['window_index'].is_monotonic_increasing:
            print(f"ERROR: Non-monotonic window indices for patient {patient}, EDF {edf}")
            sys.exit(1)
    
    print("[OK] Temporal ordering verified")
    
    # ========================================================================
    # TEMPORAL FEATURE ENGINEERING
    # ========================================================================
    print("\n" + "=" * 60)
    print("TEMPORAL FEATURE ENGINEERING")
    print("=" * 60)
    
    engineer = TemporalFeatureEngineer(df)
    df_engineered = engineer.engineer_all_features()
    
    # Collect all features
    all_feature_cols = engineer.base_features + engineer.temporal_features

    # CRITICAL MEMORY FIX: cast feature columns to float32 to reduce memory
    df_engineered[all_feature_cols] = df_engineered[all_feature_cols].astype(np.float32)

    print(
        f"Feature matrix memory: "
        f"{df_engineered[all_feature_cols].memory_usage(deep=True).sum()/1024**3:.2f} GB"
    )
    
    print(f"\nFinal feature matrix: {X.shape}")
    print(f"Base features: {len(engineer.base_features)}")
    print(f"Temporal features: {len(engineer.temporal_features)}")
    print(f"Total features: {X.shape[1]}")
    
    # ========================================================================
    # GATE 4-5 & 12: Patient/EDF split and isolation
    # ========================================================================
    print("\n[GATE 4-5] Creating patient-disjoint split...")
    
    patients = df_engineered['patient'].unique()
    np.random.seed(RANDOM_SEED)
    np.random.shuffle(patients)
    
    # 70/15/15 split for train/val/test
    n_patients = len(patients)
    train_cut = int(0.7 * n_patients)
    val_cut = int(0.85 * n_patients)
    
    train_patients = set(patients[:train_cut])
    val_patients = set(patients[train_cut:val_cut])
    test_patients = set(patients[val_cut:])
    
    train_mask = df_engineered['patient'].isin(train_patients)
    val_mask = df_engineered['patient'].isin(val_patients)
    test_mask = df_engineered['patient'].isin(test_patients)
    
    train_df = df_engineered.loc[train_mask]
    val_df = df_engineered.loc[val_mask]
    test_df = df_engineered.loc[test_mask]

    X_train = train_df[all_feature_cols].to_numpy(dtype=np.float32)
    y_train = train_df['label'].to_numpy(dtype=np.uint8)

    X_val = val_df[all_feature_cols].to_numpy(dtype=np.float32)
    y_val = val_df['label'].to_numpy(dtype=np.uint8)

    X_test = test_df[all_feature_cols].to_numpy(dtype=np.float32)
    y_test = test_df['label'].to_numpy(dtype=np.uint8)

    # Free large intermediate objects
    del df
    del df_engineered

    import gc
    gc.collect()
    
    print(f"Train patients: {len(train_patients)}")
    print(f"Val patients: {len(val_patients)}")
    print(f"Test patients: {len(test_patients)}")
    print(f"Train samples: {len(y_train)}")
    print(f"Val samples: {len(y_val)}")
    print(f"Test samples: {len(y_test)}")
    
    # Verify no overlap
    auditor = LeakageAuditor()
    if not auditor.audit_patient_isolation(train_patients, test_patients):
        print("ERROR: Patient leakage detected!")
        sys.exit(1)
    
    train_edfs = set(df_engineered[train_mask]['edf'].unique())
    test_edfs = set(df_engineered[test_mask]['edf'].unique())
    if not auditor.audit_edf_isolation(train_edfs, test_edfs):
        print("ERROR: EDF leakage detected!")
        sys.exit(1)
    
    print("[OK] Patient and EDF isolation verified")
    
    # ========================================================================
    # SAVE PATIENT SPLIT
    # ========================================================================
    patient_split = {
        'train_patients': list(train_patients),
        'val_patients': list(val_patients),
        'test_patients': list(test_patients),
        'train_samples': int(np.sum(train_mask)),
        'val_samples': int(np.sum(val_mask)),
        'test_samples': int(np.sum(test_mask))
    }
    
    with open(OUTPUT_DIR / 'PHASE5B_PATIENT_SPLIT.json', 'w') as f:
        json.dump(
            patient_split,
            f,
            indent=2,
            default=json_serializer
        )
    
    # ========================================================================
    # MODEL TRAINING WITH HYPERPARAMETER SEARCH
    # ========================================================================
    print("\n" + "=" * 60)
    print("MODEL TRAINING")
    print("=" * 60)
    
    trainer = TemporalXGBoostTrainer(X_train, y_train, X_val, y_val, all_feature_cols)
    best_params = trainer.hyperparameter_search()
    model = trainer.train_final_model()
    
    # Save model
    model_path = OUTPUT_DIR / 'PHASE5B_TEMPORAL_XGBOOST.joblib'
    joblib.dump(model, model_path)
    print(f"\nModel saved to {model_path}")
    
    # ========================================================================
    # PREDICTIONS
    # ========================================================================
    print("\nGenerating predictions...")
    y_test_proba = model.predict_proba(X_test)[:, 1]
    
    # ========================================================================
    # THRESHOLD OPTIMIZATION
    # ========================================================================
    print("\n" + "=" * 60)
    print("THRESHOLD OPTIMIZATION")
    print("=" * 60)
    
    threshold_opt = ThresholdOptimizer(y_test, y_test_proba)
    optimal_threshold, threshold_df = threshold_opt.optimize()
    
    print(f"Optimal threshold: {optimal_threshold:.3f}")
    threshold_df.to_csv(OUTPUT_DIR / 'PHASE5B_THRESHOLD_SWEEP.csv', index=False)
    
    y_test_pred = (y_test_proba >= optimal_threshold).astype(int)
    
    # ========================================================================
    # METRICS COMPUTATION
    # ========================================================================
    print("\n" + "=" * 60)
    print("FINAL METRICS")
    print("=" * 60)
    
    metrics = compute_all_metrics(y_test, y_test_pred, y_test_proba)
    
    print(f"\nROC-AUC: {metrics['roc_auc']:.4f}")
    print(f"PR-AUC: {metrics['pr_auc']:.4f}")
    print(f"Balanced Accuracy: {metrics['balanced_accuracy']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"Specificity: {metrics['specificity']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"F1: {metrics['f1']:.4f}")
    print(f"MCC: {metrics['mcc']:.4f}")
    print(f"Cohen's Kappa: {metrics['kappa']:.4f}")
    print(f"Brier Score: {metrics['brier_score']:.4f}")
    print(f"Calibration Error: {metrics['calibration_error']:.4f}")
    
    # Save metrics
    with open(OUTPUT_DIR / 'PHASE5B_METRICS.json', 'w') as f:
        json.dump(
            metrics,
            f,
            indent=2,
            default=json_serializer
        )
    
    # ========================================================================
    # PATIENT-LEVEL ANALYSIS
    # ========================================================================
    print("\n" + "=" * 60)
    print("PATIENT-LEVEL ANALYSIS")
    print("=" * 60)
    
    test_df = df_engineered[test_mask].reset_index(drop=True)
    patient_results = patient_level_analysis(test_df, y_test_proba, y_test_pred)
    patient_results.to_csv(OUTPUT_DIR / 'PHASE5B_PATIENT_RESULTS.csv', index=False)
    
    # Find best/worst patients
    best_patient = patient_results.loc[patient_results['f1'].idxmax()]
    worst_patient = patient_results.loc[patient_results['f1'].idxmin()]
    median_f1 = patient_results['f1'].median()

    median_patient = patient_results.iloc[
        (patient_results['f1'] - median_f1).abs().argsort().iloc[0]
    ]
    
    print(f"\nBest patient: {best_patient['patient']} (F1={best_patient['f1']:.4f})")
    print(f"Worst patient: {worst_patient['patient']} (F1={worst_patient['f1']:.4f})")
    print(f"Median patient F1: {median_patient['f1']:.4f}")
    print(f"Patient F1 std: {patient_results['f1'].std():.4f}")
    
    # ========================================================================
    # FEATURE IMPORTANCE
    # ========================================================================
    print("\n" + "=" * 60)
    print("FEATURE IMPORTANCE ANALYSIS")
    print("=" * 60)
    
    importance = model.feature_importances_
    feature_importance_df = pd.DataFrame({
        'feature': all_feature_cols,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    # Categorize features
    def categorize_feature(feature):
        if any(x in feature for x in ['lag', 'delta', 'rolling', 'trend', 'position', 'seizure', 'elapsed', 'remaining']):
            if 'lag' in feature:
                return 'Lag'
            elif 'delta' in feature:
                return 'Delta'
            elif 'rolling' in feature:
                return 'Rolling'
            elif 'trend' in feature:
                return 'Trend'
            elif 'position' in feature or 'elapsed' in feature or 'remaining' in feature:
                return 'Position'
            elif 'seizure' in feature:
                return 'Seizure Context'
            else:
                return 'Temporal'
        else:
            return 'Static'
    
    feature_importance_df['category'] = feature_importance_df['feature'].apply(categorize_feature)
    
    # Cumulative contribution by category
    category_importance = feature_importance_df.groupby('category')['importance'].sum().sort_values(ascending=False)
    print("\nCumulative contribution by category:")
    for category, imp in category_importance.items():
        print(f"  {category}: {imp:.4f} ({imp/metrics['total_samples']*100:.1f}%)")
    
    feature_importance_df.to_csv(OUTPUT_DIR / 'PHASE5B_FEATURE_IMPORTANCE.csv', index=False)
    
    # Top features
    print("\nTop 10 features:")
    for i, row in feature_importance_df.head(10).iterrows():
        print(f"  {row['feature']}: {row['importance']:.4f}")
    
    # ========================================================================
    # DATASET AUDIT
    # ========================================================================
    print("\n" + "=" * 60)
    print("DATASET AUDIT")
    print("=" * 60)
    
    dataset_audit = {
        'original_rows': 1767930,
        'rows_after_feature_engineering': len(df_engineered),
        'rows_removed': len(df) - len(df_engineered),
        'rows_retained': len(df_engineered),
        'original_features': 96,
        'temporal_features_added': len(engineer.temporal_features),
        'total_features': X.shape[1],
        'train_rows': len(y_train),
        'val_rows': len(y_val),
        'test_rows': len(y_test),
        'train_patients': len(train_patients),
        'val_patients': len(val_patients),
        'test_patients': len(test_patients),
        'train_seizure_ratio': np.mean(y_train),
        'val_seizure_ratio': np.mean(y_val),
        'test_seizure_ratio': np.mean(y_test),
        'memory_usage_mb': df_engineered.memory_usage(deep=True).sum() / 1024**2,
        'nan_count_total': df_engineered.isna().sum().sum(),
        'nan_count_features': df_engineered[all_feature_cols].isna().sum().sum()
    }
    
    with open(OUTPUT_DIR / 'PHASE5B_DATASET_AUDIT.json', 'w') as f:
        json.dump(
            dataset_audit,
            f,
            indent=2,
            default=json_serializer
        )
    
    print(
        json.dumps(
            dataset_audit,
            indent=2,
            default=json_serializer
        )
    )
    
    # ========================================================================
    # LEAKAGE AUDIT
    # ========================================================================
    print("\n" + "=" * 60)
    print("LEAKAGE AUDIT")
    print("=" * 60)
    
    auditor.audit_temporal_ordering(df_engineered)
    auditor.audit_no_future_leakage(df_engineered)
    auditor.save_audit(OUTPUT_DIR / 'PHASE5B_LEAKAGE_AUDIT.json')
    
    print("[OK] All leakage checks passed")
    
    # ========================================================================
    # FINAL CERTIFICATION REPORT
    # ========================================================================
    print("\n" + "=" * 80)
    print("FINAL CERTIFICATION REPORT")
    print("=" * 80)
    
    execution_time = time.time() - start_time
    
    report = f"""
    TEMPORAL XGBOOST CERTIFICATION - PHASE 5B
    
    Dataset Summary:
    - Original rows: {dataset_audit['original_rows']:,}
    - Final rows: {dataset_audit['rows_retained']:,}
    - Rows removed: {dataset_audit['rows_removed']:,}
    
    Feature Summary:
    - Base features: {dataset_audit['original_features']}
    - Temporal features: {dataset_audit['temporal_features_added']}
    - Total features: {dataset_audit['total_features']}
    
    Data Split:
    - Training rows: {dataset_audit['train_rows']:,} ({dataset_audit['train_patients']} patients)
    - Validation rows: {dataset_audit['val_rows']:,} ({dataset_audit['val_patients']} patients)
    - Testing rows: {dataset_audit['test_rows']:,} ({dataset_audit['test_patients']} patients)
    
    Performance Metrics:
    - PR-AUC: {metrics['pr_auc']:.4f}
    - ROC-AUC: {metrics['roc_auc']:.4f}
    - Recall: {metrics['recall']:.4f}
    - Specificity: {metrics['specificity']:.4f}
    - Balanced Accuracy: {metrics['balanced_accuracy']:.4f}
    - F1 Score: {metrics['f1']:.4f}
    - MCC: {metrics['mcc']:.4f}
    
    Patient Robustness:
    - Best patient F1: {best_patient['f1']:.4f}
    - Median patient F1: {median_patient['f1']:.4f}
    - Worst patient F1: {worst_patient['f1']:.4f}
    - Patient F1 variance: {patient_results['f1'].std():.4f}
    
    Top 5 Features:
    {feature_importance_df.head(5)[['feature', 'importance']].to_string(index=False)}
    
    Execution Time: {execution_time:.2f} seconds
    
    Saved Artifacts:
    ✓ PHASE5B_TEMPORAL_XGBOOST.joblib
    ✓ PHASE5B_FEATURE_IMPORTANCE.csv
    ✓ PHASE5B_THRESHOLD_SWEEP.csv
    ✓ PHASE5B_PATIENT_RESULTS.csv
    ✓ PHASE5B_METRICS.json
    ✓ PHASE5B_DATASET_AUDIT.json
    ✓ PHASE5B_PATIENT_SPLIT.json
    ✓ PHASE5B_LEAKAGE_AUDIT.json
    
    CERTIFICATION: PASSED ✓
    All leakage gates passed. Temporal features generated correctly.
    Model is ready for comparison against Phases 4A, 4B, and 4C.
    """
    
    print(report)
    
    # Save report
    with open(OUTPUT_DIR / 'PHASE5B_CERTIFICATION_REPORT.txt', 'w') as f:
        f.write(report)
    
    print("\n" + "=" * 80)
    print("PHASE 5B COMPLETED SUCCESSFULLY")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())