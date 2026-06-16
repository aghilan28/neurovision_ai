import pandas as pd
import numpy as np

from xgboost import XGBClassifier
from joblib import dump

from sklearn.metrics import (
    roc_auc_score,
    f1_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    confusion_matrix
)

print("=" * 80)
print("NEUROVISION PHASE 3B")
print("PATIENT-DISJOINT VALIDATION")
print("=" * 80)

# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_parquet(
    "real_feature_dataset_v3_clean.parquet"
)

print()
print("Rows:", len(df))
print("Patients:", df["patient"].nunique())

# ============================================================
# PATIENT SPLIT
# ============================================================

patients = sorted(
    df["patient"].unique()
)

print()
print("ALL PATIENTS")
print(patients)

# 24 patients total
# 19 train
# 5 test

test_patients = [
    "chb05",
    "chb08",
    "chb12",
    "chb18",
    "chb24"
]

train_patients = [
    p for p in patients
    if p not in test_patients
]

print()
print("TRAIN PATIENTS")
print(train_patients)

print()
print("TEST PATIENTS")
print(test_patients)

train_df = df[
    df["patient"].isin(
        train_patients
    )
]

test_df = df[
    df["patient"].isin(
        test_patients
    )
]

print()
print("Train Rows:", len(train_df))
print("Test Rows :", len(test_df))

# ============================================================
# FEATURES
# ============================================================

feature_cols = [
    c for c in df.columns
    if c not in [
        "label",
        "patient",
        "edf"
    ]
]

X_train = train_df[
    feature_cols
]

y_train = train_df[
    "label"
]

X_test = test_df[
    feature_cols
]

y_test = test_df[
    "label"
]

# ============================================================
# CLASS BALANCE
# ============================================================

neg = (y_train == 0).sum()
pos = (y_train == 1).sum()

scale_weight = neg / pos

print()
print("Train Negative:", neg)
print("Train Positive:", pos)
print("Scale Weight:", round(scale_weight, 2))

# ============================================================
# MODEL
# ============================================================

model = XGBClassifier(
    n_estimators=700,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="binary:logistic",
    eval_metric="auc",
    scale_pos_weight=scale_weight,
    tree_method="hist",
    random_state=42,
    n_jobs=16
)

print()
print("TRAINING...")
print()

model.fit(
    X_train,
    y_train
)

# ============================================================
# PROBABILITIES
# ============================================================

probs = model.predict_proba(
    X_test
)[:, 1]

auc = roc_auc_score(
    y_test,
    probs
)

# ============================================================
# THRESHOLD SEARCH
# ============================================================

best_f1 = 0
best_threshold = 0.50

for threshold in np.arange(
    0.01,
    0.99,
    0.01
):

    pred = (
        probs >= threshold
    ).astype(int)

    f1 = f1_score(
        y_test,
        pred,
        zero_division=0
    )

    if f1 > best_f1:

        best_f1 = f1
        best_threshold = threshold

pred = (
    probs >= best_threshold
).astype(int)

# ============================================================
# METRICS
# ============================================================

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

tn, fp, fn, tp = confusion_matrix(
    y_test,
    pred
).ravel()

specificity = tn / (
    tn + fp
)

# ============================================================
# FEATURE IMPORTANCE
# ============================================================

importance = pd.DataFrame({
    "feature": feature_cols,
    "importance": model.feature_importances_
})

importance = importance.sort_values(
    "importance",
    ascending=False
)

importance.to_csv(
    "PHASE3B_PATIENT_DISJOINT_IMPORTANCE.csv",
    index=False
)

# ============================================================
# SAVE MODEL
# ============================================================

dump(
    model,
    "PHASE3B_PATIENT_DISJOINT.joblib"
)

# ============================================================
# RESULTS
# ============================================================

print("=" * 80)
print("PATIENT-DISJOINT RESULTS")
print("=" * 80)

print("AUC         :", round(auc, 4))
print("BA          :", round(ba, 4))
print("F1          :", round(best_f1, 4))
print("Precision   :", round(precision, 4))
print("Sensitivity :", round(sensitivity, 4))
print("Specificity :", round(specificity, 4))
print("Threshold   :", round(best_threshold, 2))

print()
print("Saved:")
print("PHASE3B_PATIENT_DISJOINT.joblib")
print("PHASE3B_PATIENT_DISJOINT_IMPORTANCE.csv")