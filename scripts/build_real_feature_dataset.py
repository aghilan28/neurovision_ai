import os
import json
import gc
from pathlib import Path

import numpy as np
import pandas as pd
import mne
from tqdm import tqdm

DATASET_ROOT = r"E:\NeuroVision\datasets\chbmit"

WINDOW_SECONDS = 4
STRIDE_SECONDS = 2
TARGET_SFREQ = 256

OUTPUT_FILE = "real_feature_dataset.parquet"


def compute_features(window):
    features = {}

    signal = window.mean(axis=0)

    features["mean"] = float(np.mean(signal))
    features["std"] = float(np.std(signal))
    features["rms"] = float(np.sqrt(np.mean(signal ** 2)))

    features["max"] = float(np.max(signal))
    features["min"] = float(np.min(signal))

    features["ptp"] = float(np.ptp(signal))

    features["line_length"] = float(
        np.sum(np.abs(np.diff(signal)))
    )

    spectrum = np.abs(np.fft.rfft(signal))

    freqs = np.fft.rfftfreq(
        len(signal),
        d=1.0 / TARGET_SFREQ
    )

    bands = {
        "delta": (0.5,4),
        "theta": (4,8),
        "alpha": (8,13),
        "beta": (13,30),
        "gamma": (30,45)
    }

    total_power = np.sum(spectrum) + 1e-8

    for name,(low,high) in bands.items():

        mask = (
            (freqs >= low) &
            (freqs < high)
        )

        power = np.sum(spectrum[mask])

        features[f"{name}_power"] = float(power)

        features[f"{name}_relative"] = float(
            power / total_power
        )

    return features


def parse_reconstructed_json():

    with open(
        "SEIZURE_RECONSTRUCTION.json",
        "r"
    ) as f:

        return json.load(f)


def overlaps(
    start,
    end,
    intervals
):

    for s,e in intervals:

        if start < e and end > s:
            return True

    return False


def main():

    seizure_db = parse_reconstructed_json()

    rows = []

    edf_files = list(
        Path(DATASET_ROOT).rglob("*.edf")
    )

    print()
    print("EDF FILES:",len(edf_files))
    print()

    for edf in tqdm(edf_files):

        patient = edf.parent.name

        fname = edf.name

        intervals = seizure_db.get(
            patient,
            {}
        ).get(
            fname,
            []
        )

        try:

            raw = mne.io.read_raw_edf(
                str(edf),
                preload=True,
                verbose=False
            )

            data = raw.get_data()

            sfreq = raw.info["sfreq"]

            samples_per_window = int(
                WINDOW_SECONDS * sfreq
            )

            stride_samples = int(
                STRIDE_SECONDS * sfreq
            )

            total_samples = data.shape[1]

            for start_sample in range(
                0,
                total_samples - samples_per_window,
                stride_samples
            ):

                end_sample = (
                    start_sample +
                    samples_per_window
                )

                start_sec = (
                    start_sample /
                    sfreq
                )

                end_sec = (
                    end_sample /
                    sfreq
                )

                label = int(
                    overlaps(
                        start_sec,
                        end_sec,
                        intervals
                    )
                )

                window = data[
                    :,
                    start_sample:end_sample
                ]

                feat = compute_features(
                    window
                )

                feat["label"] = label
                feat["patient"] = patient
                feat["edf"] = fname

                rows.append(feat)

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
    print(df.shape)
    print()

    df.to_parquet(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("SAVED:",OUTPUT_FILE)
    print()


if __name__ == "__main__":
    main()