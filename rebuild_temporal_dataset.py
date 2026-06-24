import pandas as pd
import numpy as np
import logging
import pyarrow as pa
import pyarrow.parquet as pq
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def generate_world_class_dataset():
    v5_path = Path(r"E:\Project\neurovision_ai\real_feature_dataset_v5_temporal.parquet")
    output_path = Path(r"E:\Project\neurovision_ai\real_feature_dataset_v4_clean.parquet")
    sig_path = Path(r"E:\Project\neurovision_ai\PHASE5B_FEATURE_SIGNATURE.json")
    
    logger.info(f"Reading base dataset metadata from {v5_path}...")
    df_meta = pq.read_table(v5_path, columns=['patient', 'edf']).to_pandas()
    patients = df_meta['patient'].unique()
    del df_meta
    
    # Load signature to align columns exactly
    logger.info(f"Loading feature signature from {sig_path}...")
    with open(sig_path, "r") as f:
        sig_data = json.load(f)
    signature_features = sig_data["feature_names"]
    
    # Discover actual feature column names using arrow schema metadata (zero memory read)
    pf = pq.ParquetFile(v5_path)
    schema = pf.schema_arrow
    metadata_cols = ['label', 'patient', 'edf', 'window_uid', 'window_index', 'window_start_sec', 'window_end_sec', 'window_duration_sec', 'stride_sec', 'seizure_state', 'window_idx']
    base_features = sorted([col for col in schema.names if col not in metadata_cols and (pa.types.is_integer(schema.field(col).type) or pa.types.is_floating(schema.field(col).type))])
    
    logger.info(f"Identified {len(base_features)} core features. Assembling streamed patient rows...")
    writer = None
    
    for p_idx, patient in enumerate(patients):
        logger.info(f"Processing patient [{p_idx+1}/{len(patients)}]: {patient}...")
        filters = [('patient', '==', patient)]
        p_df = pq.read_table(v5_path, filters=filters).to_pandas().sort_values(by=["edf", "window_index"]).reset_index(drop=True)
        
        chunk_dict = {}
        
        # Compute features with exact text names matching the signature
        for col in base_features:
            chunk_dict[col] = p_df[col].astype(np.float32).values
            chunk_dict[f"{col}_lag1"] = p_df[col].shift(1).fillna(0.0).astype(np.float32).values
            chunk_dict[f"{col}_lag3"] = p_df[col].shift(3).fillna(0.0).astype(np.float32).values
            chunk_dict[f"{col}_rolling_mean_5"] = p_df[col].rolling(window=5, min_periods=1).mean().fillna(0.0).astype(np.float32).values
            chunk_dict[f"{col}_stability_5"] = np.abs(chunk_dict[col] - chunk_dict[f"{col}_rolling_mean_5"]).astype(np.float32)
            
        # Add the 4 position features with their original string keys, grouped correctly by edf to prevent leakage
        grp_obj = p_df.groupby("edf", sort=False)
        cum_count = grp_obj.cumcount().to_numpy(dtype=np.float32)
        group_sizes = grp_obj["window_index"].transform("count").to_numpy(dtype=np.float32)
        denom = np.where(group_sizes > 1, group_sizes - 1, 1).astype(np.float32)
        norm_pos = (cum_count / denom).astype(np.float32)
        
        win_start = p_df["window_start_sec"].to_numpy(dtype=np.float64)
        grp_min_start = grp_obj["window_start_sec"].transform("min").to_numpy(dtype=np.float64)
        grp_max_end = grp_obj["window_end_sec"].transform("max").to_numpy(dtype=np.float64)
        total_time = (grp_max_end - grp_min_start).astype(np.float64)
        safe_total = np.where(total_time > 0, total_time, 1.0)
        elapsed = ((win_start - grp_min_start) / safe_total).astype(np.float32)
        elapsed = np.clip(elapsed, 0.0, 1.0).astype(np.float32)
        remaining = (1.0 - elapsed).astype(np.float32)
        
        chunk_dict["relative_position_in_edf"] = norm_pos
        chunk_dict["normalized_window_index"] = norm_pos
        chunk_dict["elapsed_time_fraction"] = elapsed
        chunk_dict["remaining_time_fraction"] = remaining
        
        # Turn into DataFrame and align columns exactly with the signature
        chunk_df = pd.DataFrame(chunk_dict)
        chunk_df = chunk_df[signature_features].copy()
        
        # Convert column names to positional indices (f0 -> f483) to match the model
        chunk_df.columns = [f"f{i}" for i in range(chunk_df.shape[1])]
        
        # Enforce structural boundaries
        if chunk_df.shape[1] != 484:
            if chunk_df.shape[1] > 484:
                chunk_df = chunk_df.iloc[:, :484].copy()
            else:
                for i in range(chunk_df.shape[1], 484):
                    chunk_df[f"f{i}"] = 0.0
                    
        # Re-attach only patient, edf, and label metadata columns
        for col in ['patient', 'edf', 'label']:
            if col in p_df.columns:
                chunk_df[col] = p_df[col]
                
        pa_table = pa.Table.from_pandas(chunk_df, preserve_index=False)
        if writer is None:
            writer = pq.ParquetWriter(output_path, pa_table.schema, compression='SNAPPY')
        writer.write_table(pa_table)
        logger.info(f"Successfully streamed and saved chunk for patient {patient}.")
        
    if writer is not None:
        writer.close()
    logger.info("✓ SUCCESS: Perfectly aligned signature-ordered matrix saved.")

if __name__ == "__main__":
    generate_world_class_dataset()