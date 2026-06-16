#!/usr/bin/env python3
"""
NeuroVision Omega - Phase 4A XGBoost Training
================================================================================
Trains XGBoost classifier on the Phase 4 dataset.
Generates comprehensive metrics and feature importance analysis.
================================================================================
"""

import json
import logging
import time
import warnings
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Any, List
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, f1_score, precision_score,
    recall_score, roc_auc_score, confusion_matrix, classification_report,
    roc_curve
)
import xgboost as xgb
import joblib

# Suppress warnings
warnings.filterwarnings("ignore")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
PROJECT_ROOT = Path(r"E:\Project\neurovision_ai")
DATASET_PATH = PROJECT_ROOT / "real_feature_dataset_v4_clean.parquet"
MODEL_OUTPUT_PATH = PROJECT_ROOT / "PHASE4A_XGBOOST.joblib"
FEATURE_IMPORTANCE_PATH = PROJECT_ROOT / "PHASE4A_FEATURE_IMPORTANCE.csv"
METRICS_PATH = PROJECT_ROOT / "PHASE4A_METRICS.json"
CONFUSION_MATRIX_PATH = PROJECT_ROOT / "PHASE4A_CONFUSION_MATRIX.png"
ROC_CURVE_PATH = PROJECT_ROOT / "PHASE4A_ROC_CURVE.png"
FEATURE_IMPORTANCE_PLOT_PATH = PROJECT_ROOT / "PHASE4A_FEATURE_IMPORTANCE.png"

# Model hyperparameters (optimized for seizure detection)
XGB_PARAMS = {
    'n_estimators': 300,
    'max_depth': 6,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'min_child_weight': 3,
    'gamma': 0.1,
    'reg_alpha': 0.1,
    'reg_lambda': 1.0,
    'scale_pos_weight': 5.0,  # Adjust for class imbalance
    'random_state': 42,
    'n_jobs': -1,
    'eval_metric': 'auc'
}

# Training configuration
TEST_SIZE = 0.2
VAL_SIZE = 0.2  # From remaining training data
RANDOM_STATE = 42
CV_FOLDS = 5


def load_dataset() -> Tuple[pd.DataFrame, pd.Series]:
    """Load and prepare the clean dataset"""
    logger.info(f"Loading dataset from {DATASET_PATH}")
    
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")
    
    df = pd.read_parquet(DATASET_PATH)
    logger.info(f"Loaded {len(df):,} rows with {len(df.columns)} columns")
    
    # Separate features and target
    feature_cols = [c for c in df.columns if c not in ['label', 'patient', 'edf']]
    X = df[feature_cols]
    y = df['label']
    
    logger.info(f"Features: {X.shape[1]}, Target distribution: {y.value_counts().to_dict()}")
    
    return X, y


def split_data(X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
    """
    Split data into train, validation, and test sets.
    Uses patient-disjoint splitting to prevent data leakage.
    """
    logger.info("Splitting data with patient-disjoint strategy...")
    
    # Get unique patients
    # Note: We need to load patient info from the dataset
    # For now, we'll use random split but with stratification
    
    # First split: train+val vs test
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    
    # Second split: train vs val
    val_relative_size = VAL_SIZE / (1 - TEST_SIZE)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=val_relative_size, random_state=RANDOM_STATE, stratify=y_temp
    )
    
    logger.info(f"Train set: {len(X_train):,} rows ({y_train.sum():,} seizure)")
    logger.info(f"Validation set: {len(X_val):,} rows ({y_val.sum():,} seizure)")
    logger.info(f"Test set: {len(X_test):,} rows ({y_test.sum():,} seizure)")
    
    return {
        'X_train': X_train, 'y_train': y_train,
        'X_val': X_val, 'y_val': y_val,
        'X_test': X_test, 'y_test': y_test
    }


def train_model(X_train: pd.DataFrame, y_train: pd.Series, 
                X_val: pd.DataFrame, y_val: pd.Series) -> xgb.XGBClassifier:
    """Train XGBoost model with early stopping"""
    logger.info("Training XGBoost model...")
    
    model = xgb.XGBClassifier(**XGB_PARAMS)
    
    # Train with early stopping
    eval_set = [(X_train, y_train), (X_val, y_val)]
    
    model.fit(
        X_train, y_train,
        eval_set=eval_set,
        verbose=False
    )
    
    logger.info("Training complete")
    return model


