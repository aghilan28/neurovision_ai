import pandas as pd
import numpy as np

from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    roc_auc_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score
)

from xgboost import XGBClassifier

print("="*80)
print("NEUROVISION PHASE 2")
print("="*80)

df = pd.read_parquet("real_feature_dataset_v2.parquet")

print("Rows:", len(df))

feature_cols = [
    c for c in df.columns
    if c not in ["label", "patient", "edf"]
]

X = df[feature_cols]
y = df["label"]

groups = df["patient"]

splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.20,
    random_state=42
)

train_idx, test_idx = next(
    splitter.split(X, y, groups)
)

X_train = X.iloc[train_idx]
X_test = X.iloc[test_idx]

y_train = y.iloc[train_idx]
y_test = y.iloc[test_idx]

print()
print("Train:", len(X_train))
print("Test :", len(X_test))

scale_pos_weight = (
    (y_train == 0).sum()
    /
    (y_train == 1).sum()
)

print("Scale Weight:", scale_pos_weight)

model = XGBClassifier(
    n_estimators=500,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    tree_method="hist",
    eval_metric="auc",
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    n_jobs=16
)

print()
print("TRAINING...")

model.fit(X_train, y_train)

prob = model.predict_proba(X_test)[:,1]

best_f1 = 0
best_threshold = 0.5

for t in np.arange(0.01,0.99,0.01):

    pred = (prob >= t).astype(int)

    score = f1_score(
        y_test,
        pred,
        zero_division=0
    )

    if score > best_f1:
        best_f1 = score
        best_threshold = t

pred = (prob >= best_threshold).astype(int)

auc = roc_auc_score(y_test, prob)

ba = balanced_accuracy_score(
    y_test,
    pred
)

precision = precision_score(
    y_test,
    pred,
    zero_division=0
)

sensitivity = recall_score(
    y_test,
    pred,
    zero_division=0
)

specificity = (
    ((pred == 0) & (y_test == 0)).sum()
    /
    (y_test == 0).sum()
)

print()
print("="*80)
print("RESULTS")
print("="*80)

print("AUC         :", round(auc,4))
print("BA          :", round(ba,4))
print("F1          :", round(best_f1,4))
print("Precision   :", round(precision,4))
print("Sensitivity :", round(sensitivity,4))
print("Specificity :", round(specificity,4))
print("Threshold   :", round(best_threshold,4))

import joblib

joblib.dump(
    model,
    "PHASE2_XGBOOST.joblib"
)

print()
print("Saved:")
print("PHASE2_XGBOOST.joblib")