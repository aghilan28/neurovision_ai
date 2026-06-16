import pandas as pd

print("=" * 80)
print("PHASE 4A SIZE ESTIMATION")
print("=" * 80)

df = pd.read_parquet(
    "real_feature_dataset_v3_clean.parquet"
)

rows = len(df)

base_features = 32
expanded_features = 96

ratio = expanded_features / base_features

current_mb = (
    df.memory_usage(deep=True)
      .sum()
    / 1024
    / 1024
)

estimated_mb = current_mb * ratio

print()
print("Rows:", rows)
print("Current MB:", round(current_mb,2))
print("Estimated V4 MB:", round(estimated_mb,2))
print("Estimated V4 GB:", round(estimated_mb/1024,2))
print()

if estimated_mb < 2500:
    print("SAFE TO BUILD V4")
else:
    print("WARNING: LARGE DATASET")