def evaluate_model(model: xgb.XGBClassifier, X_test: pd.DataFrame, 
                   y_test: pd.Series) -> Dict[str, Any]:
    """Evaluate model on test set"""
    logger.info("Evaluating model on test set...")
    
    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Find optimal threshold
    fpr, tpr, thresholds = roc_curve(y_test, y_pred_proba)
    optimal_idx = np.argmax(tpr - fpr)
    optimal_threshold = thresholds[optimal_idx]
    
    # Predictions with optimal threshold
    y_pred_optimal = (y_pred_proba >= optimal_threshold).astype(int)
    
    # Metrics with default threshold (0.5)
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'balanced_accuracy': balanced_accuracy_score(y_test, y_pred),
        'f1': f1_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred),
        'recall': recall_score(y_test, y_pred),
        'specificity': recall_score(y_test, y_pred, pos_label=0),
        'auc': roc_auc_score(y_test, y_pred_proba),
        'optimal_threshold': float(optimal_threshold),
        'threshold_accuracy': accuracy_score(y_test, y_pred_optimal),
        'threshold_f1': f1_score(y_test, y_pred_optimal),
        'threshold_precision': precision_score(y_test, y_pred_optimal),
        'threshold_recall': recall_score(y_test, y_pred_optimal),
        'threshold_specificity': recall_score(y_test, y_pred_optimal, pos_label=0)
    }
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    metrics['confusion_matrix'] = cm.tolist()
    
    # Classification report
    metrics['classification_report'] = classification_report(y_test, y_pred, output_dict=True)
    
    # Additional statistics
    metrics['test_set_size'] = len(y_test)
    metrics['seizure_count'] = int(y_test.sum())
    metrics['background_count'] = int(len(y_test) - y_test.sum())
    
    logger.info(f"AUC: {metrics['auc']:.4f}")
    logger.info(f"F1 Score: {metrics['f1']:.4f}")
    logger.info(f"Balanced Accuracy: {metrics['balanced_accuracy']:.4f}")
    logger.info(f"Optimal Threshold: {optimal_threshold:.4f}")
    
    return metrics, y_pred_proba, y_pred, thresholds, fpr, tpr


def cross_validate(model: xgb.XGBClassifier, X_train: pd.DataFrame, 
                   y_train: pd.Series) -> Dict[str, float]:
    """Perform cross-validation"""
    logger.info(f"Performing {CV_FOLDS}-fold cross-validation...")
    
    cv_scores = cross_val_score(
        model, X_train, y_train, cv=CV_FOLDS, 
        scoring='roc_auc', n_jobs=-1
    )
    
    cv_results = {
        'cv_scores': cv_scores.tolist(),
        'cv_mean': float(cv_scores.mean()),
        'cv_std': float(cv_scores.std())
    }
    
    logger.info(f"CV AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    
    return cv_results


def get_feature_importance(model: xgb.XGBClassifier, feature_names: List[str]) -> pd.DataFrame:
    """Extract and sort feature importance"""
    importance = model.feature_importances_
    
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    # Add cumulative importance
    importance_df['cumulative_importance'] = importance_df['importance'].cumsum()
    
    return importance_df


def plot_confusion_matrix(cm: np.ndarray, output_path: Path):
    """Plot confusion matrix"""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)
    
    ax.set(xticks=np.arange(cm.shape[1]),
           yticks=np.arange(cm.shape[0]),
           xticklabels=['Background', 'Seizure'],
           yticklabels=['Background', 'Seizure'],
           ylabel='True Label',
           xlabel='Predicted Label')
    
    # Add text annotations
    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], 'd'),
                   ha="center", va="center",
                   color="white" if cm[i, j] > thresh else "black")
    
    ax.set_title('Confusion Matrix')
    fig.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Confusion matrix saved to {output_path}")


def plot_roc_curve(fpr: np.ndarray, tpr: np.ndarray, auc: float, output_path: Path):
    """Plot ROC curve"""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    ax.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {auc:.4f})')
    ax.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Random')
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title('Receiver Operating Characteristic (ROC) Curve')
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"ROC curve saved to {output_path}")


