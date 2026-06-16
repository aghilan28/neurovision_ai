#!/usr/bin/env python3
import json
import pandas as pd
from pathlib import Path

DATA_PATH = Path('PHASE5B_ENGINEERED_DATASET.parquet')
OUT_PATH = Path('PHASE5B_FEATURE_SIGNATURE.json')

REQUIRED_METADATA = {
    'label',
    'patient',
    'edf',
    'window_uid',
    'window_index',
    'window_start_sec',
    'window_end_sec',
    'window_duration_sec',
    'stride_sec'
}

# Expected canonical counts from Phase5B training
EXPECTED_BASE_FEATURES = 96
EXPECTED_TOTAL_FEATURES = 484

if not DATA_PATH.exists():
    raise SystemExit(f"Missing dataset: {DATA_PATH}")

df = pd.read_parquet(DATA_PATH)
cols = list(df.columns)

# Position/metadata columns to exclude from features but append at the end
position_cols = [
    'window_index', 'window_start_sec', 'window_end_sec',
    'window_duration_sec', 'stride_sec'
]

import re

# Treat additional derived position columns as position features (append at end)
derived_position_cols = [
    'normalized_window_index', 'relative_position_in_edf',
    'elapsed_time_fraction', 'remaining_time_fraction'
]

# Build feature groups deterministically from actual columns
derived_position_present = [p for p in derived_position_cols if p in cols]
position_cols_present = [p for p in position_cols if p in cols]

# Exclude raw position metadata and derived position columns from available_features;
# we'll append derived_position_present to the final signature (but not raw position_cols_present).
available_features = [c for c in cols if c not in REQUIRED_METADATA and c not in derived_position_present and c not in position_cols_present]

# Base features: those that do NOT include engineered suffixes (_lag, rolling_mean, _stability_)
def is_engineered(name: str) -> bool:
    return bool(re.search(r'(_lag\d+|rolling_mean|_stability_)', name))

base_features = sorted([c for c in available_features if not is_engineered(c)])

# Lag & engineered groups (preserve deterministic sorted order)
lag1_features = sorted([c for c in available_features if re.search(r'_lag1\b', c)])
lag3_features = sorted([c for c in available_features if re.search(r'_lag3\b', c)])
rolling_features = sorted([c for c in available_features if 'rolling_mean' in c])
stability_features = sorted([c for c in available_features if '_stability_' in c])

# Construct final ordered list
seen = set()
all_features = []

for grp in (base_features, lag1_features, lag3_features, rolling_features, stability_features):
    for f in grp:
        if f in seen:
            continue
        all_features.append(f)
        seen.add(f)

# Append derived position features at the end (these are features used by the model),
# but do NOT append raw window metadata (window_index, window_start_sec, etc.).
for p in derived_position_present:
    if p not in seen:
        all_features.append(p)
        seen.add(p)

signature = {
    'feature_count': len(all_features),
    'feature_names': all_features
}

with open(OUT_PATH, 'w') as f:
    json.dump(signature, f, indent=2)

print('Wrote', OUT_PATH)
print('feature_count=', signature['feature_count'])
# Compute deterministic base root count by stripping known suffixes
def _root_name(fname: str) -> str:
    # remove engineered suffixes
    s = re.sub(r'(_lag\d+|_rolling_mean_\d+|_stability_\d+)$', '', fname)
    # remove the final statistic suffix if present
    s = re.sub(r'_(max|mean|std)$', '', s)
    return s

# base_features was computed earlier as the deduced base feature names (non-engineered)
base_count = len(base_features)
print('base_features=', base_count)
print("window_uid in feature_names?", 'window_uid' in signature['feature_names'])

# Validate against expected canonical counts
if base_count != EXPECTED_BASE_FEATURES or signature['feature_count'] != EXPECTED_TOTAL_FEATURES:
    print('\n*** Feature signature validation FAILED ***')
    print('expected base features:', EXPECTED_BASE_FEATURES, 'found:', base_count)
    print('expected total features:', EXPECTED_TOTAL_FEATURES, 'found:', signature['feature_count'])
    # Print diagnostic summary: extras and missing
    expected_total = EXPECTED_TOTAL_FEATURES
    actual_total = signature['feature_count']
    # Identify possible position/derived extras
    extras = []
    if actual_total > expected_total:
        extras = list(all_features[expected_total:]) if len(all_features) > expected_total else []
    print('candidate extra features (tail of list):', extras[:20])
    raise SystemExit('PHASE5B feature signature does not match expected counts; adjust generator heuristics')

print('\nFeature signature validated against expected counts')
