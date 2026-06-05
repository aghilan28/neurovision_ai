"""NeuroVision CHB-MIT Training Pipeline.

Downloads CHB-MIT EDF files from PhysioNet one at a time, extracts 10-second
windows with seizure/non-seizure labels, computes spectral features, and
trains a patient-disjoint seizure detection model.

Usage:
    python scripts/train_chbmit.py --patients 1,2,3,4,5 --output /tmp/nv_chbmit_model

This is Phase 1 Tier A of the NeuroVision clinical data pipeline.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import numpy as np

# Bootstrap imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PHYSIONET_BASE = "https://physionet.org/files/chbmit/1.0.0"
WINDOW_SECONDS = 10
SFREQ = 256  # CHB-MIT is 256 Hz


def download_file(url: str, dest: str) -> bool:
    """Download a file from PhysioNet."""
    try:
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as e:
        print(f"  DOWNLOAD FAILED: {e}")
        return False


def parse_summary(text: str) -> dict:
    """Parse a CHB-MIT summary file. Returns {filename: (n_seizures, [(start, end), ...])}."""
    result = {}
    current_file = None
    n_seizures = 0
    intervals = []

    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("File Name:"):
            if current_file:
                result[current_file] = (n_seizures, intervals)
            current_file = line.split(":", 1)[1].strip()
            n_seizures = 0
            intervals = []
        elif line.startswith("Number of Seizures in File:"):
            n_seizures = int(line.split(":")[-1].strip())
        elif "Seizure" in line and "Start Time:" in line:
            start = int(line.split(":")[-1].strip().split()[0])
            intervals.append(("start", start))
        elif "Seizure" in line and "End Time:" in line:
            end = int(line.split(":")[-1].strip().split()[0])
            if intervals and intervals[-1][0] == "start":
                intervals[-1] = (intervals[-1][1], end)

    if current_file:
        result[current_file] = (n_seizures, [iv for iv in intervals if isinstance(iv, tuple) and len(iv) == 2 and isinstance(iv[0], int)])

    return result


def extract_windows(edf_path: str, seizure_intervals: list, window_sec: int = WINDOW_SECONDS,
                    max_background_per_file: int = 30) -> list:
    """Extract labeled windows from an EDF file.

    Returns list of (features_dict, label) where label is 0 (background) or 1 (seizure).
    """
    import mne
    mne.set_log_level("ERROR")

    try:
        raw = mne.io.read_raw_edf(edf_path, preload=True, verbose="ERROR")
    except Exception as e:
        print(f"  READ FAILED: {e}")
        return []

    sfreq = raw.info["sfreq"]
    duration = raw.times[-1]
    n_channels = len(raw.ch_names)
    data = raw.get_data()  # (n_channels, n_samples)

    windows = []
    window_samples = int(window_sec * sfreq)

    # Mark seizure time ranges
    seizure_set = set()
    for start, end in seizure_intervals:
        for t in range(start, min(end, int(duration))):
            seizure_set.add(t)

    # Extract windows
    n_windows = int(duration / window_sec)
    bg_count = 0

    for w in range(n_windows):
        t_start = w * window_sec
        t_end = t_start + window_sec
        s_start = int(t_start * sfreq)
        s_end = int(t_end * sfreq)

        if s_end > data.shape[1]:
            break

        segment = data[:, s_start:s_end]

        # Label: seizure if any second in the window overlaps a seizure interval
        is_seizure = any(t in seizure_set for t in range(t_start, t_end))

        if not is_seizure:
            bg_count += 1
            if bg_count > max_background_per_file:
                continue  # Limit background windows to avoid class imbalance

        # Compute features for this window
        features = compute_window_features(segment, sfreq)
        if features is not None:
            windows.append((features, 1 if is_seizure else 0))

    return windows


def compute_window_features(segment: np.ndarray, sfreq: float) -> dict | None:
    """Compute spectral features for a single EEG window.

    Features per channel: band powers (delta, theta, alpha, beta, gamma),
    spectral entropy, RMS amplitude, line length.
    Then: mean/std across channels for each feature.
    """
    from scipy.signal import welch

    n_channels, n_samples = segment.shape
    if n_samples < int(sfreq * 2):
        return None

    bands = {
        "delta": (0.5, 4),
        "theta": (4, 8),
        "alpha": (8, 13),
        "beta": (13, 30),
        "gamma": (30, 45),
    }

    all_features = {}

    # Per-channel features
    ch_band_powers = {b: [] for b in bands}
    ch_entropy = []
    ch_rms = []
    ch_line_length = []

    for ch in range(min(n_channels, 23)):  # CHB-MIT has 23 channels
        x = segment[ch]

        # Check for flat/invalid channels
        if np.std(x) < 1e-10:
            continue

        # PSD via Welch
        nperseg = min(len(x), int(sfreq * 2))
        try:
            freqs, psd = welch(x, fs=sfreq, nperseg=nperseg)
        except Exception:
            continue

        # Band powers
        for band_name, (lo, hi) in bands.items():
            mask = (freqs >= lo) & (freqs < hi)
            bp = np.trapz(psd[mask], freqs[mask]) if mask.any() else 0
            ch_band_powers[band_name].append(float(bp))

        # Spectral entropy
        psd_norm = psd[psd > 0]
        if len(psd_norm) > 1:
            psd_prob = psd_norm / psd_norm.sum()
            entropy = -np.sum(psd_prob * np.log(psd_prob + 1e-12)) / np.log(len(psd_prob))
        else:
            entropy = 0
        ch_entropy.append(float(entropy))

        # RMS amplitude
        ch_rms.append(float(np.sqrt(np.mean(x ** 2))))

        # Line length (sum of absolute differences)
        ch_line_length.append(float(np.sum(np.abs(np.diff(x))) / len(x)))

    if not ch_entropy:
        return None

    # Aggregate across channels
    for band_name in bands:
        vals = ch_band_powers[band_name]
        if vals:
            all_features[f"{band_name}_mean"] = float(np.mean(vals))
            all_features[f"{band_name}_std"] = float(np.std(vals))
            all_features[f"{band_name}_max"] = float(np.max(vals))
        else:
            all_features[f"{band_name}_mean"] = 0.0
            all_features[f"{band_name}_std"] = 0.0
            all_features[f"{band_name}_max"] = 0.0

    all_features["entropy_mean"] = float(np.mean(ch_entropy))
    all_features["entropy_std"] = float(np.std(ch_entropy))
    all_features["rms_mean"] = float(np.mean(ch_rms))
    all_features["rms_std"] = float(np.std(ch_rms))
    all_features["line_length_mean"] = float(np.mean(ch_line_length))
    all_features["line_length_std"] = float(np.std(ch_line_length))

    # Ratios (clinically important)
    total_power = sum(all_features[f"{b}_mean"] for b in bands)
    if total_power > 0:
        for b in bands:
            all_features[f"{b}_ratio"] = all_features[f"{b}_mean"] / total_power
    else:
        for b in bands:
            all_features[f"{b}_ratio"] = 0.2

    # Delta/Alpha ratio (elevated in seizures)
    alpha = all_features["alpha_mean"]
    all_features["delta_alpha_ratio"] = all_features["delta_mean"] / (alpha + 1e-12)

    # Theta/Beta ratio
    beta = all_features["beta_mean"]
    all_features["theta_beta_ratio"] = all_features["theta_mean"] / (beta + 1e-12)

    return all_features


def process_patient(patient_id: str, output_dir: str) -> dict:
    """Download and process all EDF files for one CHB-MIT patient."""
    patient_dir = os.path.join(output_dir, patient_id)
    os.makedirs(patient_dir, exist_ok=True)

    # Download summary
    summary_url = f"{PHYSIONET_BASE}/{patient_id}/{patient_id}-summary.txt"
    summary_path = os.path.join(patient_dir, f"{patient_id}-summary.txt")
    print(f"\n=== Processing {patient_id} ===")

    if not download_file(summary_url, summary_path):
        return {"patient": patient_id, "error": "summary download failed"}

    with open(summary_path) as f:
        summary = parse_summary(f.read())

    stats = {"patient": patient_id, "files": 0, "seizure_windows": 0,
             "background_windows": 0, "errors": 0}
    all_windows = []

    for filename, (n_seizures, intervals) in summary.items():
        if not filename.endswith(".edf"):
            continue

        edf_url = f"{PHYSIONET_BASE}/{patient_id}/{filename}"
        edf_path = os.path.join(patient_dir, filename)

        print(f"  {filename}: {n_seizures} seizures... ", end="", flush=True)
        t0 = time.time()

        if not download_file(edf_url, edf_path):
            stats["errors"] += 1
            continue

        windows = extract_windows(edf_path, intervals)

        # Delete raw EDF to save disk space
        os.remove(edf_path)

        sz = sum(1 for _, l in windows if l == 1)
        bg = sum(1 for _, l in windows if l == 0)
        print(f"{sz} seizure + {bg} background windows ({time.time()-t0:.0f}s)")

        all_windows.extend([(f, l, patient_id) for f, l in windows])
        stats["files"] += 1
        stats["seizure_windows"] += sz
        stats["background_windows"] += bg

    # Save features for this patient
    features_path = os.path.join(patient_dir, "features.json")
    with open(features_path, "w") as f:
        json.dump(all_windows, f)

    print(f"  → {stats['seizure_windows']} seizure + {stats['background_windows']} background windows saved")
    return stats


def build_dataset(output_dir: str, patients: list[str]) -> tuple:
    """Load features from all processed patients and build X, y arrays."""
    all_X = []
    all_y = []
    all_patients = []

    feature_names = None

    for patient_id in patients:
        features_path = os.path.join(output_dir, patient_id, "features.json")
        if not os.path.exists(features_path):
            continue

        with open(features_path) as f:
            windows = json.load(f)

        for features, label, pid in windows:
            if feature_names is None:
                feature_names = sorted(features.keys())

            row = [features.get(fn, 0.0) for fn in feature_names]
            all_X.append(row)
            all_y.append(label)
            all_patients.append(pid)

    X = np.array(all_X, dtype=np.float64)
    y = np.array(all_y, dtype=int)

    return X, y, all_patients, feature_names


def train_model(X: np.ndarray, y: np.ndarray, patients: list, seed: int = 42):
    """Train a seizure detection model with patient-disjoint split."""
    from sklearn.model_selection import LeaveOneGroupOut
    from collections import Counter

    print(f"\n=== TRAINING ===")
    print(f"Dataset: {X.shape[0]} windows, {X.shape[1]} features")
    print(f"Labels: {Counter(y)}")
    print(f"Patients: {len(set(patients))}")

    # Normalize features
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std < 1e-10] = 1.0
    X_norm = (X - mean) / std

    # Simple logistic regression (matches the BaselineModel approach)
    # Patient-disjoint: hold out each patient for evaluation
    unique_patients = sorted(set(patients))
    patient_array = np.array([unique_patients.index(p) for p in patients])

    # Use 80/20 patient split
    n_train = max(1, int(len(unique_patients) * 0.8))
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(unique_patients))
    train_patients = set(perm[:n_train])
    test_patients = set(perm[n_train:])

    train_mask = np.array([patient_array[i] in train_patients for i in range(len(y))])
    test_mask = ~train_mask

    X_train, y_train = X_norm[train_mask], y[train_mask]
    X_test, y_test = X_norm[test_mask], y[test_mask]

    print(f"Train: {len(y_train)} windows ({sum(y_train)} seizure)")
    print(f"Test:  {len(y_test)} windows ({sum(y_test)} seizure)")

    # Train softmax classifier (same as BaselineModel)
    n_classes = 2
    n_features = X_train.shape[1]
    W = rng.standard_normal((n_features, n_classes)) * 0.01
    b = np.zeros(n_classes)

    lr = 0.1
    l2 = 1e-3
    epochs = 200

    for ep in range(epochs):
        z = X_train @ W + b
        z = z - z.max(axis=1, keepdims=True)
        exp_z = np.exp(z)
        probs = exp_z / (exp_z.sum(axis=1, keepdims=True) + 1e-12)

        Y = np.zeros((len(y_train), n_classes))
        Y[np.arange(len(y_train)), y_train] = 1.0

        loss = -np.sum(Y * np.log(probs + 1e-12)) / len(y_train) + 0.5 * l2 * np.sum(W ** 2)
        grad = (probs - Y) / len(y_train)
        W -= lr * (X_train.T @ grad + l2 * W)
        b -= lr * grad.sum(axis=0)

        if ep % 50 == 0:
            print(f"  Epoch {ep}: loss={loss:.4f}")

    # Evaluate
    z_test = X_test @ W + b
    z_test = z_test - z_test.max(axis=1, keepdims=True)
    exp_z = np.exp(z_test)
    probs_test = exp_z / (exp_z.sum(axis=1, keepdims=True) + 1e-12)
    preds = np.argmax(probs_test, axis=1)

    accuracy = np.mean(preds == y_test)
    sensitivity = np.mean(preds[y_test == 1] == 1) if sum(y_test == 1) > 0 else 0
    specificity = np.mean(preds[y_test == 0] == 0) if sum(y_test == 0) > 0 else 0

    print(f"\n=== RESULTS (Patient-Disjoint) ===")
    print(f"Accuracy:    {accuracy:.4f}")
    print(f"Sensitivity: {sensitivity:.4f}")
    print(f"Specificity: {specificity:.4f}")

    return {
        "W": W.tolist(), "b": b.tolist(),
        "mean": mean.tolist(), "std": std.tolist(),
        "feature_names": None,  # Set by caller
        "accuracy": accuracy, "sensitivity": sensitivity, "specificity": specificity,
        "n_train": len(y_train), "n_test": len(y_test),
        "n_patients": len(unique_patients),
    }


def main():
    parser = argparse.ArgumentParser(description="NeuroVision CHB-MIT Training Pipeline")
    parser.add_argument("--patients", default="1,2,3,4,5",
                        help="Comma-separated patient numbers (e.g., 1,2,3,4,5)")
    parser.add_argument("--output", default="/tmp/nv_chbmit",
                        help="Output directory for features and model")
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip download, use existing features")
    args = parser.parse_args()

    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    patient_nums = [int(p.strip()) for p in args.patients.split(",")]
    patient_ids = [f"chb{p:02d}" for p in patient_nums]

    print(f"NeuroVision CHB-MIT Training Pipeline")
    print(f"Patients: {patient_ids}")
    print(f"Output: {output_dir}")

    # Phase 1: Download and extract features
    if not args.skip_download:
        all_stats = []
        for pid in patient_ids:
            stats = process_patient(pid, output_dir)
            all_stats.append(stats)
            # Save progress
            with open(os.path.join(output_dir, "stats.json"), "w") as f:
                json.dump(all_stats, f, indent=2)

    # Phase 2: Build dataset and train
    X, y, patients, feature_names = build_dataset(output_dir, patient_ids)

    if len(X) == 0:
        print("ERROR: No windows extracted. Check downloads.")
        return

    model_data = train_model(X, y, patients)
    model_data["feature_names"] = feature_names

    # Save model
    model_path = os.path.join(output_dir, "chbmit_model.json")
    with open(model_path, "w") as f:
        json.dump(model_data, f)
    print(f"\nModel saved to {model_path}")


if __name__ == "__main__":
    main()
