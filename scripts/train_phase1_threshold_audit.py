import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score
)

from xgboost import XGBClassifier

print("=" * 80)
print("PHASE 1.5 THRESHOLD FORENSICS")
print("=" * 80)

df = pd.read_parquet(
    "real_feature_dataset_v2.parquet"
)

FEATURES = [
    c for c in df.columns
    if c not in ["label", "patient", "edf"]
]

patients = sorted(
    df["patient"].unique()
)

all_results = []

global_best_f1 = []
global_best_ba = []
global_best_youden = []

for test_patient in patients:

    print()
    print("=" * 80)
    print("PATIENT:", test_patient)
    print("=" * 80)

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
    )[:, 1]

    auc = roc_auc_score(
        y_test,
        prob
    )

    thresholds = np.arange(
        0.01,
        1.00,
        0.01
    )

    best_f1 = None
    best_ba = None
    best_youden = None

    for thr in thresholds:

        pred = (
            prob >= thr
        ).astype(int)

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

        ba = balanced_accuracy_score(
            y_test,
            pred
        )

        f1 = f1_score(
            y_test,
            pred,
            zero_division=0
        )

        prec = precision_score(
            y_test,
            pred,
            zero_division=0
        )

        youden = sens + spec - 1.0

        row = {
            "patient": test_patient,
            "threshold": thr,
            "auc": auc,
            "f1": f1,
            "ba": ba,
            "precision": prec,
            "sensitivity": sens,
            "specificity": spec,
            "youden": youden
        }

        all_results.append(row)

        if best_f1 is None or f1 > best_f1["f1"]:
            best_f1 = row

        if best_ba is None or ba > best_ba["ba"]:
            best_ba = row

        if best_youden is None or youden > best_youden["youden"]:
            best_youden = row

    global_best_f1.append(best_f1)
    global_best_ba.append(best_ba)
    global_best_youden.append(best_youden)

    print(
        f"AUC={auc:.4f}"
    )

    print(
        f"BEST F1      -> "
        f"thr={best_f1['threshold']:.2f} "
        f"F1={best_f1['f1']:.4f} "
        f"BA={best_f1['ba']:.4f}"
    )

    print(
        f"BEST BA      -> "
        f"thr={best_ba['threshold']:.2f} "
        f"F1={best_ba['f1']:.4f} "
        f"BA={best_ba['ba']:.4f}"
    )

    print(
        f"BEST YOUDEN  -> "
        f"thr={best_youden['threshold']:.2f} "
        f"F1={best_youden['f1']:.4f} "
        f"BA={best_youden['ba']:.4f}"
    )

all_df = pd.DataFrame(
    all_results
)

all_df.to_csv(
    "PHASE1_THRESHOLD_SWEEP.csv",
    index=False
)

best_f1_df = pd.DataFrame(
    global_best_f1
)

best_ba_df = pd.DataFrame(
    global_best_ba
)

best_youden_df = pd.DataFrame(
    global_best_youden
)

best_f1_df.to_csv(
    "PHASE1_BEST_F1.csv",
    index=False
)

best_ba_df.to_csv(
    "PHASE1_BEST_BA.csv",
    index=False
)

best_youden_df.to_csv(
    "PHASE1_BEST_YOUDEN.csv",
    index=False
)

print()
print("=" * 80)
print("GLOBAL SUMMARY")
print("=" * 80)

print()

print(
    "MEAN BEST F1:",
    best_f1_df["f1"].mean()
)

print(
    "MEAN BEST BA:",
    best_ba_df["ba"].mean()
)

print(
    "MEAN BEST YOUDEN BA:",
    best_youden_df["ba"].mean()
)

print()
print("Generated:")
print("PHASE1_THRESHOLD_SWEEP.csv")
print("PHASE1_BEST_F1.csv")
print("PHASE1_BEST_BA.csv")
print("PHASE1_BEST_YOUDEN.csv")