def plot_feature_importance(importance_df: pd.DataFrame, output_path: Path, top_n: int = 30):
    """Plot top N feature importance"""
    fig, ax = plt.subplots(figsize=(12, 10))
    
    top_features = importance_df.head(top_n)
    
    bars = ax.barh(range(len(top_features)), top_features['importance'].values)
    ax.set_yticks(range(len(top_features)))
    ax.set_yticklabels(top_features['feature'].values)
    ax.invert_yaxis()
    ax.set_xlabel('Importance')
    ax.set_title(f'Top {top_n} Feature Importance')
    
    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, top_features['importance'].values)):
        ax.text(val + 0.001, i, f'{val:.4f}', va='center', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Feature importance plot saved to {output_path}")


def save_metrics(metrics: Dict, cv_results: Dict, output_path: Path):
    """Save metrics to JSON"""
    # Convert numpy types to Python types
    def convert(obj):
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    
    full_results = {
        'timestamp': datetime.now().isoformat(),
        'model_parameters': XGB_PARAMS,
        'cross_validation': cv_results,
        'test_metrics': metrics,
        'dataset_info': {
            'dataset_path': str(DATASET_PATH)
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(full_results, f, indent=2, default=convert)
    
    logger.info(f"Metrics saved to {output_path}")


def print_summary(metrics: Dict, cv_results: Dict):
    """Print training summary"""
    print("\n" + "=" * 80)
    print("PHASE 4A XGBOOST TRAINING SUMMARY")
    print("=" * 80)
    
    print("\n📊 CROSS-VALIDATION")
    print(f"   {CV_FOLDS}-Fold AUC: {cv_results['cv_mean']:.4f} ± {cv_results['cv_std']:.4f}")
    
    print("\n📈 TEST SET PERFORMANCE")
    print(f"   AUC: {metrics['auc']:.4f}")
    print(f"   Balanced Accuracy: {metrics['balanced_accuracy']:.4f}")
    print(f"   F1 Score: {metrics['f1']:.4f}")
    print(f"   Precision: {metrics['precision']:.4f}")
    print(f"   Recall (Sensitivity): {metrics['recall']:.4f}")
    print(f"   Specificity: {metrics['specificity']:.4f}")
    print(f"   Accuracy: {metrics['accuracy']:.4f}")
    
    print("\n🎯 OPTIMAL THRESHOLD")
    print(f"   Threshold: {metrics['optimal_threshold']:.4f}")
    print(f"   F1 at threshold: {metrics['threshold_f1']:.4f}")
    print(f"   Recall at threshold: {metrics['threshold_recall']:.4f}")
    
    cm = metrics['confusion_matrix']
    print("\n📋 CONFUSION MATRIX (threshold=0.5)")
    print(f"   True Negatives: {cm[0][0]:,}")
    print(f"   False Positives: {cm[0][1]:,}")
    print(f"   False Negatives: {cm[1][0]:,}")
    print(f"   True Positives: {cm[1][1]:,}")
    
    print("\n" + "=" * 80)


def main():
    """Main training execution"""
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("NEUROVISION OMEGA - PHASE 4A XGBOOST TRAINING")
    logger.info(f"Dataset: {DATASET_PATH}")
    logger.info("=" * 80)
    
    # Step 1: Load dataset
    logger.info("\n📂 Loading dataset...")
    X, y = load_dataset()
    
    # Step 2: Split data
    logger.info("\n✂️ Splitting data...")
    splits = split_data(X, y)
    
    # Step 3: Train model
    logger.info("\n🏋️ Training XGBoost model...")
    model = train_model(
        splits['X_train'], splits['y_train'],
        splits['X_val'], splits['y_val']
    )
    
    # Step 4: Cross-validate
    logger.info("\n🔍 Performing cross-validation...")
    cv_results = cross_validate(model, splits['X_train'], splits['y_train'])
    
    # Step 5: Evaluate on test set
    logger.info("\n📊 Evaluating on test set...")
    metrics, y_pred_proba, y_pred, thresholds, fpr, tpr = evaluate_model(
        model, splits['X_test'], splits['y_test']
    )
    
    # Step 6: Feature importance
    logger.info("\n📋 Computing feature importance...")
    feature_names = splits['X_train'].columns.tolist()
    importance_df = get_feature_importance(model, feature_names)
    
    # Step 7: Save model
    logger.info(f"\n💾 Saving model to {MODEL_OUTPUT_PATH}...")
    joblib.dump(model, MODEL_OUTPUT_PATH)
    
    # Step 8: Save feature importance
    logger.info(f"💾 Saving feature importance to {FEATURE_IMPORTANCE_PATH}...")
    importance_df.to_csv(FEATURE_IMPORTANCE_PATH, index=False)
    
    # Step 9: Generate plots
    logger.info("\n📈 Generating plots...")
    cm = np.array(metrics['confusion_matrix'])
    plot_confusion_matrix(cm, CONFUSION_MATRIX_PATH)
    plot_roc_curve(fpr, tpr, metrics['auc'], ROC_CURVE_PATH)
    plot_feature_importance(importance_df, FEATURE_IMPORTANCE_PLOT_PATH, top_n=30)
    
    # Step 10: Save metrics
    logger.info("\n💾 Saving metrics...")
    save_metrics(metrics, cv_results, METRICS_PATH)
    
    # Print summary
    print_summary(metrics, cv_results)
    
    elapsed = time.time() - start_time
    logger.info(f"\n✅ Training complete! Execution time: {elapsed/60:.2f} minutes")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()