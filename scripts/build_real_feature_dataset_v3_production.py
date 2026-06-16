import gc
import json
from pathlib import Path

import antropy as ant
import mne
import numpy as np
import pandas as pd
import pywt
from tqdm import tqdm

DATASET_ROOT = Path(r"E:\NeuroVision\datasets\chbmit")

WINDOW_SECONDS = 4
STRIDE_SECONDS = 2

OUTPUT_FILE = "real_feature_dataset_v3.parquet"

with open("SEIZURE_INTERVAL_DATABASE.json", "r") as f:
    SEIZURES = json.load(f)


def overlaps(start_sec, end_sec, intervals):
    for s, e in intervals:
        if start_sec < e and end_sec > s:
            return True
    return False


def spectral_entropy(signal, sfreq):
    spectrum = np.abs(np.fft.rfft(signal)) ** 2
    spectrum = spectrum / (np.sum(spectrum) + 1e-12)
    return float(-np.sum(spectrum * np.log2(spectrum + 1e-12)))


def compute_features(window, sfreq):

    signal = np.mean(window, axis=0)

    feats = {}

    feats["mean"] = float(np.mean(signal))
    feats["std"] = float(np.std(signal))
    feats["variance"] = float(np.var(signal))
    feats["rms"] = float(np.sqrt(np.mean(signal ** 2)))

    feats["max"] = float(np.max(signal))
    feats["min"] = float(np.min(signal))
    feats["ptp"] = float(np.ptp(signal))

    feats["line_length"] = float(
        np.sum(np.abs(np.diff(signal)))
    )

    feats["zero_crossings"] = float(
        np.sum(np.diff(np.sign(signal)) != 0)
    )

    feats["iqr"] = float(
        np.percentile(signal, 75) -
        np.percentile(signal, 25)
    )

    feats["mad"] = float(
        np.mean(
            np.abs(signal - np.mean(signal))
        )
    )

    try:
        feats["sample_entropy"] = float(
            ant.sample_entropy(signal)
        )
    except Exception:
        feats["sample_entropy"] = 0.0

    try:
        feats["perm_entropy"] = float(
            ant.perm_entropy(signal)
        )
    except Exception:
        feats["perm_entropy"] = 0.0

    try:
        feats["higuchi_fd"] = float(
            ant.higuchi_fd(signal)
        )
    except Exception:
        feats["higuchi_fd"] = 0.0

    try:
        feats["petrosian_fd"] = float(
            ant.petrosian_fd(signal)
        )
    except Exception:
        feats["petrosian_fd"] = 0.0

    coeffs = pywt.wavedec(
        signal,
        "db4",
        level=5
    )

    for i, coeff in enumerate(coeffs):
        feats[f"wavelet_energy_{i}"] = float(
            np.sum(coeff ** 2)
        )

    feats["spectral_entropy"] = spectral_entropy(
        signal,
        sfreq
    )

    spectrum = np.abs(
        np.fft.rfft(signal)
    ) ** 2

    freqs = np.fft.rfftfreq(
        len(signal),
        d=1.0 / sfreq
    )

    bands = {
        "delta": (0.5, 4),
        "theta": (4, 8),
        "alpha": (8, 13),
        "beta": (13, 30),
        "gamma": (30, 45),
    }

    total_power = np.sum(spectrum) + 1e-12

    for band, (lo, hi) in bands.items():

        mask = (
            (freqs >= lo) &
            (freqs < hi)
        )

        power = np.sum(
            spectrum[mask]
        )

        feats[f"{band}_power"] = float(power)

        feats[f"{band}_relative"] = float(
            power / total_power
        )

    return feats


rows = []

edf_files = sorted(
    DATASET_ROOT.rglob("*.edf")
)

print()
print("=" * 80)
print("FEATURE DATASET V3")
print("=" * 80)
print("EDF FILES:", len(edf_files))
print()

for edf in tqdm(edf_files):

    patient = edf.parent.name
    fname = edf.name

    intervals = (
        SEIZURES
        .get(patient, {})
        .get(fname, [])
    )

    try:

        raw = mne.io.read_raw_edf(
            str(edf),
            preload=True,
            verbose=False
        )

        data = raw.get_data()

        sfreq = raw.info["sfreq"]

        win = int(
            WINDOW_SECONDS * sfreq
        )

        stride = int(
            STRIDE_SECONDS * sfreq
        )

        total = data.shape[1]

        for start in range(
            0,
            total - win,
            stride
        ):

            end = start + win

            start_sec = start / sfreq
            end_sec = end / sfreq

            label = int(
                overlaps(
                    start_sec,
                    end_sec,
                    intervals
                )
            )

            feats = compute_features(
                data[:, start:end],
                sfreq
            )

            feats["label"] = label
            feats["patient"] = patient
            feats["edf"] = fname

            rows.append(feats)

        del raw
        gc.collect()

    except Exception as e:

        print(
            "FAILED:",
            edf,
            e
        )

df = pd.DataFrame(rows)

print()
print("=" * 80)
print("FINAL DATASET")
print("=" * 80)
print(df.shape)
print()
print(df["label"].value_counts())
print()

df.to_parquet(
    OUTPUT_FILE,
    index=False
)

print()
print("SAVED:", OUTPUT_FILE)
print()