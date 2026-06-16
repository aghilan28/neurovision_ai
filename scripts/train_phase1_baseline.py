import pandas as pd
import numpy as np

from sklearn.metrics import (
    roc_auc_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score
)

from sklearn.preprocessing import StandardScaler

from xgboost import XGBClassifier

print("="*80)
print("LOADING DATASET")
print("="*80)

df = pd.read_parquet(
    "real_feature_dataset_v2.parquet"
)

FEATURES = [
    c for c in df.columns
    if c not in ["label","patient","edf"]
]

print("Rows:",len(df))
print("Features:",len(FEATURES))

patients = sorted(
    df["patient"].unique()
)

print()
print("Patients:",len(patients))
print()

results = []

for test_patient in patients:

    print("="*80)
    print("TEST PATIENT:",test_patient)
    print("="*80)

    train_df = df[
        df.patient != test_patient
    ]

    test_df = df[
        df.patient == test_patient
    ]

    train_sz = train_df[
        train_df.label == 1
    ]

    train_bg = train_df[
        train_df.label == 0
    ]

    n_sz = len(train_sz)

    train_bg = train_bg.sample(
        n=min(
            n_sz * 4,
            len(train_bg)
        ),
        random_state=42
    )

    train_df = pd.concat(
        [
            train_sz,
            train_bg
        ]
    )

    X_train = train_df[
        FEATURES
    ].values

    y_train = train_df[
        "label"
    ].values

    X_test = test_df[
        FEATURES
    ].values

    y_test = test_df[
        "label"
    ].values

    scaler = StandardScaler()

    X_train = scaler.fit_transform(
        X_train
    )

    X_test = scaler.transform(
        X_test
    )

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss",
        tree_method="hist"
    )

    model.fit(
        X_train,
        y_train
    )

    prob = model.predict_proba(
        X_test
    )[:,1]

    pred = (
        prob >= 0.5
    ).astype(int)

    auc = roc_auc_score(
        y_test,
        prob
    )

    ba = balanced_accuracy_score(
        y_test,
        pred
    )

    f1 = f1_score(
        y_test,
        pred,
        zero_division=0
    )

    sens = recall_score(
        y_test,
        pred,
        zero_division=0
    )

    spec = recall_score(
        y_test,
        pred,
        pos_label=0,
        zero_division=0
    )

    print(
        f"AUC={auc:.4f} "
        f"BA={ba:.4f} "
        f"F1={f1:.4f}"
    )

    results.append(
        {
            "patient":test_patient,
            "auc":auc,
            "ba":ba,
            "f1":f1,
            "sens":sens,
            "spec":spec
        }
    )

res = pd.DataFrame(results)

print()
print("="*80)
print("FINAL RESULTS")
print("="*80)

print(res)

print()
print(
    "MEAN AUC:",
    res.auc.mean()
)

print(
    "MEAN BA:",
    res.ba.mean()
)

print(
    "MEAN F1:",
    res.f1.mean()
)

res.to_csv(
    "PHASE1_LOPO_RESULTS.csv",
    index=False
)

print()
print(
    "Saved: PHASE1_LOPO_RESULTS.csv"
)