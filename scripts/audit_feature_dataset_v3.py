import pandas as pd

df = pd.read_parquet(
    "real_feature_dataset_v3.parquet"
)

print("=" * 80)
print("DATASET AUDIT")
print("=" * 80)

print()
print("SHAPE")
print(df.shape)

print()
print("LABELS")
print(df["label"].value_counts())

print()
print("NULL VALUES")
print(
    df.isnull()
    .sum()
    .sort_values(ascending=False)
    .head(20)
)

print()
print("INF CHECK")

numeric = df.select_dtypes(
    include=["float64","float32","int64","int32"]
)

import numpy as np

print(
    np.isinf(
        numeric.values
    ).sum()
)

print()
print("FEATURE COUNT")

features = [
    c for c in df.columns
    if c not in [
        "label",
        "patient",
        "edf"
    ]
]

print(len(features))

print()
print(features)