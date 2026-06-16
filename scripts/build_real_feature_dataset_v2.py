import gc
import json
from pathlib import Path

import mne
import numpy as np
import pandas as pd
from tqdm import tqdm

DATASET_ROOT = Path(r"E:\NeuroVision\datasets\chbmit")

WINDOW_SECONDS = 4
STRIDE_SECONDS = 2

OUTPUT_FILE = "real_feature_dataset_v2.parquet"

with open("SEIZURE_INTERVAL_DATABASE.json","r") as f:
    SEIZURES = json.load(f)

def overlaps(start_sec,end_sec,intervals):

    for s,e in intervals:

        if start_sec < e and end_sec > s:
            return True

    return False

def compute_features(window,sfreq):

    signal = np.mean(window,axis=0)

    feats = {}

    feats["mean"] = float(np.mean(signal))
    feats["std"] = float(np.std(signal))
    feats["rms"] = float(np.sqrt(np.mean(signal**2)))

    feats["max"] = float(np.max(signal))
    feats["min"] = float(np.min(signal))
    feats["ptp"] = float(np.ptp(signal))

    feats["line_length"] = float(
        np.sum(np.abs(np.diff(signal)))
    )

    spectrum = np.abs(
        np.fft.rfft(signal)
    )

    freqs = np.fft.rfftfreq(
        len(signal),
        d=1.0/sfreq
    )

    bands = {
        "delta":(0.5,4),
        "theta":(4,8),
        "alpha":(8,13),
        "beta":(13,30),
        "gamma":(30,45)
    }

    total_power = np.sum(spectrum)+1e-12

    for band,(lo,hi) in bands.items():

        mask = (
            (freqs>=lo)&
            (freqs<hi)
        )

        power = np.sum(
            spectrum[mask]
        )

        feats[f"{band}_power"] = float(power)

        feats[f"{band}_relative"] = float(
            power/total_power
        )

    return feats

rows = []

edf_files = sorted(
    DATASET_ROOT.rglob("*.edf")
)

print()
print("EDF FILES:",len(edf_files))
print()

for edf in tqdm(edf_files):

    patient = edf.parent.name
    fname = edf.name

    intervals = (
        SEIZURES
        .get(patient,{})
        .get(fname,[])
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

        seizure_windows = 0
        background_windows = 0

        for start in range(
            0,
            total-win,
            stride
        ):

            end = start + win

            start_sec = start/sfreq
            end_sec = end/sfreq

            label = int(
                overlaps(
                    start_sec,
                    end_sec,
                    intervals
                )
            )

            if label:
                seizure_windows += 1
            else:
                background_windows += 1

            feats = compute_features(
                data[:,start:end],
                sfreq
            )

            feats["label"] = label
            feats["patient"] = patient
            feats["edf"] = fname

            rows.append(feats)

        print(
            f"{fname} "
            f"SZ={seizure_windows} "
            f"BG={background_windows}"
        )

        del raw
        gc.collect()

    except Exception as e:

        print(
            "FAILED",
            edf,
            e
        )

df = pd.DataFrame(rows)

print()
print(df.shape)
print()

print(
    df["label"]
    .value_counts()
)

df.to_parquet(
    OUTPUT_FILE,
    index=False
)

print()
print("SAVED:",OUTPUT_FILE)
print()