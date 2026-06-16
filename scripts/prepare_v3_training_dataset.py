import pandas as pd

print("=" * 80)
print("PREPARING V3 TRAINING DATASET")
print("=" * 80)

df = pd.read_parquet(
    "real_feature_dataset_v3.parquet"
)

print()
print("Before:")
print(df.shape)

numeric_cols = df.select_dtypes(
    include=["float64", "float32", "int64", "int32"]
).columns

for col in numeric_cols:
    df[col] = df[col].fillna(
        df[col].median()
    )

print()
print("Nulls Remaining:")
print(
    df.isnull()
    .sum()
    .sum()
)

df.to_parquet(
    "real_feature_dataset_v3_clean.parquet",
    index=False
)

print()
print("Saved:")
print("real_feature_dataset_v3_clean.parquet")

print()
print(df.shape)