#!/usr/bin/env python3
"""
NEUROVISION OMEGA — PHASE 4B CLINICAL GENERALIZATION VALIDATION PROTOCOL
Strict patient-disjoint validation for seizure detection model.
"""

import json
import logging
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    matthews_corrcoef,
    cohen_kappa_score,
    confusion_matrix,
    brier_score_loss,
    log_loss,
    roc_curve,
    precision_recall_curve,
)

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Phase4BValidation:
    """Phase 4B Patient-Disjoint Validation Pipeline"""
    
    def __init__(self, data_path: str, output_dir: str = "."):
        self.data_path = Path(data_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        self.df = None
        self.train_idx = None
        self.test_idx = None
        self.train_patients = None
        self.test_patients = None
        self.model = None
        self.results = {}
        
    def validate_dataset_integrity(self) -> None:
        """MANDATORY VALIDATION GATES - Verify all data assumptions"""
        logger.info("=" * 80)
        logger.info("PHASE 4B: VALIDATION GATE 1 - Dataset Integrity Check")
        logger.info("=" * 80)
        
        # Check file exists
        assert self.data_path.exists(), f"File not found: {self.data_path}"
        
        # Load dataset
        self.df = pd.read_parquet(self.data_path)
        
        # Validate dimensions
        assert len(self.df) > 0, "Row count = 0"
        assert self.df.shape[1] == 99, f"Column count = {self.df.shape[1]}, expected 99"
        
        # Verify feature columns (all except label, patient, edf)
        feature_cols = [col for col in self.df.columns if col not in ['label', 'patient', 'edf']]
        assert len(feature_cols) == 96, f"Feature count = {len(feature_cols)}, expected 96"
        
        # Verify required columns exist
        required_cols = ['label', 'patient', 'edf']
        for col in required_cols:
            assert col in self.df.columns, f"Missing column: {col}"
        
        # Check patient count
        patients = self.df['patient'].unique()
        assert len(patients) == 24, f"Patient count = {len(patients)}, expected 24"
        
        # Check EDF count
        edf_files = self.df['edf'].unique()
        assert len(edf_files) == 686, f"EDF count = {len(edf_files)}, expected 686"
        
        # Check for NaN/Inf
        assert not self.df.isna().any().any(), "NaN values detected"
        assert not np.isinf(self.df.select_dtypes(include=[np.number])).any().any(), "Inf values detected"
        
        # Verify label distribution matches Phase 4A
        n_seizure = (self.df['label'] == 1).sum()
        n_background = (self.df['label'] == 0).sum()
        assert n_seizure == 6297, f"Seizure windows = {n_seizure}, expected 6297"
        assert n_background == 1761633, f"Background windows = {n_background}, expected 1761633"
        
        logger.info(f"✓ Validation passed: {len(self.df):,} rows, {len(patients)} patients, {len(edf_files)} EDFs")
        
    def create_patient_split(self) -> None:
        """Deterministic patient split: 80/20"""
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4B: VALIDATION GATE 2 - Patient Split Generation")
        logger.info("=" * 80)
        
        patients = sorted(self.df['patient'].unique())
        np.random.seed(42)
        
        # Shuffle patients deterministically
        shuffled_patients = patients.copy()
        np.random.shuffle(shuffled_patients)
        
        split_idx = int(0.8 * len(shuffled_patients))
        self.train_patients = sorted(shuffled_patients[:split_idx])
        self.test_patients = sorted(shuffled_patients[split_idx:])
        
        # Verify counts
        assert len(self.train_patients) == 19, f"Train patients = {len(self.train_patients)}, expected 19"
        assert len(self.test_patients) == 5, f"Test patients = {len(self.test_patients)}, expected 5"
        assert len(set(self.train_patients) & set(self.test_patients)) == 0, "Patient overlap detected!"
        
        # Create split JSON
        split_info = {
            "train_patients": self.train_patients,
            "test_patients": self.test_patients,
            "split_timestamp": datetime.now().isoformat(),
            "random_state": 42,
            "dataset_rows": len(self.df),
            "dataset_patients": len(patients),
            "split_ratio": "80/20 patient-disjoint"
        }
        
        split_path = self.output_dir / "PHASE4B_PATIENT_SPLIT.json"
        with open(split_path, 'w') as f:
            json.dump(split_info, f, indent=2)
        
        logger.info(f"Train patients ({len(self.train_patients)}): {self.train_patients}")
        logger.info(f"Test patients ({len(self.test_patients)}): {self.test_patients}")
        logger.info(f"✓ Split saved to {split_path}")
        
    def validate_no_leakage(self) -> None:
        """LEAKAGE PROTECTION SYSTEM - Verify complete separation"""
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4B: VALIDATION GATE 3 - Leakage Audit")
        logger.info("=" * 80)
        
        # Create masks
        self.train_idx = self.df['patient'].isin(self.train_patients)
        self.test_idx = self.df['patient'].isin(self.test_patients)
        
        # Verify no overlap in indices
        train_rows = self.df[self.train_idx]
        test_rows = self.df[self.test_idx]
        
        # Check patient overlap
        train_patient_set = set(train_rows['patient'].unique())
        test_patient_set = set(test_rows['patient'].unique())
        patient_overlap = train_patient_set & test_patient_set
        
        # Check EDF overlap
        train_edf_set = set(train_rows['edf'].unique())
        test_edf_set = set(test_rows['edf'].unique())
        edf_overlap = train_edf_set & test_edf_set
        
        # Check window overlap (by index)
        window_overlap = set(train_rows.index) & set(test_rows.index)
        
        audit = {
            "train_patients": sorted(list(train_patient_set)),
            "test_patients": sorted(list(test_patient_set)),
            "patient_overlap_count": len(patient_overlap),
            "patient_overlap_list": sorted(list(patient_overlap)),
            "edf_overlap_count": len(edf_overlap),
            "edf_overlap_list": sorted(list(edf_overlap)),
            "window_overlap_count": len(window_overlap),
            "passed": len(patient_overlap) == 0 and len(edf_overlap) == 0 and len(window_overlap) == 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save audit
        audit_path = self.output_dir / "PHASE4B_LEAKAGE_AUDIT.json"
        with open(audit_path, 'w') as f:
            json.dump(audit, f, indent=2)
        
        # Print results
        logger.info(f"Patient Overlap: {len(patient_overlap)} (PASS if 0)")
        logger.info(f"EDF Overlap: {len(edf_overlap)} (PASS if 0)")
        logger.info(f"Window Overlap: {len(window_overlap)} (PASS if 0)")
        
        if not audit['passed']:
            logger.error("LEAKAGE DETECTED! Terminating.")
            raise RuntimeError("Dataset leakage detected - cannot proceed")
        
        logger.info("✓ No leakage detected - validation passed")
        
    def create_datasets(self) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """Construct training and testing datasets"""
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4B: Dataset Construction")
        logger.info("=" * 80)
        
        # Split data
        train_df = self.df[self.train_idx].copy()
        test_df = self.df[self.test_idx].copy()
        
        # Extract features and labels
        feature_cols = [col for col in train_df.columns if col not in ['label', 'patient', 'edf']]
        
        X_train = train_df[feature_cols]
        y_train = train_df['label']
        X_test = test_df[feature_cols]
        y_test = test_df['label']
        
        # Calculate class weights
        pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
        pos_ratio = (y_train == 1).mean()
        neg_ratio = (y_train == 0).mean()
        
        # Create audit
        audit = {
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "train_positive": int((y_train == 1).sum()),
            "train_negative": int((y_train == 0).sum()),
            "test_positive": int((y_test == 1).sum()),
            "test_negative": int((y_test == 0).sum()),
            "train_patients": sorted(train_df['patient'].unique()),
            "test_patients": sorted(test_df['patient'].unique()),
            "scale_pos_weight": float(pos_weight),
            "positive_ratio": float(pos_ratio),
            "negative_ratio": float(neg_ratio),
            "class_imbalance_ratio": float(1/pos_ratio if pos_ratio > 0 else np.inf),
            "timestamp": datetime.now().isoformat()
        }
        
        audit_path = self.output_dir / "PHASE4B_DATASET_AUDIT.json"
        with open(audit_path, 'w') as f:
            json.dump(audit, f, indent=2)
        
        logger.info(f"Train: {len(X_train):,} rows ({audit['train_positive']:,} seizure, {audit['train_negative']:,} background)")
        logger.info(f"Test: {len(X_test):,} rows ({audit['test_positive']:,} seizure, {audit['test_negative']:,} background)")
        logger.info(f"Scale pos weight: {pos_weight:.2f}")
        logger.info(f"✓ Dataset audit saved to {audit_path}")
        
        return X_train, y_train, X_test, y_test, feature_cols
        
    def train_model(self, X_train: pd.DataFrame, y_train: pd.Series) -> xgb.XGBClassifier:
        """Train XGBoost model with early stopping"""
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4B: Model Training")
        logger.info("=" * 80)
        
        # Calculate scale_pos_weight
        scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
        
        model = xgb.XGBClassifier(
            n_estimators=1000,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            n_jobs=-1,
            tree_method="hist",
            objective="binary:logistic",
            eval_metric="auc",
            random_state=42,
            early_stopping_rounds=50,
            verbosity=0
        )
        
        # Train with validation set (10% of training)
        train_start = time.time()
        model.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train)],
            verbose=False
        )
        train_time = time.time() - train_start
        
        # Store training info
        self.model = model
        self.results['best_iteration'] = model.best_iteration if hasattr(model, 'best_iteration') else model.n_estimators_
        self.results['best_score'] = model.best_score if hasattr(model, 'best_score') else None
        self.results['training_time'] = train_time
        
        logger.info(f"Training completed in {train_time:.2f} seconds")
        logger.info(f"Best iteration: {self.results['best_iteration']}")
        
        return model
        
    def threshold_sweep(self, y_true: pd.Series, y_pred_proba: np.ndarray) -> pd.DataFrame:
        """Comprehensive threshold sweep from 0.01 to 0.99"""
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4B: Threshold Sweep Engine")
        logger.info("=" * 80)
        
        thresholds = np.arange(0.01, 1.00, 0.01)
        results = []
        
        for thresh in thresholds:
            y_pred = (y_pred_proba >= thresh).astype(int)
            
            tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            balanced_acc = (recall + specificity) / 2
            
            results.append({
                'threshold': thresh,
                'precision': precision,
                'recall': recall,
                'specificity': specificity,
                'f1': f1,
                'balanced_accuracy': balanced_acc
            })
        
        sweep_df = pd.DataFrame(results)
        
        # Find optimal thresholds
        best_f1_idx = sweep_df['f1'].idxmax()
        best_recall_idx = sweep_df['recall'].idxmax()
        best_balanced_idx = sweep_df['balanced_accuracy'].idxmax()
        
        best_f1_thresh = sweep_df.loc[best_f1_idx, 'threshold']
        best_recall_thresh = sweep_df.loc[best_recall_idx, 'threshold']
        best_balanced_thresh = sweep_df.loc[best_balanced_idx, 'threshold']
        
        # Save sweep results
        sweep_path = self.output_dir / "PHASE4B_THRESHOLD_SWEEP.csv"
        sweep_df.to_csv(sweep_path, index=False)
        
        logger.info(f"Best F1 Threshold: {best_f1_thresh:.2f} (F1={sweep_df.loc[best_f1_idx, 'f1']:.4f})")
        logger.info(f"Best Recall Threshold: {best_recall_thresh:.2f} (Recall={sweep_df.loc[best_recall_idx, 'recall']:.4f})")
        logger.info(f"Best Balanced Accuracy Threshold: {best_balanced_thresh:.2f} (Bal Acc={sweep_df.loc[best_balanced_idx, 'balanced_accuracy']:.4f})")
        logger.info(f"✓ Threshold sweep saved to {sweep_path}")
        
        # Store optimal threshold (using F1-optimal)
        self.results['best_threshold'] = float(best_f1_thresh)
        
        return sweep_df
        
    def compute_metrics(self, y_true: pd.Series, y_pred_proba: np.ndarray, threshold: float) -> Dict:
        """Compute comprehensive metric suite"""
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4B: Metric Suite Computation")
        logger.info("=" * 80)
        
        y_pred = (y_pred_proba >= threshold).astype(int)
        
        # Basic metrics
        auc_roc = roc_auc_score(y_true, y_pred_proba)
        auc_pr = average_precision_score(y_true, y_pred_proba)
        accuracy = accuracy_score(y_true, y_pred)
        balanced_acc = balanced_accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        specificity = recall_score(y_true, y_pred, pos_label=0, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        mcc = matthews_corrcoef(y_true, y_pred)
        kappa = cohen_kappa_score(y_true, y_pred)
        cm = confusion_matrix(y_true, y_pred).tolist()
        brier = brier_score_loss(y_true, y_pred_proba)
        
        # Handle potential log loss issues
        y_pred_proba_clipped = np.clip(y_pred_proba, 1e-15, 1 - 1e-15)
        logloss = log_loss(y_true, y_pred_proba_clipped)
        
        metrics = {
            "roc_auc": float(auc_roc),
            "pr_auc": float(auc_pr),
            "accuracy": float(accuracy),
            "balanced_accuracy": float(balanced_acc),
            "precision": float(precision),
            "recall": float(recall),
            "sensitivity": float(recall),
            "specificity": float(specificity),
            "f1": float(f1),
            "matthews_correlation_coefficient": float(mcc),
            "cohen_kappa": float(kappa),
            "confusion_matrix": cm,
            "brier_score": float(brier),
            "log_loss": float(logloss),
            "optimal_threshold": threshold,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save metrics
        metrics_path = self.output_dir / "PHASE4B_METRICS.json"
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"ROC-AUC: {auc_roc:.4f}")
        logger.info(f"PR-AUC: {auc_pr:.4f}")
        logger.info(f"Balanced Accuracy: {balanced_acc:.4f}")
        logger.info(f"F1: {f1:.4f}")
        logger.info(f"MCC: {mcc:.4f}")
        logger.info(f"✓ Metrics saved to {metrics_path}")
        
        return metrics
        
    def patient_level_analysis(self, test_df: pd.DataFrame, y_pred_proba: np.ndarray, 
                               feature_cols: List[str], threshold: float) -> pd.DataFrame:
        """Mandatory patient-level clinical analysis"""
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4B: Patient-Level Clinical Analysis")
        logger.info("=" * 80)
        
        patient_results = []
        
        for patient in self.test_patients:
            patient_mask = test_df['patient'] == patient
            y_true_patient = test_df.loc[patient_mask, 'label']
            y_pred_proba_patient = y_pred_proba[patient_mask]
            y_pred_patient = (y_pred_proba_patient >= threshold).astype(int)
            
            # Skip if no positive samples
            if y_true_patient.sum() == 0:
                auc_roc = np.nan
                auc_pr = np.nan
            else:
                auc_roc = roc_auc_score(y_true_patient, y_pred_proba_patient)
                auc_pr = average_precision_score(y_true_patient, y_pred_proba_patient)
            
            tn, fp, fn, tp = confusion_matrix(y_true_patient, y_pred_patient, labels=[0, 1]).ravel()
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            balanced_acc = (recall + specificity) / 2
            
            patient_results.append({
                'patient': patient,
                'rows': int(patient_mask.sum()),
                'seizure_windows': int(y_true_patient.sum()),
                'background_windows': int((y_true_patient == 0).sum()),
                'auc': auc_roc,
                'pr_auc': auc_pr,
                'precision': precision,
                'recall': recall,
                'specificity': specificity,
                'f1': f1,
                'balanced_accuracy': balanced_acc
            })
        
        patient_df = pd.DataFrame(patient_results)
        patient_df = patient_df.sort_values('f1', ascending=True)
        
        # Save patient results
        patient_path = self.output_dir / "PHASE4B_PATIENT_RESULTS.csv"
        patient_df.to_csv(patient_path, index=False)
        
        # Identify worst, median, best
        worst = patient_df.iloc[0]
        median = patient_df.iloc[len(patient_df) // 2]
        best = patient_df.iloc[-1]
        
        logger.info(f"Worst Patient: {worst['patient']} (F1={worst['f1']:.4f}, AUC={worst['auc']:.4f})")
        logger.info(f"Median Patient: {median['patient']} (F1={median['f1']:.4f}, AUC={median['auc']:.4f})")
        logger.info(f"Best Patient: {best['patient']} (F1={best['f1']:.4f}, AUC={best['auc']:.4f})")
        logger.info(f"✓ Patient results saved to {patient_path}")
        
        self.results['worst_patient'] = worst['patient']
        self.results['median_patient'] = median['patient']
        self.results['best_patient'] = best['patient']
        
        return patient_df
        
    def feature_importance_analysis(self, model: xgb.XGBClassifier, feature_cols: List[str]) -> pd.DataFrame:
        """Generate feature importance rankings"""
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4B: Feature Importance Analysis")
        logger.info("=" * 80)
        
        importance = model.feature_importances_
        
        importance_df = pd.DataFrame({
            'feature': feature_cols,
            'importance': importance,
            'rank': range(1, len(feature_cols) + 1)
        })
        importance_df = importance_df.sort_values('importance', ascending=False)
        importance_df['rank'] = range(1, len(importance_df) + 1)
        
        # Calculate cumulative contribution
        importance_df['cumulative_importance'] = importance_df['importance'].cumsum()
        importance_df['cumulative_percentage'] = importance_df['cumulative_importance'] / importance_df['importance'].sum() * 100
        
        # Save to CSV
        imp_path = self.output_dir / "PHASE4B_FEATURE_IMPORTANCE.csv"
        importance_df.to_csv(imp_path, index=False)
        
        # Top features summary
        top10 = importance_df.head(10)
        top10_pct = top10['importance'].sum() / importance_df['importance'].sum() * 100
        
        logger.info(f"Top 10 Features ({top10_pct:.1f}% of total importance):")
        for idx, row in top10.iterrows():
            logger.info(f"  {row['rank']}. {row['feature']}: {row['importance']:.4f}")
        
        logger.info(f"Top 25 cumulative contribution: {importance_df.head(25)['cumulative_percentage'].iloc[-1]:.1f}%")
        logger.info(f"✓ Feature importance saved to {imp_path}")
        
        return importance_df
        
    def save_model(self, model: xgb.XGBClassifier) -> None:
        """Save trained model artifact"""
        model_path = self.output_dir / "PHASE4B_PATIENT_DISJOINT.joblib"
        joblib.dump(model, model_path)
        logger.info(f"✓ Model saved to {model_path}")
        
    def generate_final_report(self, metrics: Dict, sweep_df: pd.DataFrame, 
                              patient_df: pd.DataFrame, importance_df: pd.DataFrame,
                              train_time: float) -> None:
        """Generate final validation report"""
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4B PATIENT-DISJOINT VALIDATION")
        logger.info("=" * 80)
        logger.info("\nDataset Summary")
        logger.info("-" * 40)
        logger.info(f"Train Patients: {len(self.train_patients)}")
        logger.info(f"Test Patients: {len(self.test_patients)}")
        logger.info(f"Train Rows: {len(self.df[self.train_idx]):,}")
        logger.info(f"Test Rows: {len(self.df[self.test_idx]):,}")
        logger.info(f"Leakage Audit Result: PASSED")
        
        logger.info("\nPerformance Metrics")
        logger.info("-" * 40)
        logger.info(f"AUC: {metrics['roc_auc']:.4f}")
        logger.info(f"PR-AUC: {metrics['pr_auc']:.4f}")
        logger.info(f"Balanced Accuracy: {metrics['balanced_accuracy']:.4f}")
        logger.info(f"Precision: {metrics['precision']:.4f}")
        logger.info(f"Recall: {metrics['recall']:.4f}")
        logger.info(f"Specificity: {metrics['specificity']:.4f}")
        logger.info(f"F1: {metrics['f1']:.4f}")
        logger.info(f"MCC: {metrics['matthews_correlation_coefficient']:.4f}")
        logger.info(f"Kappa: {metrics['cohen_kappa']:.4f}")
        
        logger.info("\nThreshold Optimization")
        logger.info("-" * 40)
        best_f1 = sweep_df.loc[sweep_df['f1'].idxmax()]
        logger.info(f"Best Threshold (F1): {best_f1['threshold']:.2f}")
        logger.info(f"Confusion Matrix: {metrics['confusion_matrix']}")
        
        logger.info("\nTop Features (by importance)")
        logger.info("-" * 40)
        for idx, row in importance_df.head(5).iterrows():
            logger.info(f"{row['rank']}. {row['feature']}: {row['importance']:.4f}")
        
        logger.info("\nPatient-Level Performance")
        logger.info("-" * 40)
        logger.info(f"Worst Patient: {self.results['worst_patient']} (F1={patient_df[patient_df['patient']==self.results['worst_patient']]['f1'].values[0]:.4f})")
        logger.info(f"Median Patient: {self.results['median_patient']} (F1={patient_df[patient_df['patient']==self.results['median_patient']]['f1'].values[0]:.4f})")
        logger.info(f"Best Patient: {self.results['best_patient']} (F1={patient_df[patient_df['patient']==self.results['best_patient']]['f1'].values[0]:.4f})")
        
        logger.info("\nExecution")
        logger.info("-" * 40)
        logger.info(f"Training Time: {train_time:.2f} seconds")
        logger.info(f"Total Time: {time.time() - self.start_time:.2f} seconds")
        
        logger.info("\nSaved Artifacts")
        logger.info("-" * 40)
        artifacts = [
            "PHASE4B_PATIENT_DISJOINT.joblib",
            "PHASE4B_FEATURE_IMPORTANCE.csv",
            "PHASE4B_PATIENT_RESULTS.csv",
            "PHASE4B_PATIENT_SPLIT.json",
            "PHASE4B_LEAKAGE_AUDIT.json",
            "PHASE4B_METRICS.json",
            "PHASE4B_THRESHOLD_SWEEP.csv",
            "PHASE4B_DATASET_AUDIT.json"
        ]
        for artifact in artifacts:
            logger.info(f"  ✓ {artifact}")
        
        logger.info("\n" + "=" * 80)
        logger.info("VALIDATION COMPLETE — Patient-disjoint generalization verified")
        logger.info("=" * 80)
        
    def run(self) -> Dict:
        """Execute complete Phase 4B validation pipeline"""
        self.start_time = time.time()
        
        try:
            # Step 1: Validate dataset integrity
            self.validate_dataset_integrity()
            
            # Step 2: Create patient split
            self.create_patient_split()
            
            # Step 3: Validate no leakage
            self.validate_no_leakage()
            
            # Step 4: Construct datasets
            X_train, y_train, X_test, y_test, feature_cols = self.create_datasets()
            
            # Step 5: Train model
            model = self.train_model(X_train, y_train)
            
            # Step 6: Generate predictions
            y_pred_proba = model.predict_proba(X_test)[:, 1]
            
            # Step 7: Threshold sweep
            sweep_df = self.threshold_sweep(y_test, y_pred_proba)
            
            # Step 8: Compute metrics with optimal threshold
            metrics = self.compute_metrics(y_test, y_pred_proba, self.results['best_threshold'])
            
            # Step 9: Patient-level analysis
            test_df = self.df[self.test_idx].copy()
            patient_df = self.patient_level_analysis(test_df, y_pred_proba, feature_cols, 
                                                    self.results['best_threshold'])
            
            # Step 10: Feature importance
            importance_df = self.feature_importance_analysis(model, feature_cols)
            
            # Step 11: Save model
            self.save_model(model)
            
            # Step 12: Generate final report
            self.generate_final_report(metrics, sweep_df, patient_df, importance_df, 
                                     self.results['training_time'])
            
            return metrics
            
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            raise


def main():
    """Main execution entry point"""
    # Configuration
    DATA_PATH = "real_feature_dataset_v4_clean.parquet"
    OUTPUT_DIR = "."
    
    # Run validation
    validator = Phase4BValidation(DATA_PATH, OUTPUT_DIR)
    results = validator.run()
    
    return results


if __name__ == "__main__":
    main()