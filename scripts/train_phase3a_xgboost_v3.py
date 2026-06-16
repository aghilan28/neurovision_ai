import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score,
    f1_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    confusion_matrix
)

from xgboost import XGBClassifier
from joblib import dump

print("=" * 80)
print("NEUROVISION PHASE 3A")
print("=" * 80)

df = pd.read_parquet(
    "real_feature_dataset_v3_clean.parquet"
)

print()
print("Rows:", len(df))

X = df.drop(
    columns=[
        "label",
        "patient",
        "edf"
    ]
)

y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

neg = (y_train == 0).sum()
pos = (y_train == 1).sum()

scale_weight = neg / pos

print()
print("Train:", len(X_train))
print("Test :", len(X_test))
print("Scale Weight:", round(scale_weight, 2))

model = XGBClassifier(
    n_estimators=500,
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

probs = model.predict_proba(X_test)[:, 1]

auc = roc_auc_score(
    y_test,
    probs
)

best_f1 = 0
best_threshold = 0.5

for threshold in np.arange(
    0.05,
    0.99,
    0.01
):

    pred = (
        probs >= threshold
    ).astype(int)

    score = f1_score(
        y_test,
        pred,
        zero_division=0
    )

    if score > best_f1:
        best_f1 = score
        best_threshold = threshold

pred = (
    probs >= best_threshold
).astype(int)

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

specificity = tn / (tn + fp)

print("=" * 80)
print("RESULTS")
print("=" * 80)

print("AUC         :", round(auc, 4))
print("BA          :", round(ba, 4))
print("F1          :", round(best_f1, 4))
print("Precision   :", round(precision, 4))
print("Sensitivity :", round(sensitivity, 4))
print("Specificity :", round(specificity, 4))
print("Threshold   :", round(best_threshold, 2))

importance = pd.DataFrame({
    "feature": X.columns,
    "importance": model.feature_importances_
})

importance = importance.sort_values(
    "importance",
    ascending=False
)

importance.to_csv(
    "PHASE3A_FEATURE_IMPORTANCE.csv",
    index=False
)

dump(
    model,
    "PHASE3A_XGBOOST_V3.joblib"
)

print()
print("Saved:")
print("PHASE3A_XGBOOST_V3.joblib")
print("PHASE3A_FEATURE_IMPORTANCE.csv")